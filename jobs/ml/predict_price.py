from typing import Dict

from pyspark.ml import PipelineModel

from configs.geo_intelligence import neighbourhood_to_zone_map
from configs.settings import settings
from configs.spark_session import get_spark_session


def predict_price(payload: Dict) -> float:
    """Run a single-row prediction with the trained Spark model."""
    spark = get_spark_session("airbnb-predict-price")

    zone_code = payload.get("bangkok_zone")
    if not zone_code:
        n_key = " ".join(str(payload.get("neighbourhood", "")).lower().split())
        zone_code = neighbourhood_to_zone_map().get(n_key, "OTHER")

    # Fallback values keep this script usable even without explicit geospatial inputs.
    distance_to_siam = float(payload.get("distance_to_siam", 0.0))
    distance_to_asok = float(payload.get("distance_to_asok", 0.0))
    distance_to_city_center = float(payload.get("distance_to_city_center", 0.0))

    row = {
        "room_type": payload.get("room_type", "Entire home/apt"),
        "bangkok_zone": zone_code,
        "minimum_nights": float(payload.get("minimum_nights", 1)),
        "number_of_reviews": float(payload.get("number_of_reviews", 0)),
        "reviews_per_month": float(payload.get("reviews_per_month", 0.0)),
        "availability_365": float(payload.get("availability_365", 180)),
        "distance_to_nearest_bts": float(payload.get("distance_to_nearest_bts", 10.0)),
        "distance_to_nearest_mrt": float(payload.get("distance_to_nearest_mrt", 10.0)),
        "transit_accessibility_score": float(payload.get("transit_accessibility_score", 0.0)),
        "is_tourist_area_num": 1.0 if bool(payload.get("is_tourist_area", False)) else 0.0,
        "distance_to_siam": distance_to_siam,
        "distance_to_asok": distance_to_asok,
        "distance_to_city_center": distance_to_city_center,
    }

    input_df = spark.createDataFrame([row])
    model = PipelineModel.load(settings.model_local_path)

    prediction = model.transform(input_df).select("prediction").first()[0]
    spark.stop()
    return float(prediction)
