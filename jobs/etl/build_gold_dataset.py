from configs.minio_client import upload_directory
from configs.settings import settings


if __name__ == "__main__":
    """Publish the local gold parquet dataset to MinIO."""
    upload_directory(settings.gold_data_path, settings.minio_gold_prefix)
    print(
        f"Uploaded gold dataset to s3://{settings.minio_bucket}/{settings.minio_gold_prefix}/"
    )
