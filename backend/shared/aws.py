import os
import boto3
from botocore.config import Config as BotoConfig
from shared.config import Config

_boto_cfg = BotoConfig(
    region_name=Config.AWS_REGION,
    retries={"max_attempts": 3, "mode": "standard"},
)


def _ddb_kwargs() -> dict:
    kwargs = {"config": _boto_cfg}
    if Config.DYNAMODB_ENDPOINT_URL:
        kwargs["endpoint_url"] = Config.DYNAMODB_ENDPOINT_URL
        kwargs["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID", "local")
        kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY", "local")
    return kwargs


    return kwargs


def get_dynamodb_resource():
    return boto3.resource("dynamodb", **_ddb_kwargs())


def get_dynamodb_client():
    return boto3.client("dynamodb", **_ddb_kwargs())


def get_s3_client():
    kwargs = {"config": _boto_cfg}
    if Config.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = Config.S3_ENDPOINT_URL
    return boto3.client("s3", **kwargs)


def get_cognito_client():
    return boto3.client("cognito-idp", config=_boto_cfg)