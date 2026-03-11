"""Analytics service with Spark or pandas fallback when Java is unavailable."""
from functools import lru_cache
from pathlib import Path
from typing import Dict, Union

import pandas as pd

from configs.settings import settings

_USE_PANDAS: bool | None = None


def _use_pandas() -> bool:
    """True when Spark/Java unavailable or USE_PANDAS=1."""
    global _USE_PANDAS
    if _USE_PANDAS is not None:
        return _USE_PANDAS
    if settings.use_pandas_fallback:
        _USE_PANDAS = True
        return True
    try:
        from configs.spark_session import get_spark_session

        get_spark_session("airbnb-streamlit-analytics")
        _USE_PANDAS = False
        return False
    except Exception:
        _USE_PANDAS = True
        return True


@lru_cache(maxsize=1)
def _spark():
    """Return Spark session; raises if Java unavailable."""
    from configs.spark_session import get_spark_session

    return get_spark_session("airbnb-streamlit-analytics")


@lru_cache(maxsize=1)
def load_gold_dataframe() -> Union["pd.DataFrame", "object"]:
    """Load curated listing data. Returns pandas or Spark DataFrame depending on backend."""
    if _use_pandas():
        path = Path(settings.gold_data_path)
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path)
    return _spark().read.parquet(settings.gold_data_path)


def get_kpis() -> Dict[str, float]:
    df = load_gold_dataframe()
    if _use_pandas():
        if df.empty:
            return {"total_listings": 0, "average_price": 0.0}
        return {
            "total_listings": int(len(df)),
            "average_price": float(df["price"].mean() if "price" in df.columns else 0.0),
        }
    from pyspark.sql import functions as F

    row = df.agg(
        F.count("*").alias("total_listings"),
        F.avg("price").alias("average_price"),
    ).first()
    return {
        "total_listings": int(row["total_listings"] or 0),
        "average_price": float(row["average_price"] or 0.0),
    }


def listings_by_neighbourhood(limit: int = 15):
    df = load_gold_dataframe()
    if _use_pandas():
        if df.empty or "neighbourhood" not in df.columns:
            return pd.DataFrame()
        return (
            df.groupby("neighbourhood")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(limit)
        )
    from pyspark.sql import functions as F

    return (
        df.groupBy("neighbourhood")
        .count()
        .orderBy(F.col("count").desc())
        .limit(limit)
        .toPandas()
    )


def room_type_distribution():
    df = load_gold_dataframe()
    if _use_pandas():
        if df.empty or "room_type" not in df.columns:
            return pd.DataFrame()
        return df.groupby("room_type").size().reset_index(name="count")
    return df.groupBy("room_type").count().toPandas()


def average_price_vs_distance_to_city_center(bucket_km: float = 1.0):
    df = load_gold_dataframe()
    if "distance_to_city_center" not in (df.columns if hasattr(df, "columns") else []):
        return None
    if _use_pandas():
        if df.empty:
            return None
        df = df.copy()
        df["distance_bucket_km"] = (df["distance_to_city_center"] // bucket_km) * bucket_km
        return (
            df.groupby("distance_bucket_km")["price"]
            .agg(["mean", "count"])
            .rename(columns={"mean": "avg_price", "count": "listing_count"})
            .reset_index()
            .sort_values("distance_bucket_km")
        )
    from pyspark.sql import functions as F

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
    df = load_gold_dataframe()
    if "bangkok_zone" not in (df.columns if hasattr(df, "columns") else []):
        return None
    if _use_pandas():
        if df.empty:
            return None
        return (
            df.groupby("bangkok_zone")["price"]
            .agg(["mean", "count"])
            .rename(columns={"mean": "avg_price", "count": "listing_count"})
            .reset_index()
            .sort_values("avg_price", ascending=False)
        )
    from pyspark.sql import functions as F

    return (
        df.groupBy("bangkok_zone")
        .agg(F.avg("price").alias("avg_price"), F.count("*").alias("listing_count"))
        .orderBy(F.col("avg_price").desc())
        .toPandas()
    )


def listings_count_by_zone():
    df = load_gold_dataframe()
    if "bangkok_zone" not in (df.columns if hasattr(df, "columns") else []):
        return None
    if _use_pandas():
        if df.empty:
            return None
        return (
            df.groupby("bangkok_zone")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
    from pyspark.sql import functions as F

    return (
        df.groupBy("bangkok_zone")
        .count()
        .orderBy(F.col("count").desc())
        .toPandas()
    )


def price_vs_nearest_bts(limit: int = 5000):
    df = load_gold_dataframe()
    if "distance_to_nearest_bts" not in (df.columns if hasattr(df, "columns") else []):
        return None
    if _use_pandas():
        if df.empty:
            return None
        cols = [c for c in ["price", "distance_to_nearest_bts", "bangkok_zone"] if c in df.columns]
        return df[cols].dropna(subset=["price", "distance_to_nearest_bts"]).head(limit)
    from pyspark.sql import functions as F

    return (
        df.select("price", "distance_to_nearest_bts", "bangkok_zone")
        .dropna(subset=["price", "distance_to_nearest_bts"])
        .limit(limit)
        .toPandas()
    )


def price_vs_transit_accessibility(limit: int = 5000):
    df = load_gold_dataframe()
    if "transit_accessibility_score" not in (df.columns if hasattr(df, "columns") else []):
        return None
    if _use_pandas():
        if df.empty:
            return None
        cols = [c for c in ["price", "transit_accessibility_score", "bangkok_zone"] if c in df.columns]
        return df[cols].dropna(subset=["price", "transit_accessibility_score"]).head(limit)
    from pyspark.sql import functions as F

    return (
        df.select("price", "transit_accessibility_score", "bangkok_zone")
        .dropna(subset=["price", "transit_accessibility_score"])
        .limit(limit)
        .toPandas()
    )


def tourist_area_price_comparison():
    df = load_gold_dataframe()
    if "is_tourist_area" not in (df.columns if hasattr(df, "columns") else []):
        return None
    if _use_pandas():
        if df.empty:
            return None
        return (
            df.groupby("is_tourist_area")["price"]
            .agg(["mean", "count"])
            .rename(columns={"mean": "avg_price", "count": "listing_count"})
            .reset_index()
            .sort_values("is_tourist_area", ascending=False)
        )
    from pyspark.sql import functions as F

    return (
        df.groupBy("is_tourist_area")
        .agg(F.avg("price").alias("avg_price"), F.count("*").alias("listing_count"))
        .orderBy(F.col("is_tourist_area").desc())
        .toPandas()
    )


def geo_map_points(limit: int = 3000):
    df = load_gold_dataframe()
    required = {"latitude", "longitude", "price"}
    cols = set(df.columns) if hasattr(df, "columns") else set()
    if not required.issubset(cols):
        return None
    display_cols = [c for c in ["id", "name", "neighbourhood", "bangkok_zone", "price", "latitude", "longitude"] if c in cols]
    if _use_pandas():
        if df.empty:
            return None
        return df[display_cols].dropna(subset=["latitude", "longitude", "price"]).head(limit)
    return df.select(*display_cols).dropna(subset=["latitude", "longitude", "price"]).limit(limit).toPandas()
