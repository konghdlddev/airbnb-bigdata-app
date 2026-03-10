# สรุป Features และ Logic การทำงานของระบบ

เอกสารนี้สรุปว่าในโปรเจกต์มี feature อะไรบ้าง และแต่ละส่วนทำงานอย่างไรแบบ end-to-end

## 1) ภาพรวมระบบ

ระบบประกอบด้วย 5 แกนหลัก:

1. Big Data ETL ด้วย PySpark
2. Natural Language Search (Rule-based)
3. Price Prediction ด้วย Spark MLlib
4. Recommendation Engine (source-based + zone/price-based)
5. Streamlit Web App (Dashboard, Search, Prediction, Recommendations)

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

ไฟล์หลัก: `jobs/etl/feature_engineering.py`, `jobs/etl/geospatial_features.py`, `configs/geospatial.py`, `configs/geo_intelligence.py`

ฟีเจอร์ที่เพิ่ม:

- `price_category`
- `popularity_score`
- `occupancy_rate`

Geospatial features (Haversine):

- landmark distances เช่น `distance_to_siam`, `distance_to_asok`, `distance_to_silom`, `distance_to_riverside`, `distance_to_bangna`, `distance_to_city_center`
- transit distances เช่น `distance_to_nearest_bts`, `distance_to_nearest_mrt`
- nearest station เช่น `nearest_bts_station`, `nearest_mrt_station`
- walkability flags เช่น `is_walkable_to_bts`, `is_walkable_to_mrt`
- `transit_accessibility_score`
- `bangkok_zone` (smart-zone classification)
- `is_tourist_area`

Landmarks/Geo config ที่ใช้:

- `configs/bangkok_landmarks.json`
- `configs/bangkok_transit.json`
- `configs/bangkok_zones.json`

จากนั้นเขียนผลเป็น Gold Parquet และอัปโหลดไป MinIO

## 3) Natural Language Search Logic

ไฟล์หลัก: `jobs/search/parse_query.py`, `jobs/search/build_filters.py`, `jobs/search/search_listings.py`

### 3.1 Parser ตรวจจับอะไรบ้าง

- `room_type` (เช่น private room, entire home)
- `price_max` / `price range` (under/below/less than, between x-y)
- `location` (pattern `in ...`, `at ...`)
- `zone_code` จาก alias โซน (เช่น sukhumvit -> SUK)
- `landmark` สำหรับ query แบบ `near ...` (เช่น near siam)
- `bedrooms` และ `accommodates`
- `near bts` / `near mrt`
- sort intent เช่น `cheap`, `popular`

รองรับไทยเพิ่มเติม:

- location phrases: `แถว`, `ใกล้`, `ย่าน`, `ที่`
- budget phrases: `ราคา`, `งบ`, `ไม่เกิน`, `บาท`, `ต่อคืน`
- room type aliases ไทย เช่น `ห้องส่วนตัว`, `ห้องรวม`, `ห้องทั้งหลัง`, `ห้องพักโรงแรม`

### 3.2 Intent Rules สำคัญ (แก้ conflict แล้ว)

- ถ้า query มี `in/at` + location:
  - ใช้ exact location filter (`neighbourhood_eq`)
  - ไม่ขยายเป็นโซน
- ถ้า query มี `near`:
  - ใช้ broader logic (zone/landmark distance)
  - ไม่บังคับ exact location
  - landmark distance จะทำงานเฉพาะกรณี `near` เพื่อลด conflict กับ `in/at`

ตัวอย่าง:

- `room in bang na` -> filter เฉพาะ `Bang Na`
- `room near bang na` -> ขยายตามโซน (เช่น Bang Na + พื้นที่เกี่ยวข้อง)

### 3.3 Search Filter ที่รองรับ

- `neighbourhood_eq` (exact match)
- `neighbourhood_in` (จาก zone expansion)
- `price_lte`, `price_gte`
- `room_type`
- `distance_lt` (เช่น `distance_to_siam < 2`)
- `distance_to_nearest_bts_lt`, `distance_to_nearest_mrt_lt`
- `bedrooms_gte`, `accommodates_gte`
- sort ตาม `price` หรือ `popularity_score`

Fallback behavior สำคัญ:

- ถ้า query แนว area-based (`near`/`ใกล้`/`แถว`) แล้วผลลัพธ์เป็น 0 ระบบจะผ่อนเฉพาะเงื่อนไขพื้นที่
- ระบบยังคงเงื่อนไขงบประมาณ/ประเภทห้องที่ผู้ใช้ระบุไว้

คอลัมน์ที่แสดงผลลัพธ์หลัก:

- `id`, `name`, `neighbourhood`, `zone_code`, `bangkok_zone`, `room_type`, `price`, `minimum_nights`, `number_of_reviews`, `distance_to_nearest_bts`, `distance_to_nearest_mrt`, `transit_accessibility_score`, `bedrooms`, `accommodates`

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
  - `bangkok_zone`
- Numeric:
  - `minimum_nights`
  - `number_of_reviews`
  - `reviews_per_month`
  - `availability_365`
  - `distance_to_siam`
  - `distance_to_asok`
  - `distance_to_city_center`
  - `distance_to_nearest_bts`
  - `distance_to_nearest_mrt`
  - `transit_accessibility_score`
  - `is_tourist_area_num`

### 5.2 Pipeline

1. `StringIndexer` สำหรับ `room_type`, `bangkok_zone`
2. `OneHotEncoder`
3. `VectorAssembler`
4. `RandomForestRegressor`

### 5.3 Outlier Handling ก่อนเทรน

ไฟล์: `jobs/ml/train_price_model.py`

ขั้นตอนหลัก:

1. คำนวณ quantile ของราคา (เช่น P25/P75 และ upper quantiles)
2. คำนวณ IQR และสร้างขอบเขตราคาที่ยอมรับได้
3. กรองแถวที่เป็น outlier รุนแรง
4. ทำ winsorization กับค่าปลายหางที่ยังเหลือ
5. ค่อย split และ train model

หมายเหตุ:

- สัดส่วนการแบ่งข้อมูลเทรน: `80/20` (`randomSplit([0.8, 0.2], seed=42)`)
- เป้าหมายคือทำให้ predicted price เสถียรขึ้นและไม่ถูกลากโดยราคา extreme

### 5.4 Prediction Service

- รับ input จากฟอร์ม
- ถ้าไม่มี `bangkok_zone` จะ infer จาก `neighbourhood`
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
- average price by bangkok_zone
- listings count by zone
- price vs nearest BTS
- price vs transit accessibility score
- tourist vs non-tourist pricing
- listings geo map

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

### 6.4 Recommendations (ใหม่)

ไฟล์: `app/pages/recommendations.py`, `app/services/recommendation_service.py`

รองรับ 2 โหมดการแนะนำ:

1. Source-listing mode (อิง listing ต้นทาง)
2. Zone + Price mode (ผู้ใช้เลือกโซนและช่วงราคาโดยตรง)

ฟังก์ชันหลักที่เพิ่ม:

- `get_zone_options()`
- `get_price_bounds()`
- `recommend_by_zone_and_price(...)`

หลักการแนะนำแบบ geo-aware และ budget-aware:

- zone similarity (`bangkok_zone`)
- room type similarity
- price similarity
- distance-to-city-center similarity
- transit accessibility similarity
- tourist-area profile similarity

สำหรับ zone/price mode จะจัดอันดับจากคะแนนรวม (recommendation score) ที่ผสม:

- ความใกล้งบประมาณที่ผู้ใช้เลือก
- ความเข้าถึงระบบขนส่ง (BTS/MRT)
- ความนิยมของ listing

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
- `validate_zone_classification.py`

## 10) เครื่องมือที่ใช้ในงานนี้

Runtime / Infra:

- Docker + Docker Compose
- MinIO (S3-compatible)

Data / ML:

- PySpark
- Spark MLlib (`RandomForestRegressor`)

Application:

- Streamlit (multi-page app)
- Python service layer (`app/services/*`)

Validation / QA commands:

- `python -m compileall -q configs jobs app`
- `docker compose exec -T streamlit python scripts/validate_search_queries.py`
- `docker compose exec -T streamlit python scripts/validate_geospatial_features.py`
- `docker compose exec -T streamlit python scripts/validate_location_intent.py`
- `docker compose exec -T streamlit bash -lc "python jobs/etl/clean_data.py && python jobs/etl/feature_engineering.py && python jobs/etl/build_gold_dataset.py && python jobs/ml/train_price_model.py"`
- `validate_geo_search_queries.py`
- `validate_transit_distance.py`

ใช้สำหรับเช็ก parser/filter/output ตาม scenario สำคัญ
