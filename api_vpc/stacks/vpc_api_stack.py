from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_apigatewayv2_alpha as apigw,
    aws_apigatewayv2_integrations_alpha as apigw_int,
    aws_cognito as cognito,
    aws_lambda as _lambda,
    aws_dynamodb as ddb,
    aws_iam as iam,
)
from aws_cdk.aws_apigatewayv2_authorizers_alpha import HttpUserPoolAuthorizer
from constructs import Construct
import pathlib

class VpcApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # 1. Cognito User Pool
        user_pool = cognito.UserPool(
            self, "Users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            password_policy=cognito.PasswordPolicy(min_length=8)
        )
        user_pool_client = user_pool.add_client("spa-client")

        # 2. DynamoDB Table
        table = ddb.Table(
            self, "VpcMetadata",
            partition_key=ddb.Attribute(name="vpc_id", type=ddb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY
        )

        # 3. Lambda Execution Role
        lambda_role = iam.Role(
            self, "LambdaExecRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "VpcPermissions": iam.PolicyDocument(statements=[
                    iam.PolicyStatement(
                        actions=[
                            "ec2:CreateVpc", "ec2:CreateSubnet",
                            "ec2:DescribeVpcs", "ec2:DescribeSubnets",
                            "ec2:CreateTags"
                        ],
                        resources=["*"]
                    ),
                    iam.PolicyStatement(
                        actions=["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Scan"],
                        resources=[table.table_arn]
                    )
                ])
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        common_lambda_args = dict(
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=256,
            role=lambda_role,
            environment={"TABLE_NAME": table.table_name}
        )
        src_dir = str(pathlib.Path(__file__).parent.parent / "lambda_src")

        # 4. Lambda Functions
        create_fn = _lambda.Function(
            self, "CreateVpcFn",
            handler="create_vpc.handler",
            code=_lambda.Code.from_asset(src_dir),
            **common_lambda_args
        )
        get_fn = _lambda.Function(
            self, "GetVpcsFn",
            handler="get_vpcs.handler",
            code=_lambda.Code.from_asset(src_dir),
            **common_lambda_args
        )

        # 5. HTTP API
        http_api = apigw.HttpApi(self, "VpcApi",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_origins=["*"]
            )
        )

        # Cognito Authorizer for HTTP API
        authorizer = HttpUserPoolAuthorizer(self, "CognitoAuth",
            authorizer_name="CognitoAuth",
            user_pool=user_pool,
            user_pool_clients=[user_pool_client],
            identity_source=["$request.header.Authorization"]
        )

        # Routes
        http_api.add_routes(
            path="/vpcs",
            methods=[apigw.HttpMethod.POST],
            integration=apigw_int.HttpLambdaIntegration("CreateIntegration", create_fn),
            authorizer=authorizer
        )
        http_api.add_routes(
            path="/vpcs",
            methods=[apigw.HttpMethod.GET],
            integration=apigw_int.HttpLambdaIntegration("GetIntegration", get_fn),
            authorizer=authorizer
        )

        # Outputs
        self.http_api_url = http_api.url
        self.user_pool_id = user_pool.user_pool_id
        self.user_pool_client_id = user_pool_client.user_pool_client_id
