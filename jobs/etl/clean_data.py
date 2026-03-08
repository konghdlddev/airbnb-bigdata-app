from typing import Dict

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, LongType

from configs.settings import settings
from configs.spark_session import get_spark_session
from configs.zone_mapping import neighbourhood_to_zone


EXPECTED_COLUMNS = [
    "id",
    "name",
    "host_id",
    "host_name",
    "neighbourhood",
    "zone_code",
    "latitude",
    "longitude",
    "room_type",
    "price",
    "minimum_nights",
    "number_of_reviews",
    "last_review",
    "reviews_per_month",
    "calculated_host_listings_count",
    "availability_365",
    "number_of_reviews_ltm",
]

NUMERIC_CASTS: Dict[str, object] = {
    "id": LongType(),
    "host_id": LongType(),
    "latitude": DoubleType(),
    "longitude": DoubleType(),
    "price": DoubleType(),
    "minimum_nights": IntegerType(),
    "number_of_reviews": IntegerType(),
    "reviews_per_month": DoubleType(),
    "calculated_host_listings_count": IntegerType(),
    "availability_365": IntegerType(),
    "number_of_reviews_ltm": IntegerType(),
}

STRING_COLUMNS = ["name", "host_name", "neighbourhood", "room_type", "last_review"]

NEIGHBOURHOOD_ALIAS = {
    "bangna": "Bang Na",
    "bang na": "Bang Na",
    "bang kapi": "Bang Kapi",
    "parthum wan": "Pathum Wan",
    "ratchathewi": "Ratchathewi",
    "sukhumvit": "Vadhana",
}


def normalize_room_type(df: DataFrame) -> DataFrame:
    """Normalize room type text values into canonical labels."""
    return df.withColumn(
        "room_type",
        F.when(F.lower(F.col("room_type")).contains("entire"), F.lit("Entire home/apt"))
        .when(F.lower(F.col("room_type")).contains("private"), F.lit("Private room"))
        .when(F.lower(F.col("room_type")).contains("shared"), F.lit("Shared room"))
        .when(F.lower(F.col("room_type")).contains("hotel"), F.lit("Hotel room"))
        .otherwise(F.col("room_type")),
    )


def normalize_neighbourhood(df: DataFrame) -> DataFrame:
    """Normalize neighbourhood text and map common aliases to canonical names."""
    normalized = df.withColumn(
        "neighbourhood",
        F.initcap(F.trim(F.regexp_replace(F.col("neighbourhood"), r"\s+", " "))),
    )

    alias_expr = F.create_map([F.lit(x) for kv in NEIGHBOURHOOD_ALIAS.items() for x in kv])
    return normalized.withColumn(
        "neighbourhood",
        F.coalesce(alias_expr[F.lower(F.col("neighbourhood"))], F.col("neighbourhood")),
    )

def drop_accidental_columns(df: DataFrame) -> DataFrame:
    """Drop accidental index columns (for example _c0, unnamed columns)."""
    keep_cols = []
    for col_name in df.columns:
        lowered = col_name.strip().lower()
        if lowered in {"_c0", "unnamed: 0", ""}:
            continue
        keep_cols.append(col_name)
    return df.select(*keep_cols)


def normalize_schema(df: DataFrame) -> DataFrame:
    """Force canonical column names/order and remove duplicate column names."""
    # Spark can keep duplicate names when reading malformed headers; keep first occurrence only.
    seen = set()
    unique_cols = []
    for col_name in df.columns:
        if col_name not in seen:
            unique_cols.append(col_name)
            seen.add(col_name)

    normalized = df.select(*unique_cols)
    present_cols = [c for c in EXPECTED_COLUMNS if c in normalized.columns]
    return normalized.select(*present_cols)


def clean_dataset(df: DataFrame) -> DataFrame:
    """Apply null handling and type casting to raw listing data."""
    cleaned = drop_accidental_columns(df)
    cleaned = normalize_schema(cleaned)

    for col_name in STRING_COLUMNS:
        if col_name in cleaned.columns:
            cleaned = cleaned.withColumn(
                col_name,
                F.trim(F.regexp_replace(F.col(col_name).cast("string"), r"\s+", " ")),
            )

    for col_name, target_type in NUMERIC_CASTS.items():
        if col_name not in cleaned.columns:
            continue
        cleaned = cleaned.withColumn(
            col_name,
            F.regexp_replace(F.col(col_name).cast("string"), r"[^0-9.\-]", "").cast(target_type),
        )

    cleaned = cleaned.filter(F.col("price").isNotNull() & (F.col("price") > 0))
    cleaned = cleaned.filter(
        F.col("latitude").isNotNull()
        & F.col("longitude").isNotNull()
        & F.col("latitude").between(-90.0, 90.0)
        & F.col("longitude").between(-180.0, 180.0)
    )

    cleaned = cleaned.fillna(
        {
            "reviews_per_month": 0.0,
            "number_of_reviews": 0,
            "minimum_nights": 0,
            "availability_365": 0,
            "number_of_reviews_ltm": 0,
            "calculated_host_listings_count": 0,
        }
    )

    cleaned = normalize_room_type(cleaned)
    cleaned = normalize_neighbourhood(cleaned)

    # Enrich rows with zone_code to support zone-based search and ML features.
    n_to_zone = neighbourhood_to_zone()
    n_to_zone_expr = F.create_map([F.lit(x) for kv in n_to_zone.items() for x in kv])
    cleaned = cleaned.withColumn("zone_code", n_to_zone_expr[F.col("neighbourhood")])

    # Re-select in canonical order before writing parquet.
    cleaned = cleaned.select(*[c for c in EXPECTED_COLUMNS if c in cleaned.columns])
    return cleaned


if __name__ == "__main__":
    spark = get_spark_session("airbnb-clean-data")

    raw_df = (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .option("multiLine", "true")
        .option("escape", '"')
        .csv(settings.raw_data_path)
    )

    print("\n[clean_data] Raw schema")
    raw_df.printSchema()
    raw_df.show(5, truncate=False)

    clean_df = clean_dataset(raw_df)

    print("\n[clean_data] Cleaned schema")
    clean_df.printSchema()
    clean_df.show(5, truncate=False)

    clean_df.write.mode("overwrite").parquet(settings.silver_data_path)
    print(f"Saved silver dataset to {settings.silver_data_path}")

    spark.stop()
