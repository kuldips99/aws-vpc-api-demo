import json, os, boto3
TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def handler(event, context):
    items = TABLE.scan(
        ProjectionExpression="vpc_id, #n, cidr, subnets, timestamp",
        ExpressionAttributeNames={"#n": "name"}
    )["Items"]
    return {"statusCode": 200, "body": json.dumps(items)}


