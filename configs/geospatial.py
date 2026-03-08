from typing import Dict, Union

from pyspark.sql.column import Column
from pyspark.sql import functions as F


# Key Bangkok landmarks used for location intelligence features.
LANDMARKS: Dict[str, Dict[str, Union[str, float, list]]] = {
    "siam": {
        "label": "Siam Center",
        "lat": 13.7466,
        "lng": 100.5347,
        "aliases": ["siam", "siam center"],
        "distance_column": "distance_to_siam",
    },
    "asok": {
        "label": "Asok",
        "lat": 13.7376,
        "lng": 100.5600,
        "aliases": ["asok", "อโศก"],
        "distance_column": "distance_to_asok",
    },
    "silom": {
        "label": "Silom",
        "lat": 13.7243,
        "lng": 100.5343,
        "aliases": ["silom", "si lom", "สีลม"],
        "distance_column": "distance_to_silom",
    },
    "riverside": {
        "label": "Riverside (Chao Phraya)",
        "lat": 13.7308,
        "lng": 100.5093,
        "aliases": ["riverside", "chao phraya", "river"],
        "distance_column": "distance_to_riverside",
    },
    "city_center": {
        "label": "Bangkok City Center",
        "lat": 13.7563,
        "lng": 100.5018,
        "aliases": ["city center", "bangkok city center", "downtown"],
        "distance_column": "distance_to_city_center",
    },
}

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
