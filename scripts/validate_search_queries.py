import json

from configs.settings import settings
from configs.spark_session import get_spark_session
from jobs.search.build_filters import build_filters
from jobs.search.parse_query import parse_query
from jobs.search.search_listings import search_listings


def main() -> None:
    queries = [
        "Room 2000 in bang kapi",
        "private room under 1500",
        "entire home in ratchathewi",
        "cheap room in bang na",
        "room below 2500 in sukhumvit",
    ]

    spark = get_spark_session("nl-search-validation")
    df = spark.read.parquet(settings.gold_data_path)

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
