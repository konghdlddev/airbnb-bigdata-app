from typing import Dict, Union

from pyspark.sql.column import Column
from pyspark.sql import functions as F

from configs.geo_intelligence import get_landmarks


def _build_landmarks() -> Dict[str, Dict[str, Union[str, float, list]]]:
    rows = get_landmarks()
    output: Dict[str, Dict[str, Union[str, float, list]]] = {}
    for key, meta in rows.items():
        output[key] = {
            "label": key.replace("_", " ").title(),
            "lat": float(meta["lat"]),
            "lng": float(meta["lng"]),
            "aliases": meta.get("aliases", []),
            "distance_column": f"distance_to_{key}",
        }
    return output


LANDMARKS: Dict[str, Dict[str, Union[str, float, list]]] = _build_landmarks()

NEAR_DISTANCE_KM = 2.0


def calculate_distance(lat1: Column, lon1: Column, lat2: float, lon2: float) -> Column:
    """Compute Haversine distance in kilometers using Spark SQL column expressions."""
    # Use vectorized Spark math functions instead of Python UDF for better performance.
    earth_radius_km = F.lit(6371.0)

    lat1_rad = F.radians(lat1)
    lon1_rad = F.radians(lon1)
    lat2_rad = F.radians(F.lit(lat2))
    lon2_rad = F.radians(F.lit(lon2))

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        F.sin(dlat / F.lit(2.0)) ** F.lit(2.0)
        + F.cos(lat1_rad) * F.cos(lat2_rad) * (F.sin(dlon / F.lit(2.0)) ** F.lit(2.0))
    )
    c = F.lit(2.0) * F.asin(F.sqrt(a))
    return earth_radius_km * c
