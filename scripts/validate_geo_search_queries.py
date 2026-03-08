import json

from configs.settings import settings
from configs.spark_session import get_spark_session
from jobs.search.build_filters import build_filters
from jobs.search.parse_query import parse_query
from jobs.search.search_listings import search_listings


QUERIES = [
    "cheap room near bts",
    "private room near mrt under 1500",
    "room near siam",
    "entire home in sukhumvit",
    "room in bang na",
    "room near bang na",
    "2 bedroom room near asok for 4 people",
]


def main() -> None:
    spark = get_spark_session("validate-geo-search-queries")
    df = spark.read.parquet(settings.gold_data_path)

    for q in QUERIES:
        parsed = parse_query(q)
        filters = build_filters(parsed)
        rows = search_listings(df, filters).limit(5).toPandas().to_dict(orient="records")

        print("=" * 100)
        print("QUERY:", q)
        print("PARSED:", json.dumps(parsed, ensure_ascii=True))
        print("FILTERS:", json.dumps(filters, ensure_ascii=True))
        print("TOP_5:", json.dumps(rows, ensure_ascii=True))

    spark.stop()


if __name__ == "__main__":
    main()
