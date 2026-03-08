from typing import Dict

from configs.geo_intelligence import get_zones


def _zone_neighbourhoods(zone_code: str):
    zones = get_zones()
    zone = zones.get(zone_code, {})
    # Convert aliases to title case for matching normalized neighbourhood values in dataset.
    return sorted({" ".join(str(x).split()).title() for x in zone.get("neighbourhood_aliases", [])})


def build_filters(parsed_query: Dict) -> Dict:
    """Convert parsed query object into filter settings for Spark search."""
    filters = {}

    if parsed_query.get("zone_code"):
        filters["zone_code"] = parsed_query["zone_code"]
        filters["bangkok_zone_eq"] = parsed_query["zone_code"]
        zone_neighbourhoods = _zone_neighbourhoods(parsed_query["zone_code"])
        if zone_neighbourhoods:
            filters["neighbourhood_in"] = zone_neighbourhoods

    if parsed_query.get("distance_column") and parsed_query.get("distance_threshold_km") is not None:
        filters["distance_lt"] = {
            "column": parsed_query["distance_column"],
            "threshold_km": float(parsed_query["distance_threshold_km"]),
            "landmark_label": parsed_query.get("landmark_label"),
        }

    if parsed_query.get("near_bts_km") is not None:
        filters["distance_to_nearest_bts_lt"] = float(parsed_query["near_bts_km"])

    if parsed_query.get("near_mrt_km") is not None:
        filters["distance_to_nearest_mrt_lt"] = float(parsed_query["near_mrt_km"])

    if parsed_query.get("location"):
        filters["neighbourhood_eq"] = parsed_query["location"]

    if parsed_query.get("room_type"):
        filters["room_type"] = parsed_query["room_type"]

    if parsed_query.get("price_max") is not None:
        filters["price_lte"] = parsed_query["price_max"]

    if parsed_query.get("price_min") is not None:
        filters["price_gte"] = parsed_query["price_min"]

    if parsed_query.get("price_max_range") is not None:
        filters["price_lte"] = parsed_query["price_max_range"]

    if parsed_query.get("bedrooms") is not None:
        filters["bedrooms_gte"] = int(parsed_query["bedrooms"])

    if parsed_query.get("accommodates") is not None:
        filters["accommodates_gte"] = int(parsed_query["accommodates"])

    if parsed_query.get("sort_intent"):
        filters["sort_by"] = parsed_query["sort_intent"]

    return filters
