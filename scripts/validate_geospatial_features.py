import json

from configs.settings import settings
from configs.spark_session import get_spark_session
from jobs.search.build_filters import build_filters
from jobs.search.parse_query import parse_query
from jobs.search.search_listings import search_listings


def main() -> None:
    spark = get_spark_session("validate-geospatial-features")
    df = spark.read.parquet(settings.gold_data_path)

    print("[COLUMNS]", [
        "distance_to_siam",
        "distance_to_asok",
        "distance_to_silom",
        "distance_to_riverside",
        "distance_to_city_center",
    ])
    df.select(
        "id",
        "name",
        "neighbourhood",
        "zone_code",
        "distance_to_siam",
        "distance_to_asok",
        "distance_to_city_center",
        "price",
    ).show(5, truncate=False)

    queries = [
        "room near siam",
        "cheap room near asok",
        "private room near silom",
    ]

    for q in queries:
        parsed = parse_query(q)
        filters = build_filters(parsed)
        rows = search_listings(df, filters).limit(3).toPandas().to_dict(orient="records")
        print("=" * 80)
        print(f"QUERY: {q}")
        print("PARSED:", json.dumps(parsed, ensure_ascii=True))
        print("FILTERS:", json.dumps(filters, ensure_ascii=True))
        print("SAMPLE_ROWS:", json.dumps(rows, ensure_ascii=True))

    spark.stop()


if __name__ == "__main__":
    main()
