from functools import lru_cache
from typing import Dict

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from configs.settings import settings
from configs.spark_session import get_spark_session


@lru_cache(maxsize=1)
def _spark():
    return get_spark_session("airbnb-streamlit-analytics")


@lru_cache(maxsize=1)
def load_gold_dataframe() -> DataFrame:
    """Load curated listing data from local parquet storage."""
    return _spark().read.parquet(settings.gold_data_path)


def get_kpis() -> Dict[str, float]:
    """Compute top-level dashboard KPIs."""
    df = load_gold_dataframe()
    row = df.agg(
        F.count("*").alias("total_listings"),
        F.avg("price").alias("average_price"),
    ).first()
    return {
        "total_listings": int(row["total_listings"] or 0),
        "average_price": float(row["average_price"] or 0.0),
    }


def listings_by_neighbourhood(limit: int = 15):
    """Return listing counts by neighbourhood for charting."""
    return (
        load_gold_dataframe()
        .groupBy("neighbourhood")
        .count()
        .orderBy(F.col("count").desc())
        .limit(limit)
        .toPandas()
    )


def room_type_distribution():
    """Return room-type distribution for charting."""
    return load_gold_dataframe().groupBy("room_type").count().toPandas()


def average_price_vs_distance_to_city_center(bucket_km: float = 1.0):
    """Aggregate average price by distance buckets from Bangkok city center."""
    df = load_gold_dataframe()
    if "distance_to_city_center" not in df.columns:
        return None

    bucket_expr = (
        F.floor(F.col("distance_to_city_center") / F.lit(bucket_km)) * F.lit(bucket_km)
    ).alias("distance_bucket_km")

    return (
        df.select(bucket_expr, "price")
        .groupBy("distance_bucket_km")
        .agg(F.avg("price").alias("avg_price"), F.count("*").alias("listing_count"))
        .orderBy(F.col("distance_bucket_km").asc())
        .toPandas()
    )


def average_price_by_bangkok_zone():
    """Return average listing price grouped by Bangkok smart zones."""
    df = load_gold_dataframe()
    if "bangkok_zone" not in df.columns:
        return None
    return (
        df.groupBy("bangkok_zone")
        .agg(F.avg("price").alias("avg_price"), F.count("*").alias("listing_count"))
        .orderBy(F.col("avg_price").desc())
        .toPandas()
    )


def listings_count_by_zone():
    """Return listing counts by Bangkok smart zones."""
    df = load_gold_dataframe()
    if "bangkok_zone" not in df.columns:
        return None
    return (
        df.groupBy("bangkok_zone")
        .count()
        .orderBy(F.col("count").desc())
        .toPandas()
    )


def price_vs_nearest_bts(limit: int = 5000):
    """Sample points for scatter of price vs nearest BTS distance."""
    df = load_gold_dataframe()
    if "distance_to_nearest_bts" not in df.columns:
        return None
    return (
        df.select("price", "distance_to_nearest_bts", "bangkok_zone")
        .dropna(subset=["price", "distance_to_nearest_bts"])
        .limit(limit)
        .toPandas()
    )


def price_vs_transit_accessibility(limit: int = 5000):
    """Sample points for scatter of price vs transit accessibility score."""
    df = load_gold_dataframe()
    if "transit_accessibility_score" not in df.columns:
        return None
    return (
        df.select("price", "transit_accessibility_score", "bangkok_zone")
        .dropna(subset=["price", "transit_accessibility_score"])
        .limit(limit)
        .toPandas()
    )


def tourist_area_price_comparison():
    """Compare pricing between tourist and non-tourist areas."""
    df = load_gold_dataframe()
    if "is_tourist_area" not in df.columns:
        return None
    return (
        df.groupBy("is_tourist_area")
        .agg(F.avg("price").alias("avg_price"), F.count("*").alias("listing_count"))
        .orderBy(F.col("is_tourist_area").desc())
        .toPandas()
    )


def geo_map_points(limit: int = 3000):
    """Return listing points for map visualization."""
    df = load_gold_dataframe()
    required = {"latitude", "longitude", "price"}
    if not required.issubset(set(df.columns)):
        return None
    cols = [
        c
        for c in ["id", "name", "neighbourhood", "bangkok_zone", "price", "latitude", "longitude"]
        if c in df.columns
    ]
    return df.select(*cols).dropna(subset=["latitude", "longitude", "price"]).limit(limit).toPandas()
