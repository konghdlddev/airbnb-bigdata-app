import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from configs.geo_intelligence import (
    detect_landmark_from_query,
    detect_zone_from_query,
    neighbourhood_to_zone_map,
)
from configs.zone_mapping import map_neighbourhood_to_zone_code


RULES_PATH = Path("configs/query_rules.json")
NEAR_BTS_KM = 1.0
NEAR_MRT_KM = 1.0
DEFAULT_NEAR_LANDMARK_KM = 2.0


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
    # Thai natural phrasing such as "แถวบางกะปิ" or "ย่าน บางนา".
    thai_loc = re.search(r"(?:แถว|ใกล้|ย่าน|ที่)\s*([a-zA-Z\u0E00-\u0E7F][a-zA-Z\u0E00-\u0E7F\s\-]{1,40})", query)
    if thai_loc:
        raw = re.sub(r"\s+", " ", thai_loc.group(1)).strip(" .,!?")
        # Trim trailing price-related segments from location phrase.
        raw = re.split(r"\s*(?:ราคา|งบ|บาท|ต่อคืน|คืน|under|below|between)\s*", raw, maxsplit=1)[0].strip()
        normalized = _normalize_location(raw, rules)
        if normalized:
            return normalized

    for prep in rules.get("location_prepositions", ["in", "at", "near"]):
        loc_match = re.search(rf"\b{prep}\s+([a-zA-Z\u0E00-\u0E7F][a-zA-Z\u0E00-\u0E7F\s\-]{{1,40}})", query)
        if loc_match:
            raw = re.sub(r"\s+", " ", loc_match.group(1)).strip(" .,!?")
            raw = re.split(r"\s*(?:ราคา|งบ|บาท|ต่อคืน|คืน|under|below|between)\s*", raw, maxsplit=1)[0].strip()
            return _normalize_location(raw, rules)
    return None


def _extract_price(query: str, rules: Dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    # Thai range: "ราคา 300-700 บาท" or "ระหว่าง 300 ถึง 700".
    th_range = re.search(r"(?:ราคา\s*)?(\d{2,6})\s*(?:-|ถึง|to|and)\s*(\d{2,6})\s*(?:บาท)?", query)
    if th_range:
        low = float(min(int(th_range.group(1)), int(th_range.group(2))))
        high = float(max(int(th_range.group(1)), int(th_range.group(2))))
        return None, low, high

    range_match = re.search(r"(?:between\s*)?(\d{2,6})\s*(?:-|to|and)\s*(\d{2,6})", query)
    if range_match:
        low = float(min(int(range_match.group(1)), int(range_match.group(2))))
        high = float(max(int(range_match.group(1)), int(range_match.group(2))))
        return None, low, high

    th_max_match = re.search(r"(?:ไม่เกิน|ต่ำกว่า|งบ(?:ไม่เกิน)?|ราคา(?:ไม่เกิน)?)\s*(\d{2,6})\s*(?:บาท)?", query)
    if th_max_match:
        return float(th_max_match.group(1)), None, None

    max_match = re.search(r"(?:under|below|less\s+than)\s*(\d{2,6})\b", query)
    if max_match:
        return float(max_match.group(1)), None, None

    th_price_match = re.search(r"(?:ราคา|งบ)\s*(\d{2,6})\s*(?:บาท)?(?:\s*ต่อคืน|\s*/คืน)?", query)
    if th_price_match:
        return float(th_price_match.group(1)), None, None

    raw_num = re.search(r"\b(\d{2,6})\b", query)
    if raw_num:
        return float(raw_num.group(1)), None, None

    for hint, limit in rules.get("price_hints", {}).items():
        if hint in query:
            return float(limit), None, None

    return None, None, None


def _extract_room_type(query: str, rules: Dict) -> Optional[str]:
    sorted_aliases = sorted(rules.get("room_type_aliases", {}).items(), key=lambda kv: len(kv[0]), reverse=True)
    for alias, canonical in sorted_aliases:
        if not canonical:
            continue
        if alias.isascii():
            if re.search(rf"\b{re.escape(alias)}\b", query):
                return canonical
        elif alias in query:
            return canonical
    return None


def _extract_bedrooms(query: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:bedroom|bedrooms|bed)\b", query)
    return int(m.group(1)) if m else None


def _extract_accommodates(query: str) -> Optional[int]:
    m = re.search(r"(?:for|accommodates?|รองรับ)\s*(\d+)\s*(?:people|persons|guests)?", query)
    if m:
        return int(m.group(1))

    m2 = re.search(r"(\d+)\s*(?:people|persons|guests)", query)
    return int(m2.group(1)) if m2 else None


def _extract_sort_intent(query: str) -> Optional[str]:
    if re.search(r"\b(cheap|budget|affordable)\b", query) or "ถูก" in query:
        return "cheap"
    if re.search(r"\b(popular|best rated)\b", query) or "นิยม" in query:
        return "popular"
    return None


def _extract_transit_intent(query: str) -> Dict[str, object]:
    out: Dict[str, object] = {}
    if re.search(r"\bnear\s+bts\b", query) or re.search(r"ใกล้\s*bts", query):
        out["near_bts_km"] = NEAR_BTS_KM
    if re.search(r"\bnear\s+mrt\b", query) or re.search(r"ใกล้\s*mrt", query):
        out["near_mrt_km"] = NEAR_MRT_KM
    if re.search(r"\bnear\s+river\b", query) or re.search(r"ใกล้\s*(?:แม่น้ำ|ริมน้ำ)", query):
        out["distance_column"] = "distance_to_river"
        out["distance_threshold_km"] = DEFAULT_NEAR_LANDMARK_KM
        out["landmark_label"] = "River"
    return out


def _landmark_distance_column(landmark_key: str) -> str:
    aliases = {
        "siam_center": "distance_to_siam",
        "asok": "distance_to_asok",
        "silom": "distance_to_silom",
        "riverside": "distance_to_riverside",
        "city_center": "distance_to_city_center",
    }
    return aliases.get(landmark_key, f"distance_to_{landmark_key}")


def parse_query(user_query: str) -> Dict[str, Optional[object]]:
    """Parse natural language query into structured filter fields."""
    q = user_query.strip().lower()
    rules = _load_rules()

    room_type = _extract_room_type(q, rules)
    price_max, price_min, price_max_range = _extract_price(q, rules)
    location = _extract_location(q, rules)
    bedrooms = _extract_bedrooms(q)
    accommodates = _extract_accommodates(q)
    sort_intent = _extract_sort_intent(q)

    zone_code = detect_zone_from_query(q)
    landmark_match = detect_landmark_from_query(q)
    transit_intent = _extract_transit_intent(q)

    has_exact_location_intent = re.search(r"\b(?:in|at)\b", q) is not None or any(x in q for x in ["ที่", "ย่าน"])
    has_near_intent = re.search(r"\bnear\b", q) is not None or any(x in q for x in ["ใกล้", "แถว"])

    if has_exact_location_intent and location:
        zone_code = None

    if has_near_intent and location and not zone_code:
        zone_code = neighbourhood_to_zone_map().get(" ".join(location.lower().split()))
        if not zone_code:
            zone_code = map_neighbourhood_to_zone_code(location)

    if has_near_intent:
        # For phrases like "แถวบางกะปิ", keep exact area if no zone/landmark expansion is available.
        if zone_code or landmark_match:
            location = None

    landmark_key = None
    landmark_label = transit_intent.get("landmark_label")
    distance_column = transit_intent.get("distance_column")
    distance_threshold_km = transit_intent.get("distance_threshold_km")

    if has_near_intent and landmark_match:
        landmark_key, _ = landmark_match
        landmark_label = landmark_key.replace("_", " ").title()
        distance_column = _landmark_distance_column(landmark_key)
        distance_threshold_km = DEFAULT_NEAR_LANDMARK_KM
        location = None

    return {
        "raw_query": user_query,
        "zone_code": zone_code,
        "location": location,
        "room_type": room_type,
        "price_max": price_max,
        "price_min": price_min,
        "price_max_range": price_max_range,
        "bedrooms": bedrooms,
        "accommodates": accommodates,
        "sort_intent": sort_intent,
        "landmark_key": landmark_key,
        "landmark_label": landmark_label,
        "distance_column": distance_column,
        "distance_threshold_km": distance_threshold_km,
        "near_bts_km": transit_intent.get("near_bts_km"),
        "near_mrt_km": transit_intent.get("near_mrt_km"),
    }
