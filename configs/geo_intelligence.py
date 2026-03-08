import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple


LANDMARKS_PATH = Path("configs/bangkok_landmarks.json")
TRANSIT_PATH = Path("configs/bangkok_transit.json")
ZONES_PATH = Path("configs/bangkok_zones.json")


@lru_cache(maxsize=1)
def _load_json(path: str) -> Dict:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_landmarks() -> Dict[str, Dict]:
    return _load_json(str(LANDMARKS_PATH))


@lru_cache(maxsize=1)
def get_transit_stations() -> List[Dict]:
    return _load_json(str(TRANSIT_PATH)).get("stations", [])


@lru_cache(maxsize=1)
def get_zones() -> Dict[str, Dict]:
    return _load_json(str(ZONES_PATH)).get("zones", {})


@lru_cache(maxsize=1)
def zone_alias_index() -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    for zone_code, zone in get_zones().items():
        for alias in zone.get("aliases", []):
            rows.append((" ".join(alias.lower().split()), zone_code))
    return sorted(rows, key=lambda x: len(x[0]), reverse=True)


@lru_cache(maxsize=1)
def neighbourhood_to_zone_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for zone_code, zone in get_zones().items():
        for alias in zone.get("neighbourhood_aliases", []):
            mapping[" ".join(alias.lower().split())] = zone_code
    return mapping


def detect_zone_from_query(query: str) -> Optional[str]:
    norm = " ".join(query.lower().split())
    for alias, zone_code in zone_alias_index():
        if alias and alias in norm:
            return zone_code
    return None


def zone_landmark_refs(zone_code: str) -> List[str]:
    return get_zones().get(zone_code, {}).get("landmark_refs", [])


def detect_landmark_from_query(query: str) -> Optional[Tuple[str, Dict]]:
    norm = " ".join(query.lower().split())
    for key, meta in get_landmarks().items():
        for alias in meta.get("aliases", []):
            if " ".join(alias.lower().split()) in norm:
                return key, meta
    return None
