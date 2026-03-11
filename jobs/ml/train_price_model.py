import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pyspark.ml import Pipeline
from pyspark.ml.feature import OneHotEncoder, StringIndexer, VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.sql import functions as F

from configs.minio_client import upload_directory
from configs.settings import settings
from configs.spark_session import get_spark_session


FEATURE_COLUMNS = [
    "room_type",
    "bangkok_zone",
    "minimum_nights",
    "number_of_reviews",
    "reviews_per_month",
    "availability_365",
    "distance_to_nearest_bts",
    "distance_to_nearest_mrt",
    "transit_accessibility_score",
    "is_tourist_area",
    "distance_to_siam",
    "distance_to_asok",
    "distance_to_city_center",
]

# Robust outlier controls for training labels (price).
LOWER_Q = 0.01
UPPER_Q = 0.99
IQR_MULTIPLIER = 1.5


def apply_price_outlier_handling(df):
    """Filter and winsorize extreme label outliers to stabilize price predictions."""
    # Use low relative error so upper-tail quantiles remain reliable under skewed pricing.
    quantiles = df.approxQuantile("price", [0.25, 0.75, LOWER_Q, UPPER_Q], 0.001)
    q1, q3, q_low, q_high = quantiles
    iqr = max(q3 - q1, 1.0)

    iqr_lower = q1 - (IQR_MULTIPLIER * iqr)
    iqr_upper = q3 + (IQR_MULTIPLIER * iqr)

    lower_bound = max(0.0, min(iqr_lower, q_low))
    # Keep both statistical robustness (IQR) and high-end market segment (upper quantile).
    upper_bound = max(lower_bound + 1.0, min(max(iqr_upper, q_high), q3 * 10.0))

    filtered = df.filter((F.col("price") >= F.lit(lower_bound)) & (F.col("price") <= F.lit(upper_bound)))
    clipped = filtered.withColumn(
        "price",
        F.when(F.col("price") < F.lit(q_low), F.lit(q_low))
        .when(F.col("price") > F.lit(q_high), F.lit(q_high))
        .otherwise(F.col("price")),
    )

    return clipped, {
        "q1": q1,
        "q3": q3,
        "q_low": q_low,
        "q_high": q_high,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }


def build_training_pipeline() -> Pipeline:
    """Build Spark ML pipeline for feature transformation and regression."""
    room_indexer = StringIndexer(
        inputCol="room_type", outputCol="room_type_idx", handleInvalid="keep"
    )
    zone_indexer = StringIndexer(
        inputCol="bangkok_zone", outputCol="bangkok_zone_idx", handleInvalid="keep"
    )

    encoder = OneHotEncoder(
        inputCols=["room_type_idx", "bangkok_zone_idx"],
        outputCols=["room_type_ohe", "bangkok_zone_ohe"],
        handleInvalid="keep",
    )

    assembler = VectorAssembler(
        inputCols=[
            "room_type_ohe",
            "bangkok_zone_ohe",
            "minimum_nights",
            "number_of_reviews",
            "reviews_per_month",
            "availability_365",
            "distance_to_nearest_bts",
            "distance_to_nearest_mrt",
            "transit_accessibility_score",
            "is_tourist_area_num",
            "distance_to_siam",
            "distance_to_asok",
            "distance_to_city_center",
        ],
        outputCol="features",
    )

    rf = RandomForestRegressor(
        labelCol="price",
        featuresCol="features",
        predictionCol="prediction",
        numTrees=80,
        maxDepth=10,
        seed=42,
    )

    return Pipeline(stages=[room_indexer, zone_indexer, encoder, assembler, rf])


if __name__ == "__main__":
    spark = get_spark_session("airbnb-train-price-model")

    df = spark.read.parquet(settings.gold_data_path).select(*FEATURE_COLUMNS, "price")
    raw_count = df.count()

    numeric_fill = {
        "minimum_nights": 0.0,
        "number_of_reviews": 0.0,
        "reviews_per_month": 0.0,
        "availability_365": 0.0,
        "distance_to_nearest_bts": 20.0,
        "distance_to_nearest_mrt": 20.0,
        "transit_accessibility_score": 0.0,
        "distance_to_siam": 20.0,
        "distance_to_asok": 20.0,
        "distance_to_city_center": 20.0,
    }
    df = df.fillna(numeric_fill)
    df = df.fillna({"room_type": "Unknown", "bangkok_zone": "OTHER"})
    df = df.withColumn("is_tourist_area_num", F.when(F.col("is_tourist_area") == True, F.lit(1.0)).otherwise(F.lit(0.0)))

    df = df.dropna(subset=["price"])

    df, stats = apply_price_outlier_handling(df)
    final_count = df.count()

    train_df, _ = df.randomSplit([0.8, 0.2], seed=42)
    pipeline = build_training_pipeline()
    model = pipeline.fit(train_df)

    model.write().overwrite().save(settings.model_local_path)
    upload_directory(settings.model_local_path, settings.minio_model_prefix)

    print(f"Model saved to {settings.model_local_path}")
    print(f"Model uploaded to s3://{settings.minio_bucket}/{settings.minio_model_prefix}/")
    print(
        "Outlier handling:",
        {
            "raw_rows": raw_count,
            "rows_after_outlier_filter": final_count,
            **{k: round(float(v), 4) for k, v in stats.items()},
        },
    )

    spark.stop()
