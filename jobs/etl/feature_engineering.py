from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from configs.settings import settings
from configs.spark_session import get_spark_session


def add_features(df: DataFrame) -> DataFrame:
    """Create derived business features used by analytics and ML."""
    return (
        df.withColumn(
            "price_category",
            F.when(F.col("price") < 1000, F.lit("budget"))
            .when((F.col("price") >= 1000) & (F.col("price") < 2500), F.lit("mid"))
            .otherwise(F.lit("premium")),
        )
        .withColumn(
            "popularity_score",
            F.coalesce(F.col("reviews_per_month"), F.lit(0.0))
            * F.coalesce(F.col("number_of_reviews"), F.lit(0.0)),
        )
        .withColumn("occupancy_rate", F.lit(365.0) - F.coalesce(F.col("availability_365"), F.lit(0.0)))
    )


if __name__ == "__main__":
    spark = get_spark_session("airbnb-feature-engineering")

    silver_df = spark.read.parquet(settings.silver_data_path)
    print("\n[feature_engineering] Input (silver) schema")
    silver_df.printSchema()
    silver_df.show(5, truncate=False)

    featured_df = add_features(silver_df)

    print("\n[feature_engineering] Output (gold) schema")
    featured_df.printSchema()
    featured_df.show(5, truncate=False)

    featured_df.write.mode("overwrite").parquet(settings.gold_data_path)
    print(f"Saved gold dataset to {settings.gold_data_path}")

    spark.stop()
