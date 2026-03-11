"""Recommendation service with Spark or pandas fallback."""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.services.analytics_service import _use_pandas, load_gold_dataframe


DISPLAY_COLUMNS = [
    "id",
    "name",
    "neighbourhood",
    "bangkok_zone",
    "room_type",
    "price",
    "distance_to_nearest_bts",
    "distance_to_nearest_mrt",
    "transit_accessibility_score",
    "is_tourist_area",
    "recommendation_score",
]


def get_listing_id_options(limit: int = 5000) -> List[int]:
    df = load_gold_dataframe()
    if "id" not in df.columns:
        return []
    if _use_pandas():
        ids = df["id"].dropna().head(limit).astype(int).tolist()
        return [int(x) for x in ids]
    from pyspark.sql import functions as F

    rows = df.select("id").dropna().limit(limit).toPandas()
    return [int(x) for x in rows["id"].tolist()]


def get_listing_details(listing_id: int) -> Optional[Dict]:
    df = load_gold_dataframe()
    if _use_pandas():
        row = df[df["id"] == int(listing_id)].head(1)
        if row.empty:
            return None
        return row.iloc[0].to_dict()
    from pyspark.sql import functions as F

    row = df.filter(F.col("id") == int(listing_id)).limit(1).toPandas()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_zone_options() -> List[str]:
    df = load_gold_dataframe()
    if "bangkok_zone" not in df.columns:
        return []
    if _use_pandas():
        return sorted(df["bangkok_zone"].dropna().unique().astype(str).tolist())
    from pyspark.sql import functions as F

    rows = (
        df.select("bangkok_zone")
        .dropna(subset=["bangkok_zone"])
        .distinct()
        .orderBy("bangkok_zone")
        .toPandas()
    )
    return [str(x) for x in rows["bangkok_zone"].tolist()]


def get_price_bounds() -> Dict[str, float]:
    df = load_gold_dataframe()
    if _use_pandas():
        if df.empty or "price" not in df.columns:
            return {"min_price": 0.0, "max_price": 0.0}
        return {
            "min_price": float(df["price"].min()),
            "max_price": float(df["price"].max()),
        }
    from pyspark.sql import functions as F

    row = df.agg(F.min("price").alias("min_price"), F.max("price").alias("max_price")).first()
    return {"min_price": float(row["min_price"] or 0.0), "max_price": float(row["max_price"] or 0.0)}


def recommend_by_zone_and_price(
    zone_code: str,
    min_price: float,
    max_price: float,
    limit: int = 10,
):
    df = load_gold_dataframe()
    if "bangkok_zone" not in df.columns:
        return None
    low, high = float(min(min_price, max_price)), float(max(min_price, max_price))
    target_price = (low + high) / 2.0

    if _use_pandas():
        out = df[(df["bangkok_zone"] == zone_code) & (df["price"] >= low) & (df["price"] <= high)]
        if out.empty:
            return None
        price = out["price"].fillna(0).astype(float)
        transit = out["transit_accessibility_score"].fillna(0).astype(float) if "transit_accessibility_score" in out.columns else 0
        reviews = out["number_of_reviews"].fillna(0).astype(float) if "number_of_reviews" in out.columns else 0
        budget_score = np.maximum(0, 1 - np.abs(price - target_price) / max(target_price, 1)) * 70
        transit_score = np.minimum(100, transit) * 0.2
        popularity_score = np.log1p(reviews) * 2
        out = out.copy()
        out["recommendation_score"] = budget_score + transit_score + popularity_score
        cols = [c for c in DISPLAY_COLUMNS if c in out.columns]
        return out[cols].sort_values(["recommendation_score", "price"], ascending=[False, True]).head(limit)
    from pyspark.sql import functions as F

    def _safe_col(df, col_name, default):
        return F.col(col_name) if col_name in df.columns else F.lit(default)

    out = df.filter(F.col("bangkok_zone") == zone_code).filter((F.col("price") >= low) & (F.col("price") <= high))
    if out.limit(1).count() == 0:
        return None
    price = _safe_col(out, "price", 0.0)
    transit = _safe_col(out, "transit_accessibility_score", 0.0)
    reviews = _safe_col(out, "number_of_reviews", 0.0)
    budget_score = F.greatest(F.lit(0.0), F.lit(1.0) - (F.abs(price - F.lit(target_price)) / F.lit(max(target_price, 1.0)))) * F.lit(70.0)
    transit_score = F.least(F.lit(100.0), transit) * F.lit(0.2)
    popularity_score = F.log1p(reviews) * F.lit(2.0)
    out = out.withColumn("recommendation_score", budget_score + transit_score + popularity_score)
    cols = [c for c in DISPLAY_COLUMNS if c in out.columns]
    return out.orderBy(F.col("recommendation_score").desc(), F.col("price").asc()).select(*cols).limit(limit).toPandas()


def recommend_similar_listings(listing_id: int, limit: int = 10):
    df = load_gold_dataframe()
    if _use_pandas():
        target_row = df[df["id"] == int(listing_id)].head(1)
        if target_row.empty:
            return None
        t = target_row.iloc[0]
        target_zone = t.get("bangkok_zone")
        target_room_type = t.get("room_type")
        target_price = float(t.get("price") or 0)
        target_city = float(t.get("distance_to_city_center") or 0)
        target_transit = float(t.get("transit_accessibility_score") or 0)
        target_tourist = bool(t.get("is_tourist_area") or False)
        out = df[df["id"] != int(listing_id)].copy()
        zone_score = (out["bangkok_zone"] == target_zone).astype(float) * 25
        room_score = (out["room_type"] == target_room_type).astype(float) * 15
        price = out["price"].fillna(0).astype(float)
        price_sim = np.maximum(0, 1 - np.abs(price - target_price) / max(target_price, 1)) * 30
        city = out["distance_to_city_center"].fillna(0).astype(float) if "distance_to_city_center" in out.columns else 0
        city_sim = np.maximum(0, 1 - np.abs(city - target_city) / 8) * 8
        transit = out["transit_accessibility_score"].fillna(0).astype(float) if "transit_accessibility_score" in out.columns else 0
        transit_sim = np.maximum(0, 1 - np.abs(transit - target_transit) / 100) * 12
        tourist_score = (out["is_tourist_area"].fillna(False) == target_tourist).astype(float) * 10
        out["recommendation_score"] = zone_score + room_score + price_sim + city_sim + transit_sim + tourist_score
        cols = [c for c in DISPLAY_COLUMNS if c in out.columns]
        return out[cols].sort_values(["recommendation_score", "price"], ascending=[False, True]).head(limit)
    from pyspark.sql import functions as F

    def _safe_col(df, col_name, default):
        return F.col(col_name) if col_name in df.columns else F.lit(default)

    target_row = df.filter(F.col("id") == int(listing_id)).limit(1).collect()
    if not target_row:
        return None
    target = target_row[0].asDict()
    target_zone = target.get("bangkok_zone")
    target_room_type = target.get("room_type")
    target_price = float(target.get("price") or 0)
    target_city = float(target.get("distance_to_city_center") or 0)
    target_transit = float(target.get("transit_accessibility_score") or 0)
    target_tourist = bool(target.get("is_tourist_area") or False)
    out = df.filter(F.col("id") != int(listing_id))
    zone_score = F.when(_safe_col(out, "bangkok_zone", None) == F.lit(target_zone), F.lit(25.0)).otherwise(F.lit(0.0))
    room_type_score = F.when(_safe_col(out, "room_type", None) == F.lit(target_room_type), F.lit(15.0)).otherwise(F.lit(0.0))
    price = _safe_col(out, "price", 0.0)
    price_similarity = F.greatest(F.lit(0.0), F.lit(1.0) - (F.abs(price - F.lit(target_price)) / F.lit(max(target_price, 1.0)))) * F.lit(30.0)
    city_center = _safe_col(out, "distance_to_city_center", 0.0)
    city_center_similarity = F.greatest(F.lit(0.0), F.lit(1.0) - (F.abs(city_center - F.lit(target_city)) / F.lit(8.0))) * F.lit(8.0)
    transit_score = _safe_col(out, "transit_accessibility_score", 0.0)
    transit_similarity = F.greatest(F.lit(0.0), F.lit(1.0) - (F.abs(transit_score - F.lit(target_transit)) / F.lit(100.0))) * F.lit(12.0)
    tourist_score = F.when(_safe_col(out, "is_tourist_area", False) == F.lit(target_tourist), F.lit(10.0)).otherwise(F.lit(0.0))
    out = out.withColumn("recommendation_score", zone_score + room_type_score + price_similarity + city_center_similarity + transit_similarity + tourist_score)
    cols = [c for c in DISPLAY_COLUMNS if c in out.columns]
    return out.orderBy(F.col("recommendation_score").desc(), F.col("price").asc()).select(*cols).limit(limit).toPandas()
