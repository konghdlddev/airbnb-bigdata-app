import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple


ZONE_MAPPING_PATH = Path("configs/bangkok_zone_mapping.json")


@lru_cache(maxsize=1)
def _mapping() -> Dict:
    """Load Bangkok zone mapping config once and cache it."""
    with ZONE_MAPPING_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_zone_alias_index() -> List[Tuple[str, Dict]]:
    """Return alias -> zone entries sorted by alias length (longest first)."""
    zones = _mapping().get("zones", [])
    alias_rows: List[Tuple[str, Dict]] = []

    for zone in zones:
        aliases = zone.get("aliases", []) + [zone.get("display_name", ""), zone.get("zone_name", "")]
        for alias in aliases:
            normalized = " ".join(alias.lower().split())
            if normalized:
                alias_rows.append((normalized, zone))

    # Longest aliases first to avoid partial short-token false matches.
    return sorted(alias_rows, key=lambda row: len(row[0]), reverse=True)


@lru_cache(maxsize=1)
def neighbourhood_to_zone() -> Dict[str, str]:
    """Build neighbourhood -> zone_code lookup from centroids and zone definitions."""
    mapping: Dict[str, str] = {}

    for row in _mapping().get("neighbourhood_centroids", []):
        name = row.get("name")
        zone_code = row.get("zone_code")
        if name and zone_code:
            mapping[name] = zone_code

    for zone in _mapping().get("zones", []):
        zone_code = zone.get("zone_code")
        for n in zone.get("neighbourhoods", []):
            if n and zone_code and n not in mapping:
                mapping[n] = zone_code

    return mapping


@lru_cache(maxsize=1)
def zone_to_neighbourhoods() -> Dict[str, List[str]]:
    """Build zone_code -> sorted neighbourhood list lookup."""
    result: Dict[str, List[str]] = {}
    for zone in _mapping().get("zones", []):
        zone_code = zone.get("zone_code")
        n_list = sorted(set(zone.get("neighbourhoods", [])))
        if zone_code:
            result[zone_code] = n_list
    return result


def detect_zone(query: str) -> Optional[Dict[str, object]]:
    """Detect zone from free-text query using configured aliases."""
    normalized_query = " ".join(query.lower().split())

    for alias, zone in get_zone_alias_index():
        if alias in normalized_query:
            zone_code = zone.get("zone_code")
            return {
                "zone_code": zone_code,
                "zone_name": zone.get("zone_name") or zone.get("display_name") or zone_code,
                "display_name": zone.get("display_name") or zone_code,
                "neighbourhoods": zone_to_neighbourhoods().get(zone_code, []),
                "matched_alias": alias,
            }

    return None


def map_neighbourhood_to_zone_code(neighbourhood: str) -> Optional[str]:
    """Map normalized neighbourhood name to zone_code if available."""
    if not neighbourhood:
        return None

    lookup = neighbourhood_to_zone()
    if neighbourhood in lookup:
        return lookup[neighbourhood]

    lower_target = neighbourhood.lower()
    for key, value in lookup.items():
        if key.lower() == lower_target:
            return value

    return None
