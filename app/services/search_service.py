from typing import Dict, Tuple

from app.services.analytics_service import load_gold_dataframe
from jobs.search.build_filters import build_filters
from jobs.search.parse_query import parse_query
from jobs.search.search_listings import search_listings


def build_filter_logic(filters: Dict) -> str:
    """Convert structured filters to SQL-like readable logic for UI debugging."""
    parts = []

    if filters.get("zone_code"):
        neighbourhoods = filters.get("neighbourhood_in", [])
        if neighbourhoods:
            expanded = ", ".join([f"'{n}'" for n in neighbourhoods])
            parts.append(f"zone_code = '{filters['zone_code']}'")
            parts.append(f"neighbourhood IN ({expanded})")
        if filters.get("bangkok_zone_eq"):
            parts.append(f"bangkok_zone = '{filters['bangkok_zone_eq']}'")

    if filters.get("distance_lt"):
        distance_filter = filters["distance_lt"]
        parts.append(
            f"{distance_filter['column']} < {distance_filter['threshold_km']}"
        )

    if filters.get("distance_to_nearest_bts_lt") is not None:
        parts.append(f"distance_to_nearest_bts < {filters['distance_to_nearest_bts_lt']}")

    if filters.get("distance_to_nearest_mrt_lt") is not None:
        parts.append(f"distance_to_nearest_mrt < {filters['distance_to_nearest_mrt_lt']}")

    if filters.get("neighbourhood_eq"):
        parts.append(f"neighbourhood = '{filters['neighbourhood_eq']}'")

    if filters.get("room_type"):
        parts.append(f"room_type = '{filters['room_type']}'")

    if filters.get("price_lte") is not None:
        parts.append(f"price <= {int(filters['price_lte']) if float(filters['price_lte']).is_integer() else filters['price_lte']}")

    if filters.get("price_gte") is not None:
        parts.append(f"price >= {int(filters['price_gte']) if float(filters['price_gte']).is_integer() else filters['price_gte']}")

    if filters.get("bedrooms_gte") is not None:
        parts.append(f"bedrooms >= {filters['bedrooms_gte']}")

    if filters.get("accommodates_gte") is not None:
        parts.append(f"accommodates >= {filters['accommodates_gte']}")

    if filters.get("sort_by"):
        parts.append(f"ORDER BY {filters['sort_by']}")

    if not parts:
        return "WHERE TRUE"

    return "WHERE " + " AND ".join(parts)


def get_processed_preview(limit: int = 5):
    """Return first few rows from processed parquet for debugging in UI."""
    preview_columns = [
        "id",
        "name",
        "host_id",
        "host_name",
        "neighbourhood",
        "latitude",
        "longitude",
        "room_type",
        "price",
    ]
    df = load_gold_dataframe()
    cols = [c for c in preview_columns if c in df.columns]
    return df.select(*cols).limit(limit).toPandas()


def run_natural_language_search(query: str, limit: int = 10) -> Tuple[Dict, Dict, str, object]:
    """Parse user query and return structured filters plus matching records."""
    parsed = parse_query(query)
    filters = build_filters(parsed)

    df = load_gold_dataframe()
    result_pdf = search_listings(df, filters).limit(limit).toPandas()
    filter_logic = build_filter_logic(filters)

    # If a near/area query is too strict and yields no rows, relax area constraints while
    # preserving budget/room/capacity filters so users still get useful suggestions.
    normalized_query = query.lower()
    has_near_phrase = any(token in normalized_query for token in ["near", "แถว", "ใกล้"])
    has_area_constraint = any(k in filters for k in ["neighbourhood_eq", "neighbourhood_in", "bangkok_zone_eq", "zone_code"])

    if result_pdf.empty and has_near_phrase and has_area_constraint:
        relaxed_filters = dict(filters)
        for key in ["neighbourhood_eq", "neighbourhood_in", "bangkok_zone_eq", "zone_code", "distance_lt"]:
            relaxed_filters.pop(key, None)

        result_pdf = search_listings(df, relaxed_filters).limit(limit).toPandas()
        if not result_pdf.empty:
            filters = relaxed_filters
            filter_logic = build_filter_logic(filters) + " [fallback: broadened area]"

    return parsed, filters, filter_logic, result_pdf
