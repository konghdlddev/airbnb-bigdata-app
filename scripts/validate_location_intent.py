import json

from configs.settings import settings
from configs.spark_session import get_spark_session
from jobs.search.build_filters import build_filters
from jobs.search.parse_query import parse_query
from jobs.search.search_listings import search_listings


def main() -> None:
    queries = [
        "near bangna",
        "in bang na",
        "room near bang na",
        "room in bang na",
    ]

    spark = get_spark_session("validate-location-intent")
    df = spark.read.parquet(settings.gold_data_path)

    for q in queries:
        parsed = parse_query(q)
        filters = build_filters(parsed)
        rows = search_listings(df, filters).limit(5).toPandas().to_dict(orient="records")
        neighbourhoods = sorted({r["neighbourhood"] for r in rows}) if rows else []

        print("=" * 80)
        print("QUERY:", q)
        print("PARSED:", json.dumps(parsed, ensure_ascii=True))
        print("FILTERS:", json.dumps(filters, ensure_ascii=True))
        print("TOP5_NEIGHBOURHOODS:", json.dumps(neighbourhoods, ensure_ascii=True))

    spark.stop()


if __name__ == "__main__":
    main()
