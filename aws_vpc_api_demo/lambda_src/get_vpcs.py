import json
import os
import boto3
from botocore.exceptions import ClientError

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def handler(event, context):
    try:
        resp = TABLE.scan(
            ProjectionExpression="vpc_id, #n, cidr, subnets, #ts",
            ExpressionAttributeNames={
                "#n": "name",
                "#ts": "timestamp"
            }
        )
        return {
            "statusCode": 200,
            "body": json.dumps(resp["Items"])
        }
    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


