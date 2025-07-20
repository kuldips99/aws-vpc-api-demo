#!/usr/bin/env python3
import aws_cdk as cdk
import os
from aws_vpc_api_demo.vpc_api_stack import VpcApiStack

app = cdk.App()

VpcApiStack(
    app,
    "VpcApiStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
    ),
)

app.synth()


