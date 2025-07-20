#!/usr/bin/env python3
import aws_cdk as cdk
from api_vpc.stacks.vpc_api_stack import VpcApiStack   

app = cdk.App()
VpcApiStack(app, "VpcApiStack", env=cdk.Environment(
    account="242201265757",
    region="us-east-1"          
))
app.synth()
