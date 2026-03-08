from typing import Dict, List, Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from app.services.analytics_service import load_gold_dataframe


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


def _safe_col(df: DataFrame, col_name: str, default_value):
    return F.col(col_name) if col_name in df.columns else F.lit(default_value)


def get_listing_id_options(limit: int = 5000) -> List[int]:
    df = load_gold_dataframe()
    if "id" not in df.columns:
        return []
    rows = df.select("id").dropna().limit(limit).toPandas()
    return [int(x) for x in rows["id"].tolist()]


def get_listing_details(listing_id: int) -> Optional[Dict]:
    df = load_gold_dataframe()
    row = df.filter(F.col("id") == int(listing_id)).limit(1).toPandas()
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def recommend_similar_listings(listing_id: int, limit: int = 10):
    df = load_gold_dataframe()

    target_row = df.filter(F.col("id") == int(listing_id)).limit(1).collect()
    if not target_row:
        return None

    target = target_row[0].asDict()

    target_zone = target.get("bangkok_zone")
    target_room_type = target.get("room_type")
    target_price = float(target.get("price") or 0.0)
    target_city_center_distance = float(target.get("distance_to_city_center") or 0.0)
    target_transit_score = float(target.get("transit_accessibility_score") or 0.0)
    target_tourist = bool(target.get("is_tourist_area") or False)

    out = df.filter(F.col("id") != int(listing_id))

    zone_score = F.when(_safe_col(out, "bangkok_zone", None) == F.lit(target_zone), F.lit(25.0)).otherwise(F.lit(0.0))
    room_type_score = F.when(_safe_col(out, "room_type", None) == F.lit(target_room_type), F.lit(15.0)).otherwise(F.lit(0.0))

    price = _safe_col(out, "price", 0.0).cast("double")
    price_similarity = F.greatest(
        F.lit(0.0),
        F.lit(1.0) - (F.abs(price - F.lit(target_price)) / F.lit(max(target_price, 1.0))),
    ) * F.lit(30.0)

    city_center = _safe_col(out, "distance_to_city_center", 0.0).cast("double")
    city_center_similarity = F.greatest(
        F.lit(0.0),
        F.lit(1.0) - (F.abs(city_center - F.lit(target_city_center_distance)) / F.lit(8.0)),
    ) * F.lit(8.0)

    transit_score = _safe_col(out, "transit_accessibility_score", 0.0).cast("double")
    transit_similarity = F.greatest(
        F.lit(0.0),
        F.lit(1.0) - (F.abs(transit_score - F.lit(target_transit_score)) / F.lit(100.0)),
    ) * F.lit(12.0)

    tourist_score = F.when(_safe_col(out, "is_tourist_area", False) == F.lit(target_tourist), F.lit(10.0)).otherwise(F.lit(0.0))

    out = out.withColumn(
        "recommendation_score",
        zone_score + room_type_score + price_similarity + city_center_similarity + transit_similarity + tourist_score,
    )

    order_cols = [F.col("recommendation_score").desc(), F.col("price").asc()]
    out = out.orderBy(*order_cols)

    cols = [c for c in DISPLAY_COLUMNS if c in out.columns]
    return out.select(*cols).limit(limit).toPandas()
