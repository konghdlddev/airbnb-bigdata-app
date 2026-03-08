from configs.minio_client import upload_file
from configs.settings import settings


if __name__ == "__main__":
    """Upload the raw CSV file to MinIO as the ingestion entry point."""
    upload_file(settings.raw_data_path, settings.minio_raw_key)
    print(f"Uploaded raw dataset to s3://{settings.minio_bucket}/{settings.minio_raw_key}")
