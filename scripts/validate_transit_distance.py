from configs.settings import settings
from configs.spark_session import get_spark_session


def main() -> None:
    spark = get_spark_session("validate-transit-distance")
    df = spark.read.parquet(settings.gold_data_path)

    required = [
        "distance_to_nearest_bts",
        "distance_to_nearest_mrt",
        "nearest_bts_station",
        "nearest_mrt_station",
        "transit_accessibility_score",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print("[ERROR] Missing columns:", missing)
        spark.stop()
        return

    print("[TRANSIT METRICS SUMMARY]")
    df.select(
        "distance_to_nearest_bts",
        "distance_to_nearest_mrt",
        "transit_accessibility_score",
    ).summary("count", "min", "25%", "50%", "75%", "max", "mean").show(truncate=False)

    print("[TOP 20 CLOSEST TO BTS]")
    (
        df.select("id", "name", "neighbourhood", "nearest_bts_station", "distance_to_nearest_bts", "price")
        .orderBy("distance_to_nearest_bts")
        .show(20, truncate=False)
    )

    print("[TOP 20 CLOSEST TO MRT]")
    (
        df.select("id", "name", "neighbourhood", "nearest_mrt_station", "distance_to_nearest_mrt", "price")
        .orderBy("distance_to_nearest_mrt")
        .show(20, truncate=False)
    )

    print("[WALKABLE COUNTS (< 1 km)]")
    walkable_bts = df.filter(df.distance_to_nearest_bts <= 1.0).count()
    walkable_mrt = df.filter(df.distance_to_nearest_mrt <= 1.0).count()
    total = df.count()
    print("walkable_bts:", walkable_bts, "/", total)
    print("walkable_mrt:", walkable_mrt, "/", total)

    spark.stop()


if __name__ == "__main__":
    main()
