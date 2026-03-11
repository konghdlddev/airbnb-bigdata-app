import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.minio_client import upload_file
from configs.settings import settings


if __name__ == "__main__":
    """Upload the raw CSV file to MinIO as the ingestion entry point."""
    upload_file(settings.raw_data_path, settings.minio_raw_key)
    print(f"Uploaded raw dataset to s3://{settings.minio_bucket}/{settings.minio_raw_key}")
