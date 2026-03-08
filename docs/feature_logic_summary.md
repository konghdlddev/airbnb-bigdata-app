# สรุป Features และ Logic การทำงานของระบบ

เอกสารนี้สรุปว่าในโปรเจกต์มี feature อะไรบ้าง และแต่ละส่วนทำงานอย่างไรแบบ end-to-end

## 1) ภาพรวมระบบ

ระบบประกอบด้วย 4 แกนหลัก:

1. Big Data ETL ด้วย PySpark
2. Natural Language Search (Rule-based)
3. Price Prediction ด้วย Spark MLlib
4. Streamlit Web App (Dashboard, Search, Prediction)

โครงสร้างข้อมูลหลัก:

- Raw CSV: `data/raw/airbnb_bangkok.csv`
- Silver Parquet: `data/processed/silver/listings`
- Gold Parquet: `data/processed/gold/listings`
- Model: `models/price_prediction`
- MinIO bucket: `airbnb-data`

## 2) Data Pipeline (ETL) Logic

### 2.1 Ingest + Cleaning

ไฟล์หลัก: `jobs/etl/ingest_to_minio.py`, `jobs/etl/clean_data.py`

ลำดับการทำงาน:

1. อ่านไฟล์ CSV โดยเปิด `header=true` และ `inferSchema=true`
2. ตัดคอลัมน์ index ที่หลุดมาจากไฟล์ (เช่น `_c0`, `Unnamed: 0`)
3. Normalize schema ให้ชื่อคอลัมน์อยู่ในรูปแบบมาตรฐาน
4. แปลงชนิดข้อมูลตัวเลข (price, lat/lng, reviews, availability ฯลฯ)
5. Trim/clean string columns
6. Normalize `room_type` และ `neighbourhood`
7. กรองข้อมูลไม่ถูกต้อง:
   - price ต้องไม่ null และ > 0
   - latitude/longitude ต้องอยู่ในช่วง valid
8. เติมค่า null บางคอลัมน์ด้วยค่า default
9. เติม `zone_code` จาก mapping (`configs/bangkok_zone_mapping.json`)
10. เขียนผลเป็น Silver Parquet

### 2.2 Feature Engineering

ไฟล์หลัก: `jobs/etl/feature_engineering.py`, `configs/geospatial.py`

ฟีเจอร์ที่เพิ่ม:

- `price_category`
- `popularity_score`
- `occupancy_rate`

Geospatial features (Haversine):

- `distance_to_siam`
- `distance_to_asok`
- `distance_to_silom`
- `distance_to_riverside`
- `distance_to_city_center`

Landmarks ที่ใช้:

- Siam Center
- Asok
- Silom
- Riverside (Chao Phraya)
- Bangkok City Center

จากนั้นเขียนผลเป็น Gold Parquet และอัปโหลดไป MinIO

## 3) Natural Language Search Logic

ไฟล์หลัก: `jobs/search/parse_query.py`, `jobs/search/build_filters.py`, `jobs/search/search_listings.py`

### 3.1 Parser ตรวจจับอะไรบ้าง

- `room_type` (เช่น private room, entire home)
- `price_max` (under/below/less than และตัวเลขในประโยค)
- `location` (pattern `in ...`, `at ...`)
- `zone_code` จาก alias โซน (เช่น sukhumvit -> SUK)
- `landmark` สำหรับ query แบบ `near ...` (เช่น near siam)

### 3.2 Intent Rules สำคัญ (แก้ conflict แล้ว)

- ถ้า query มี `in/at` + location:
  - ใช้ exact location filter (`neighbourhood_eq`)
  - ไม่ขยายเป็นโซน
- ถ้า query มี `near`:
  - ใช้ broader logic (zone/landmark distance)
  - ไม่บังคับ exact location

ตัวอย่าง:

- `room in bang na` -> filter เฉพาะ `Bang Na`
- `room near bang na` -> ขยายตามโซน (เช่น Bang Na + พื้นที่เกี่ยวข้อง)

### 3.3 Search Filter ที่รองรับ

- `neighbourhood_eq` (exact match)
- `neighbourhood_in` (จาก zone expansion)
- `price_lte`
- `room_type`
- `distance_lt` (เช่น `distance_to_siam < 2`)

คอลัมน์ที่แสดงผลลัพธ์หลัก:

- `id`, `name`, `neighbourhood`, `zone_code`, `room_type`, `price`, `minimum_nights`, `number_of_reviews`

## 4) Zone Mapping Logic

ไฟล์หลัก: `configs/bangkok_zone_mapping.json`, `configs/zone_mapping.py`

ใช้สำหรับ:

1. map neighbourhood -> `zone_code` ตอน ETL
2. detect zone จาก alias ตอน parse query
3. expand `zone_code` -> รายชื่อ neighbourhood ตอน search

## 5) Price Prediction Logic

ไฟล์หลัก: `jobs/ml/train_price_model.py`, `app/services/prediction_service.py`

### 5.1 Features ที่ใช้เทรนโมเดล

- Categorical:
  - `room_type`
  - `zone_code`
- Numeric:
  - `minimum_nights`
  - `number_of_reviews`
  - `availability_365`
  - `distance_to_siam`
  - `distance_to_asok`
  - `distance_to_city_center`

### 5.2 Pipeline

1. `StringIndexer` สำหรับ `room_type`, `zone_code`
2. `OneHotEncoder`
3. `VectorAssembler`
4. `RandomForestRegressor`

### 5.3 Prediction Service

- รับ input จากฟอร์ม
- ถ้าไม่มี `zone_code` จะ map จาก `neighbourhood`
- distance features ใช้ค่าเฉลี่ยตาม neighbourhood (fallback เป็นค่าเฉลี่ย global)
- ส่งเข้า model แล้วคืนราคา predicted

## 6) Streamlit UI Logic

### 6.1 Dashboard

ไฟล์: `app/pages/dashboard.py`

แสดง:

- total listings
- average price
- listings by neighbourhood
- room type distribution
- average price vs distance to city center

### 6.2 Natural Language Search

ไฟล์: `app/pages/natural_language_search.py`

แสดง:

- preview ข้อมูล processed
- parsed query JSON
- applied filters JSON
- filter logic (`WHERE ...`)
- Parsed Zone / Parsed Landmark
- ตารางผลลัพธ์

### 6.3 Price Prediction

ไฟล์: `app/pages/price_prediction.py`

- ฟอร์มแบบ user-friendly
- area dropdown จากข้อมูลจริง
- แบ่ง section เป็น Listing Details / Popularity / Availability
- แสดงราคาที่คาดการณ์ต่อคืน

## 7) Docker Runtime Logic

ไฟล์: `docker-compose.yml`, `scripts/bootstrap.sh`

services:

- `minio`
- `spark`
- `streamlit`

bootstrap behavior:

- รอบแรก: รัน ETL + train model ก่อนเปิด Streamlit
- รอบถัดไป: ถ้ามี gold/model แล้ว จะ skip ขั้นตอนหนักเพื่อให้เปิดเร็ว

## 8) คำสั่งใช้งานที่พบบ่อย

เริ่มระบบ:

```bash
docker compose up --build
```

ดู log ของแอป:

```bash
docker compose logs -f streamlit
```

รีรัน ETL + train ใหม่:

```bash
docker compose exec -T streamlit bash -lc "python jobs/etl/clean_data.py && python jobs/etl/feature_engineering.py && python jobs/etl/build_gold_dataset.py && python jobs/ml/train_price_model.py"
```

## 9) Validation Scripts (สำหรับ debug)

อยู่ในโฟลเดอร์ `scripts/` เช่น:

- `validate_search_queries.py`
- `validate_zone_integration.py`
- `validate_geospatial_features.py`
- `validate_location_intent.py`

ใช้สำหรับเช็ก parser/filter/output ตาม scenario สำคัญ
