import json

from configs.settings import settings
from configs.spark_session import get_spark_session


def main() -> None:
    spark = get_spark_session("validate-zone-classification")
    df = spark.read.parquet(settings.gold_data_path)

    if "bangkok_zone" not in df.columns:
        print("[ERROR] Missing column: bangkok_zone")
        spark.stop()
        return

    print("[ZONE COUNTS]")
    df.groupBy("bangkok_zone").count().orderBy("count", ascending=False).show(20, truncate=False)

    print("[SAMPLE NEIGHBOURHOOD -> ZONE]")
    (
        df.select("neighbourhood", "zone_code", "bangkok_zone")
        .dropna(subset=["neighbourhood"])
        .distinct()
        .orderBy("neighbourhood")
        .show(40, truncate=False)
    )

    mismatch = df.filter(df.zone_code.isNotNull() & (df.zone_code != df.bangkok_zone))
    mismatch_count = mismatch.count()
    print("[MISMATCH zone_code != bangkok_zone]", mismatch_count)
    if mismatch_count > 0:
        mismatch.select("id", "name", "neighbourhood", "zone_code", "bangkok_zone").show(20, truncate=False)

    spark.stop()


if __name__ == "__main__":
    main()
