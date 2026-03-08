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

    if filters.get("neighbourhood_eq"):
        parts.append(f"neighbourhood = '{filters['neighbourhood_eq']}'")

    if filters.get("room_type"):
        parts.append(f"room_type = '{filters['room_type']}'")

    if filters.get("price_lte") is not None:
        parts.append(f"price <= {int(filters['price_lte']) if float(filters['price_lte']).is_integer() else filters['price_lte']}")

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
    filter_logic = build_filter_logic(filters)

    df = load_gold_dataframe()
    result_df = search_listings(df, filters).limit(limit)
    return parsed, filters, filter_logic, result_df.toPandas()
