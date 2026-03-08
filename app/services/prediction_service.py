from functools import lru_cache
from typing import Dict, List

from pyspark.ml import PipelineModel

from app.services.analytics_service import _spark
from configs.settings import settings
from configs.zone_mapping import map_neighbourhood_to_zone_code


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


def predict_listing_price(payload: Dict) -> float:
    """Predict listing price from user inputs."""
    zone_code = payload.get("zone_code")
    if not zone_code:
        zone_code = map_neighbourhood_to_zone_code(payload.get("neighbourhood", "")) or "UNKNOWN"

    row = {
        "room_type": payload["room_type"],
        "zone_code": zone_code,
        "minimum_nights": float(payload["minimum_nights"]),
        "number_of_reviews": float(payload["number_of_reviews"]),
        "availability_365": float(payload["availability_365"]),
    }

    df = _spark().createDataFrame([row])
    pred = _model().transform(df).select("prediction").first()[0]
    return float(pred)
