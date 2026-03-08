import json
import re
from pathlib import Path
from typing import Dict, Optional

from configs.zone_mapping import detect_zone


RULES_PATH = Path("configs/query_rules.json")


def _load_rules() -> Dict:
    with RULES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_location(raw_location: Optional[str], rules: Dict) -> Optional[str]:
    if not raw_location:
        return None

    compact = " ".join(raw_location.strip().lower().split())
    alias = rules.get("location_aliases", {}).get(compact)
    if alias:
        return alias

    return compact.title()


def _extract_location(query: str, rules: Dict) -> Optional[str]:
    for prep in rules["location_prepositions"]:
        # Capture location words after preposition up to punctuation or query end.
        loc_match = re.search(rf"\b{prep}\s+([a-zA-Z][a-zA-Z\s\-]{{1,40}})", query)
        if loc_match:
            raw = re.sub(r"\s+", " ", loc_match.group(1)).strip(" .,!?")
            return _normalize_location(raw, rules)
    return None


def _extract_price_max(query: str, rules: Dict) -> Optional[float]:
    keyword_match = re.search(r"(?:under|below|less\s+than)\s*(\d{2,6})\b", query)
    if keyword_match:
        return float(keyword_match.group(1))

    # Support free-form search phrases like "room 2000 in bang kapi".
    number_match = re.search(r"\b(\d{2,6})\b", query)
    if number_match:
        return float(number_match.group(1))

    for hint, limit in rules["price_hints"].items():
        if hint in query:
            return float(limit)

    return None


def _extract_room_type(query: str, rules: Dict) -> Optional[str]:
    # Prefer specific aliases first so "private room" wins over generic "room".
    sorted_aliases = sorted(rules["room_type_aliases"].items(), key=lambda kv: len(kv[0]), reverse=True)
    for alias, canonical in sorted_aliases:
        if re.search(rf"\b{re.escape(alias)}\b", query):
            return canonical
    return None


def parse_query(user_query: str) -> Dict[str, Optional[object]]:
    """Parse natural language query into structured filter fields."""
    q = user_query.strip().lower()
    rules = _load_rules()

    zone_match = detect_zone(q)
    room_type = _extract_room_type(q, rules)
    price_max = _extract_price_max(q, rules)
    location = _extract_location(q, rules)

    # If a query clearly mentions a zone alias, prefer zone-based search over exact location.
    zone_code = zone_match["zone_code"] if zone_match else None
    zone_name = zone_match["zone_name"] if zone_match else None
    zone_neighbourhoods = zone_match["neighbourhoods"] if zone_match else []
    if zone_code:
        location = None

    return {
        "raw_query": user_query,
        "zone_code": zone_code,
        "zone_name": zone_name,
        "zone_neighbourhoods": zone_neighbourhoods,
        "location": location,
        "room_type": room_type,
        "price_max": price_max,
    }
