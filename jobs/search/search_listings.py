from typing import Dict

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


OUTPUT_COLUMNS = [
    "id",
    "name",
    "neighbourhood",
    "zone_code",
    "bangkok_zone",
    "room_type",
    "price",
    "minimum_nights",
    "number_of_reviews",
    "distance_to_nearest_bts",
    "distance_to_nearest_mrt",
    "transit_accessibility_score",
    "bedrooms",
    "accommodates",
]


def search_listings(df: DataFrame, filters: Dict) -> DataFrame:
    """Apply structured search filters over listing data."""
    result = df

    if filters.get("neighbourhood_in"):
        result = result.filter(F.col("neighbourhood").isin(filters["neighbourhood_in"]))

    if filters.get("bangkok_zone_eq") and "bangkok_zone" in result.columns:
        result = result.filter(F.col("bangkok_zone") == filters["bangkok_zone_eq"])

    if filters.get("distance_lt"):
        distance_filter = filters["distance_lt"]
        distance_col = distance_filter.get("column")
        threshold = float(distance_filter.get("threshold_km", 0))
        if distance_col in result.columns:
            result = result.filter(F.col(distance_col) < F.lit(threshold))

    if filters.get("neighbourhood_eq"):
        result = result.filter(F.col("neighbourhood") == filters["neighbourhood_eq"])

    if filters.get("distance_to_nearest_bts_lt") is not None and "distance_to_nearest_bts" in result.columns:
        result = result.filter(F.col("distance_to_nearest_bts") < float(filters["distance_to_nearest_bts_lt"]))

    if filters.get("distance_to_nearest_mrt_lt") is not None and "distance_to_nearest_mrt" in result.columns:
        result = result.filter(F.col("distance_to_nearest_mrt") < float(filters["distance_to_nearest_mrt_lt"]))

    if filters.get("room_type"):
        result = result.filter(F.col("room_type") == filters["room_type"])

    if filters.get("price_lte") is not None:
        result = result.filter(F.col("price") <= float(filters["price_lte"]))

    if filters.get("price_gte") is not None:
        result = result.filter(F.col("price") >= float(filters["price_gte"]))

    if filters.get("bedrooms_gte") is not None and "bedrooms" in result.columns:
        result = result.filter(F.col("bedrooms") >= int(filters["bedrooms_gte"]))

    if filters.get("accommodates_gte") is not None and "accommodates" in result.columns:
        result = result.filter(F.col("accommodates") >= int(filters["accommodates_gte"]))

    sort_by = filters.get("sort_by")
    if sort_by == "popular" and "popularity_score" in result.columns:
        ordered = result.orderBy(F.col("popularity_score").desc(), F.col("price").asc())
    else:
        ordered = result.orderBy(F.col("price").asc())

    final_cols = [c for c in OUTPUT_COLUMNS if c in ordered.columns]
    return ordered.select(*final_cols)
