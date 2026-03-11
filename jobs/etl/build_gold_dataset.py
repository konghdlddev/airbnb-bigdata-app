import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from configs.minio_client import upload_directory
from configs.settings import settings


if __name__ == "__main__":
    """Publish the local gold parquet dataset to MinIO."""
    upload_directory(settings.gold_data_path, settings.minio_gold_prefix)
    print(
        f"Uploaded gold dataset to s3://{settings.minio_bucket}/{settings.minio_gold_prefix}/"
    )
