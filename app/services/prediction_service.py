"""Price prediction service. Requires Spark/Java for ML model; pandas fallback for options only."""
from functools import lru_cache
from typing import Dict, List

import pandas as pd

from app.services.analytics_service import _spark, _use_pandas, load_gold_dataframe
from configs.geo_intelligence import neighbourhood_to_zone_map
from configs.settings import settings


@lru_cache(maxsize=1)
def _model():
    """Load and cache the trained Spark pipeline model. Requires Spark/Java."""
    from pyspark.ml import PipelineModel

    return PipelineModel.load(settings.model_local_path)


@lru_cache(maxsize=1)
def get_area_options() -> List[str]:
    df = load_gold_dataframe()
    if _use_pandas():
        if df.empty or "neighbourhood" not in df.columns:
            return ["Ratchathewi"]
        opts = df["neighbourhood"].dropna().unique().astype(str).tolist()
        return sorted(opts) or ["Ratchathewi"]
    from pyspark.sql import functions as F

    rows = (
        _spark()
        .read.parquet(settings.gold_data_path)
        .select("neighbourhood")
        .dropna(subset=["neighbourhood"])
        .distinct()
        .orderBy("neighbourhood")
        .collect()
    )
    return [r["neighbourhood"] for r in rows if r["neighbourhood"]] or ["Ratchathewi"]


@lru_cache(maxsize=1)
def _distance_defaults_by_neighbourhood() -> Dict[str, Dict[str, float]]:
    df = load_gold_dataframe()
    distance_cols = ["distance_to_siam", "distance_to_asok", "distance_to_city_center"]
    existing = [c for c in distance_cols if c in (df.columns if hasattr(df, "columns") else [])]
    if not existing:
        return {}
    if _use_pandas():
        if df.empty or "neighbourhood" not in df.columns:
            return {}
        agg = df.groupby("neighbourhood")[existing].mean()
        return {str(n): {c: float(agg.loc[n, c] or 0) for c in existing} for n in agg.index if n}
    from pyspark.sql import functions as F

    rows = df.groupBy("neighbourhood").agg(*[F.avg(c).alias(c) for c in existing]).collect()
    return {
        str(r["neighbourhood"]): {c: float(r[c] or 0) for c in existing}
        for r in rows
        if r["neighbourhood"]
    }


@lru_cache(maxsize=1)
def _global_distance_defaults() -> Dict[str, float]:
    df = load_gold_dataframe()
    distance_cols = ["distance_to_siam", "distance_to_asok", "distance_to_city_center"]
    existing = [c for c in distance_cols if c in (df.columns if hasattr(df, "columns") else [])]
    if not existing:
        return {c: 0.0 for c in distance_cols}
    if _use_pandas():
        if df.empty:
            return {c: 0.0 for c in distance_cols}
        return {c: float(df[c].mean() or 0) for c in existing}
    from pyspark.sql import functions as F

    row = df.agg(*[F.avg(c).alias(c) for c in existing]).first()
    return {c: float(row[c] or 0) for c in existing}


def _predict_price_pandas(payload: Dict) -> float:
    """Pandas fallback: estimate price from average by room_type + neighbourhood in Gold data."""
    df = load_gold_dataframe()
    if df.empty or "price" not in df.columns:
        return 1500.0  # default fallback
    room_type = payload.get("room_type", "Private room")
    neighbourhood = payload.get("neighbourhood", "")
    mask = df["room_type"] == room_type
    if neighbourhood and "neighbourhood" in df.columns:
        mask_n = mask & (df["neighbourhood"] == neighbourhood)
        subset = df.loc[mask_n, "price"].dropna()
        if len(subset) >= 3:
            return float(subset.median())
    subset = df.loc[mask, "price"].dropna()
    if len(subset) >= 1:
        return float(subset.median())
    return float(df["price"].median()) if not df["price"].empty else 1500.0


def predict_listing_price(payload: Dict) -> float:
    """Predict listing price. Uses Spark ML when available; pandas fallback (avg by room_type+area) otherwise."""
    if _use_pandas():
        return _predict_price_pandas(payload)
    zone_code = payload.get("bangkok_zone")
    if not zone_code:
        n_key = " ".join(str(payload.get("neighbourhood", "")).lower().split())
        zone_code = neighbourhood_to_zone_map().get(n_key, "OTHER")

    neighbourhood = payload.get("neighbourhood") or "Unknown"
    neighbourhood_defaults = _distance_defaults_by_neighbourhood().get(neighbourhood, {})
    global_defaults = _global_distance_defaults()

    def _distance_value(key: str) -> float:
        return float(payload.get(key, neighbourhood_defaults.get(key, global_defaults.get(key, 0.0))))

    row = {
        "room_type": payload["room_type"],
        "bangkok_zone": zone_code,
        "neighbourhood": payload.get("neighbourhood") or "Unknown",
        "bedrooms": int(payload.get("bedrooms", 1)),
        "accommodates": int(payload.get("accommodates", 2)),
        "minimum_nights": float(payload["minimum_nights"]),
        "number_of_reviews": float(payload["number_of_reviews"]),
        "reviews_per_month": float(payload.get("reviews_per_month", 0.0)),
        "availability_365": float(payload["availability_365"]),
        "distance_to_nearest_bts": float(payload.get("distance_to_nearest_bts", 10.0)),
        "distance_to_nearest_mrt": float(payload.get("distance_to_nearest_mrt", 10.0)),
        "transit_accessibility_score": float(payload.get("transit_accessibility_score", 0.0)),
        "is_tourist_area_num": 1.0 if bool(payload.get("is_tourist_area", False)) else 0.0,
        "distance_to_siam": _distance_value("distance_to_siam"),
        "distance_to_asok": _distance_value("distance_to_asok"),
        "distance_to_city_center": _distance_value("distance_to_city_center"),
    }

    from pyspark.sql import functions as F

    df = _spark().createDataFrame([row])
    pred = _model().transform(df).select("prediction").first()[0]
    return float(pred)
