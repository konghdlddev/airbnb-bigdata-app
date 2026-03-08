import json

from configs.settings import settings
from configs.spark_session import get_spark_session
from jobs.search.build_filters import build_filters
from jobs.search.parse_query import parse_query
from jobs.search.search_listings import search_listings


def main() -> None:
    spark = get_spark_session("zone-integration-validation")
    df = spark.read.parquet(settings.gold_data_path)

    print("[DATASET] Columns:", df.columns)
    df.select("id", "name", "neighbourhood", "zone_code", "room_type", "price", "minimum_nights", "number_of_reviews", "availability_365").show(5, truncate=False)

    queries = [
        "room in sukhumvit",
        "cheap room near rama 9",
        "private room bang na",
        "room in old town",
    ]

    for query in queries:
        parsed = parse_query(query)
        filters = build_filters(parsed)
        rows = search_listings(df, filters).limit(3).toPandas().to_dict(orient="records")

        print("=" * 80)
        print(f"QUERY: {query}")
        print("PARSED:", json.dumps(parsed, ensure_ascii=True))
        print("FILTERS:", json.dumps(filters, ensure_ascii=True))
        print("SAMPLE_ROWS:", json.dumps(rows, ensure_ascii=True))

    spark.stop()


if __name__ == "__main__":
    main()
