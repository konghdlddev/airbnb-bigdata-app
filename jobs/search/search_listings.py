from typing import Dict

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


OUTPUT_COLUMNS = [
    "id",
    "name",
    "neighbourhood",
    "zone_code",
    "room_type",
    "price",
    "minimum_nights",
    "number_of_reviews",
]


def search_listings(df: DataFrame, filters: Dict) -> DataFrame:
    """Apply structured search filters over listing data."""
    result = df

    if filters.get("neighbourhood_in"):
        result = result.filter(F.col("neighbourhood").isin(filters["neighbourhood_in"]))

    if filters.get("neighbourhood_eq"):
        result = result.filter(F.col("neighbourhood") == filters["neighbourhood_eq"])

    if filters.get("room_type"):
        result = result.filter(F.col("room_type") == filters["room_type"])

    if filters.get("price_lte") is not None:
        result = result.filter(F.col("price") <= float(filters["price_lte"]))

    final_cols = [c for c in OUTPUT_COLUMNS if c in result.columns]
    return result.select(*final_cols).orderBy(F.col("price").asc())
