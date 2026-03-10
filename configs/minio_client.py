import os
from typing import Optional

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from configs.settings import settings

def get_s3_client() -> BaseClient:
    """Build an S3-compatible client for MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=f"http{'s' if settings.minio_secure else ''}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name="us-east-1",
    )
def ensure_bucket(client: Optional[BaseClient] = None) -> None:
    """Create the target bucket if it does not exist."""
    s3 = client or get_s3_client()
    try:
        s3.head_bucket(Bucket=settings.minio_bucket)
    except ClientError:
        s3.create_bucket(Bucket=settings.minio_bucket)


def upload_file(local_path: str, object_key: str, client: Optional[BaseClient] = None) -> None:
    """Upload one file to MinIO."""
    s3 = client or get_s3_client()
    ensure_bucket(s3)
    s3.upload_file(local_path, settings.minio_bucket, object_key)


def upload_directory(local_dir: str, object_prefix: str, client: Optional[BaseClient] = None) -> None:
    """Upload an entire local directory recursively to MinIO."""
    s3 = client or get_s3_client()
    ensure_bucket(s3)

    for root, _, files in os.walk(local_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            relative_path = os.path.relpath(local_path, local_dir)
            object_key = f"{object_prefix.rstrip('/')}/{relative_path}"
            s3.upload_file(local_path, settings.minio_bucket, object_key)
