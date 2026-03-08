from functools import lru_cache
from typing import Dict, List

from pyspark.ml import PipelineModel
from pyspark.sql import functions as F

from app.services.analytics_service import _spark
from configs.geo_intelligence import neighbourhood_to_zone_map
from configs.settings import settings


@lru_cache(maxsize=1)
def _model() -> PipelineModel:
    """Load and cache the trained Spark pipeline model."""
    return PipelineModel.load(settings.model_local_path)


@lru_cache(maxsize=1)
def get_area_options() -> List[str]:
    """Return sorted distinct neighbourhood values for the Area dropdown."""
    df = _spark().read.parquet(settings.gold_data_path)
    rows = (
        df.select("neighbourhood")
        .dropna(subset=["neighbourhood"])
        .distinct()
        .orderBy("neighbourhood")
        .collect()
    )
    options = [r["neighbourhood"] for r in rows if r["neighbourhood"]]
    return options or ["Ratchathewi"]


@lru_cache(maxsize=1)
def _distance_defaults_by_neighbourhood() -> Dict[str, Dict[str, float]]:
    """Compute average distance features by neighbourhood for prediction-time defaults."""
    df = _spark().read.parquet(settings.gold_data_path)
    distance_cols = ["distance_to_siam", "distance_to_asok", "distance_to_city_center"]
    existing_distance_cols = [c for c in distance_cols if c in df.columns]

    if not existing_distance_cols:
        return {}

    agg_exprs = [F.avg(c).alias(c) for c in existing_distance_cols]
    rows = (
        df.groupBy("neighbourhood")
        .agg(*agg_exprs)
        .collect()
    )

    mapping: Dict[str, Dict[str, float]] = {}
    for r in rows:
        neighbourhood = r["neighbourhood"]
        if not neighbourhood:
            continue
        mapping[neighbourhood] = {
            col: float(r[col]) if r[col] is not None else 0.0 for col in existing_distance_cols
        }
    return mapping


@lru_cache(maxsize=1)
def _global_distance_defaults() -> Dict[str, float]:
    """Fallback distance defaults when neighbourhood-level averages are unavailable."""
    df = _spark().read.parquet(settings.gold_data_path)
    distance_cols = ["distance_to_siam", "distance_to_asok", "distance_to_city_center"]
    existing = [c for c in distance_cols if c in df.columns]
    if not existing:
        return {c: 0.0 for c in distance_cols}

    agg_exprs = [F.avg(c).alias(c) for c in existing]
    row = df.agg(*agg_exprs).first()
    result = {c: 0.0 for c in distance_cols}
    for c in existing:
        result[c] = float(row[c] or 0.0)
    return result


def predict_listing_price(payload: Dict) -> float:
    """Predict listing price from user inputs."""
    zone_code = payload.get("bangkok_zone")
    if not zone_code:
        n_key = " ".join(str(payload.get("neighbourhood", "")).lower().split())
        zone_code = neighbourhood_to_zone_map().get(n_key, "OTHER")

    neighbourhood = payload["neighbourhood"]
    neighbourhood_defaults = _distance_defaults_by_neighbourhood().get(neighbourhood, {})
    global_defaults = _global_distance_defaults()

    def _distance_value(key: str) -> float:
        return float(payload.get(key, neighbourhood_defaults.get(key, global_defaults.get(key, 0.0))))

    row = {
        "room_type": payload["room_type"],
        "bangkok_zone": zone_code,
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

    df = _spark().createDataFrame([row])
    pred = _model().transform(df).select("prediction").first()[0]
    return float(pred)
