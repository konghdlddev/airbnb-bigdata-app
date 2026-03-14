"""
เพิ่มคอลัมน์ bedrooms และ accommodates ใน Gold dataset ถ้ายังไม่มี

ใช้เมื่อ raw/silver ไม่มีสองคอลัมน์นี้ — จะเติมค่าจาก room_type (ค่าประมาณ):
- bedrooms: Entire home/apt -> 2, อื่นๆ -> 1
- accommodates: Entire home/apt -> 4, Private room -> 2, Shared/Hotel -> 2

เขียนไปโฟลเดอร์ชั่วคราวก่อน แล้วค่อยย้ายมาแทนที่ — หลีกเลี่ยงกรณีอ่าน/เขียน path เดียวกันแล้วไฟล์ถูกลบตอน overwrite

รันก่อนเทรนโมเดล: python jobs/etl/add_bedrooms_accommodates_to_gold.py
จากนั้นรัน train_price_model.py (ที่ใช้ bedrooms, accommodates เป็นฟีเจอร์)
"""
import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pyspark.sql import functions as F

from configs.settings import settings
from configs.spark_session import get_spark_session


def add_bedrooms_accommodates(df):
    """เพิ่ม bedrooms และ accommodates ถ้ายังไม่มี (ประมาณจาก room_type)."""
    out = df
    if "bedrooms" not in out.columns:
        out = out.withColumn(
            "bedrooms",
            F.when(F.col("room_type") == "Entire home/apt", F.lit(2)).otherwise(F.lit(1)),
        )
        print("  + added column: bedrooms (derived from room_type)")
    if "accommodates" not in out.columns:
        out = out.withColumn(
            "accommodates",
            F.when(F.col("room_type") == "Entire home/apt", F.lit(4))
            .when(F.col("room_type") == "Private room", F.lit(2))
            .otherwise(F.lit(2)),
        )
        print("  + added column: accommodates (derived from room_type)")
    return out


if __name__ == "__main__":
    spark = get_spark_session("airbnb-add-bedrooms-accommodates")
    path = Path(settings.gold_data_path).resolve()
    path_tmp = path.parent / (path.name + "_tmp")
    path_str = str(path)
    path_tmp_str = str(path_tmp)

    print(f"Reading Gold: {path_str}")
    df = spark.read.parquet(path_str)
    print(f"  columns: {df.columns}")
    df = add_bedrooms_accommodates(df)

    if path_tmp.exists():
        shutil.rmtree(path_tmp)
    print(f"Writing to temp: {path_tmp_str}")
    df.write.mode("overwrite").parquet(path_tmp_str)

    print(f"Replacing Gold: {path_str}")
    if path.exists():
        shutil.rmtree(path)
    shutil.move(path_tmp_str, path_str)

    print("Done. Gold now has bedrooms and accommodates.")
    spark.stop()
