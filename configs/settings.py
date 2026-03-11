import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Centralized application settings loaded from environment variables."""

    raw_data_path: str = os.getenv("APP_RAW_DATA_PATH", "data/raw/airbnb_bangkok.csv")
    silver_data_path: str = os.getenv("APP_SILVER_DATA_PATH", "data/processed/silver/listings")
    gold_data_path: str = os.getenv("APP_GOLD_DATA_PATH", "data/processed/gold/listings")
    model_local_path: str = os.getenv("APP_MODEL_PATH", "models/price_prediction")
    vector_index_path: str = os.getenv("APP_VECTOR_INDEX_PATH", "data/processed/gold/listing_embeddings")
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
