from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_cognito as cognito,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as apigw_int,
    aws_apigatewayv2_authorizers as apigw_auth,
)
from aws_cdk.aws_cognito import AuthFlow
from constructs import Construct
import pathlib

class VpcApiStack(Stack):
    """Serverless API that creates VPCs + subnets and stores metadata in DynamoDB."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1 Cognito User Pool + App Client (enable USER_PASSWORD_AUTH)
        user_pool = cognito.UserPool(
            self, "Users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            password_policy=cognito.PasswordPolicy(min_length=8),
        )
        user_pool_client = user_pool.add_client("spa-client",
            auth_flows=AuthFlow(user_password=True)   # ← enable USER_PASSWORD_AUTH
        )

        # 2 DynamoDB table
        table = ddb.Table(
            self, "VpcMetadata",
            partition_key=ddb.Attribute(name="vpc_id", type=ddb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # 3 IAM Role for Lambdas
        lambda_role = iam.Role(
            self, "LambdaExecRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "VpcAndDdb": iam.PolicyDocument(statements=[
                    iam.PolicyStatement(
                        actions=[
                            "ec2:CreateVpc", "ec2:CreateSubnet", "ec2:CreateTags",
                            "ec2:DescribeVpcs", "ec2:DescribeSubnets"
                        ],
                        resources=["*"],
                    ),
                    iam.PolicyStatement(
                        actions=["dynamodb:PutItem", "dynamodb:Scan"],
                        resources=[table.table_arn],
                    ),
                ])
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # 4 Lambda functions
        src_dir = str(pathlib.Path(__file__).parent / "lambda_src")
        common = dict(
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=256,
            timeout=Duration.seconds(30),
            role=lambda_role,
            environment={"TABLE_NAME": table.table_name},
            code=_lambda.Code.from_asset(src_dir),
        )
        create_fn = _lambda.Function(self, "CreateVpcFn",
                                     handler="create_vpc.handler", **common)
        get_fn    = _lambda.Function(self, "GetVpcsFn",
                                     handler="get_vpcs.handler",  **common)

        # 5 HTTP API + Cognito Authorizer
        http_api = apigw.HttpApi(
            self, "VpcApi",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_origins=["*"]
            ),
        )
        authorizer = apigw_auth.HttpUserPoolAuthorizer(
            "CognitoAuth",
            user_pool,
            user_pool_clients=[user_pool_client],
        )
        http_api.add_routes(
            path="/vpcs", methods=[apigw.HttpMethod.POST],
            integration=apigw_int.HttpLambdaIntegration("CreateInt", create_fn),
            authorizer=authorizer
        )
        http_api.add_routes(
            path="/vpcs", methods=[apigw.HttpMethod.GET],
            integration=apigw_int.HttpLambdaIntegration("GetInt", get_fn),
            authorizer=authorizer
        )

        # 6 CloudFormation Outputs
        CfnOutput(self, "HttpApiUrl",       value=http_api.url)
        CfnOutput(self, "UserPoolId",       value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)


