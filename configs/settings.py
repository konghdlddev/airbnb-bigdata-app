import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# โปรเจกต์ root — ใช้ path แบบ absolute เพื่อให้ Docker และ local ทำงานได้เสมอ
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _resolve_path(env_key: str, default_rel: str) -> str:
    """Resolve path: ใช้ env ถ้ามี มิฉะนั้นใช้ default แบบ absolute จาก project root."""
    val = os.getenv(env_key)
    if val:
        p = Path(val)
        return str(p.resolve()) if not p.is_absolute() else val
    return str(_PROJECT_ROOT / default_rel)


@dataclass(frozen=True)
class Settings:
    """Centralized application settings loaded from environment variables."""

    raw_data_path: str = _resolve_path("APP_RAW_DATA_PATH", "data/raw/airbnb_bangkok.csv")
    silver_data_path: str = _resolve_path("APP_SILVER_DATA_PATH", "data/processed/silver/listings")
    gold_data_path: str = _resolve_path("APP_GOLD_DATA_PATH", "data/processed/gold/listings")
    model_local_path: str = _resolve_path("APP_MODEL_PATH", "models/price_prediction")
    vector_index_path: str = _resolve_path("APP_VECTOR_INDEX_PATH", "data/processed/gold/listing_embeddings")
    embedding_model_name: str = os.getenv(
        "APP_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    use_pandas_fallback: bool = os.getenv("USE_PANDAS", "false").lower() in ("1", "true", "yes")

    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "airbnb-data")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    minio_raw_key: str = "raw/airbnb_bangkok.csv"
    minio_gold_prefix: str = "gold/listings"
    minio_model_prefix: str = "models/price_prediction"


settings = Settings()
