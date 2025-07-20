import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_vpc_api_demo.aws_vpc_api_demo_stack import AwsVpcApiDemoStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_vpc_api_demo/aws_vpc_api_demo_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsVpcApiDemoStack(app, "aws-vpc-api-demo")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
