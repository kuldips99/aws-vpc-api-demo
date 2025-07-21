import json, os, boto3, decimal
from botocore.exceptions import ClientError

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
EC2   = boto3.client("ec2")

class DecimalEncoder(json.JSONEncoder):
    """Serialize DynamoDB Decimal objects for JSON output."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

def vpc_exists(vpc_id: str) -> bool:
    """Return True if the VPC still exists; False if deleted."""
    try:
        resp = EC2.describe_vpcs(VpcIds=[vpc_id])
        return len(resp["Vpcs"]) > 0
    except ClientError as e:
        # Deleted VPCs raise InvalidVpcID.NotFound
        if e.response["Error"]["Code"] == "InvalidVpcID.NotFound":
            return False
        raise  # any other error should bubble up

def handler(event, context):
    # 1. Read all items
    items = TABLE.scan(
        ProjectionExpression="vpc_id, #n, cidr, subnets, #ts",
        ExpressionAttributeNames={"#n": "name", "#ts": "timestamp"},
    )["Items"]

    # 2. Keep only those whose VPC still exists
    live_items = [item for item in items if vpc_exists(item["vpc_id"])]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(live_items, cls=DecimalEncoder),
    }


