from typing import Dict

from pyspark.ml import PipelineModel

from configs.settings import settings
from configs.spark_session import get_spark_session
from configs.zone_mapping import map_neighbourhood_to_zone_code


def predict_price(payload: Dict) -> float:
    """Run a single-row prediction with the trained Spark model."""
    spark = get_spark_session("airbnb-predict-price")

    zone_code = payload.get("zone_code")
    if not zone_code:
        zone_code = map_neighbourhood_to_zone_code(payload.get("neighbourhood", "")) or "UNKNOWN"

    # Fallback values keep this script usable even without explicit geospatial inputs.
    distance_to_siam = float(payload.get("distance_to_siam", 0.0))
    distance_to_asok = float(payload.get("distance_to_asok", 0.0))
    distance_to_city_center = float(payload.get("distance_to_city_center", 0.0))

    row = {
        "room_type": payload.get("room_type", "Entire home/apt"),
        "zone_code": zone_code,
        "minimum_nights": float(payload.get("minimum_nights", 1)),
        "number_of_reviews": float(payload.get("number_of_reviews", 0)),
        "availability_365": float(payload.get("availability_365", 180)),
        "distance_to_siam": distance_to_siam,
        "distance_to_asok": distance_to_asok,
        "distance_to_city_center": distance_to_city_center,
    }

    input_df = spark.createDataFrame([row])
    model = PipelineModel.load(settings.model_local_path)

    prediction = model.transform(input_df).select("prediction").first()[0]
    spark.stop()
    return float(prediction)
