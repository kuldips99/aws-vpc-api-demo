import json, os, time, uuid, boto3
from botocore.exceptions import ClientError

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
EC2   = boto3.client("ec2")

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body)}

def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        cidr = body.get("cidr", "10.0.0.0/16")
        subnet_cidrs = body.get("subnets", ["10.0.1.0/24", "10.0.2.0/24"])
        name = body.get("name", f"demo-{uuid.uuid4().hex[:6]}")

        # 1 Create VPC
        vpc_id = EC2.create_vpc(CidrBlock=cidr)["Vpc"]["VpcId"]
        EC2.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": name}])

        # 2 Create subnets & tag
        subnet_ids = []
        for i, s_cidr in enumerate(subnet_cidrs):
            sn = EC2.create_subnet(VpcId=vpc_id, CidrBlock=s_cidr)["Subnet"]["SubnetId"]
            subnet_ids.append(sn)
            EC2.create_tags(Resources=[sn],
                            Tags=[{"Key": "Name", "Value": f"{name}-subnet-{i}"}])

        # 3 Persist
        TABLE.put_item(Item={
            "vpc_id": vpc_id,
            "name": name,
            "cidr": cidr,
            "subnets": subnet_ids,
            "timestamp": int(time.time())
        })

        return _resp(201, {"vpc_id": vpc_id, "subnets": subnet_ids})
    except ClientError as e:
        return _resp(500, {"error": str(e)})


