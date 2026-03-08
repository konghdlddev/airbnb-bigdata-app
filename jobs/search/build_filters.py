from typing import Dict


def build_filters(parsed_query: Dict) -> Dict:
    """Convert parsed query object into filter settings for Spark search."""
    filters = {}

    if parsed_query.get("zone_code"):
        filters["zone_code"] = parsed_query["zone_code"]
        filters["neighbourhood_in"] = parsed_query.get("zone_neighbourhoods", [])

    if parsed_query.get("distance_column") and parsed_query.get("distance_threshold_km") is not None:
        filters["distance_lt"] = {
            "column": parsed_query["distance_column"],
            "threshold_km": float(parsed_query["distance_threshold_km"]),
            "landmark_label": parsed_query.get("landmark_label"),
        }

    if parsed_query.get("location"):
        filters["neighbourhood_eq"] = parsed_query["location"]

    if parsed_query.get("room_type"):
        filters["room_type"] = parsed_query["room_type"]

    if parsed_query.get("price_max") is not None:
        filters["price_lte"] = parsed_query["price_max"]

    return filters
