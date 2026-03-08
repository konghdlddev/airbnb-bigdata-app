from typing import Dict, List, Tuple

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from configs.geo_intelligence import get_landmarks, get_transit_stations, get_zones
from configs.geospatial import calculate_distance


TOURIST_LANDMARKS = ["grand_palace", "wat_pho", "khao_san", "siam_center", "riverside"]
TOURIST_RADIUS_KM = 2.0
CITY_CENTER = (13.7563, 100.5018)
RIVER_POINT = (13.7308, 100.5093)


def _distance_column_name(landmark_key: str) -> str:
    return f"distance_to_{landmark_key}"


def add_landmark_distance_features(df: DataFrame) -> DataFrame:
    """Add distance-to-landmark features for core Bangkok points of interest."""
    out = df
    landmarks = get_landmarks()

    for key, meta in landmarks.items():
        out = out.withColumn(
            _distance_column_name(key),
            calculate_distance(F.col("latitude"), F.col("longitude"), float(meta["lat"]), float(meta["lng"])),
        )

    # Compatibility aliases expected by existing app/search components.
    if "distance_to_siam_center" in out.columns:
        out = out.withColumn("distance_to_siam", F.col("distance_to_siam_center"))
    if "distance_to_riverside" not in out.columns:
        out = out.withColumn(
            "distance_to_riverside",
            calculate_distance(F.col("latitude"), F.col("longitude"), RIVER_POINT[0], RIVER_POINT[1]),
        )

    out = out.withColumn(
        "distance_to_city_center",
        calculate_distance(F.col("latitude"), F.col("longitude"), CITY_CENTER[0], CITY_CENTER[1]),
    )
    out = out.withColumn(
        "distance_to_river",
        calculate_distance(F.col("latitude"), F.col("longitude"), RIVER_POINT[0], RIVER_POINT[1]),
    )

    return out


def _min_distance_expr(stations: List[Dict]) -> F.Column:
    exprs = [
        calculate_distance(F.col("latitude"), F.col("longitude"), float(s["lat"]), float(s["lng"]))
        for s in stations
    ]
    return F.least(*exprs) if exprs else F.lit(None)


def _nearest_station_name_expr(stations: List[Dict]) -> F.Column:
    if not stations:
        return F.lit(None)

    structs = [
        F.struct(
            calculate_distance(F.col("latitude"), F.col("longitude"), float(s["lat"]), float(s["lng"])).alias(
                "distance"
            ),
            F.lit(s["station_name"]).alias("station_name"),
        )
        for s in stations
    ]
    return F.array_sort(F.array(*structs))[0]["station_name"]


def add_transit_features(df: DataFrame) -> DataFrame:
    """Add nearest BTS/MRT distances, station names, and accessibility scoring."""
    stations = get_transit_stations()
    bts = [s for s in stations if str(s.get("mode", "")).upper() == "BTS"]
    mrt = [s for s in stations if str(s.get("mode", "")).upper() == "MRT"]

    out = (
        df.withColumn("distance_to_nearest_bts", _min_distance_expr(bts))
        .withColumn("distance_to_nearest_mrt", _min_distance_expr(mrt))
        .withColumn("nearest_bts_station", _nearest_station_name_expr(bts))
        .withColumn("nearest_mrt_station", _nearest_station_name_expr(mrt))
    )

    out = out.withColumn("is_walkable_to_bts", F.col("distance_to_nearest_bts") <= F.lit(1.0)).withColumn(
        "is_walkable_to_mrt", F.col("distance_to_nearest_mrt") <= F.lit(1.0)
    )

    # Stable score in [0, 100], combining BTS and MRT proximity while avoiding div-by-zero.
    score = (
        (F.lit(60.0) / (F.col("distance_to_nearest_bts") + F.lit(0.25)))
        + (F.lit(40.0) / (F.col("distance_to_nearest_mrt") + F.lit(0.25)))
    )
    out = out.withColumn("transit_accessibility_score", F.least(F.lit(100.0), score))

    return out


def classify_bangkok_zone(df: DataFrame) -> DataFrame:
    """Classify listings into smart Bangkok zones using neighbourhood and proximity fallback."""
    zones = get_zones()

    # Primary rule: normalized neighbourhood alias map.
    n_to_zone: Dict[str, str] = {}
    for zone_code, cfg in zones.items():
        for n in cfg.get("neighbourhood_aliases", []):
            n_to_zone[" ".join(str(n).lower().split())] = zone_code

    map_expr_items: List[F.Column] = []
    for k, v in n_to_zone.items():
        map_expr_items.extend([F.lit(k), F.lit(v)])

    out = df
    if map_expr_items:
        zone_map_expr = F.create_map(map_expr_items)
        out = out.withColumn(
            "bangkok_zone",
            zone_map_expr[F.lower(F.regexp_replace(F.col("neighbourhood"), r"\s+", " "))],
        )
    else:
        out = out.withColumn("bangkok_zone", F.lit(None))

    # Fallback rule: nearest referenced landmark per zone if neighbourhood mapping missing.
    fallback = F.col("bangkok_zone")
    for zone_code, cfg in zones.items():
        refs = cfg.get("landmark_refs", [])
        ref_cols = [f"distance_to_{r}" for r in refs if f"distance_to_{r}" in out.columns]
        if not ref_cols:
            continue
        if len(ref_cols) == 1:
            nearest_ref = F.col(ref_cols[0])
        else:
            nearest_ref = F.least(*[F.col(c) for c in ref_cols])
        fallback = F.when(F.col("bangkok_zone").isNull() & (nearest_ref < F.lit(3.0)), F.lit(zone_code)).otherwise(
            fallback
        )

    out = out.withColumn("bangkok_zone", fallback)
    out = out.withColumn("bangkok_zone", F.coalesce(F.col("bangkok_zone"), F.col("zone_code"), F.lit("OTHER")))

    return out


def add_tourist_area_features(df: DataFrame, radius_km: float = TOURIST_RADIUS_KM) -> DataFrame:
    """Flag listings located in high-tourism areas based on landmark radii."""
    distance_cols = [f"distance_to_{k}" for k in TOURIST_LANDMARKS if f"distance_to_{k}" in df.columns]
    if not distance_cols:
        return df.withColumn("is_tourist_area", F.lit(False))

    min_tourist_distance = F.least(*[F.col(c) for c in distance_cols])
    return df.withColumn("is_tourist_area", min_tourist_distance <= F.lit(radius_km))


def add_geospatial_features(df: DataFrame) -> DataFrame:
    """Apply full Geo Intelligence layer transformations for Gold dataset."""
    out = add_landmark_distance_features(df)
    out = add_transit_features(out)
    out = classify_bangkok_zone(out)
    out = add_tourist_area_features(out)
    return out
