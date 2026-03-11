# สรุป Features และ Logic การทำงานของระบบ

เอกสารนี้สรุป feature หลักและ logic การทำงานแบบ end-to-end

## 1) ภาพรวมระบบ

ระบบประกอบด้วย 5 แกนหลัก:

1. **Big Data ETL** ด้วย PySpark
2. **Natural Language Search** (Rule-based + Vector Search)
3. **Price Prediction** ด้วย Spark MLlib
4. **Recommendation Engine** (source-based + zone/price-based)
5. **Streamlit Web App** (Dashboard, Search, Prediction, Recommendations)

โครงสร้างข้อมูลหลัก:

| ประเภท | Path |
|--------|------|
| Raw CSV | `data/raw/airbnb_bangkok.csv` |
| Silver Parquet | `data/processed/silver/listings` |
| Gold Parquet | `data/processed/gold/listings` |
| Vector Index | `data/processed/gold/listing_embeddings` |
| Model | `models/price_prediction` |
| MinIO bucket | `airbnb-data` |

## 2) Data Pipeline (ETL) Logic

### 2.1 Ingest + Cleaning

ไฟล์: `jobs/etl/ingest_to_minio.py`, `jobs/etl/clean_data.py`

ลำดับ: อ่าน CSV → normalize schema → แปลงชนิดข้อมูล → clean string → กรองข้อมูลไม่ถูกต้อง → เติม zone_code จาก mapping → เขียน Silver Parquet

### 2.2 Feature Engineering

ไฟล์: `jobs/etl/feature_engineering.py`, `jobs/etl/geospatial_features.py`

ฟีเจอร์ที่เพิ่ม: `price_category`, `popularity_score`, `occupancy_rate`, landmark distances, transit distances, `bangkok_zone`, `is_tourist_area`, `transit_accessibility_score`

Config: `configs/bangkok_landmarks.json`, `configs/bangkok_transit.json`, `configs/bangkok_zones.json`

## 3) Natural Language Search Logic

### 3.1 สถาปัตยกรรม (Hybrid: Vector + Filter)

- **Vector Search:** เมื่อมี listing embeddings ระบบจะ embed query แล้วคำนวณ cosine similarity กับ listing vectors (semantic search)
- **Filter:** ใช้ parsed query สร้าง structured filters (zone, price, room_type ฯลฯ) กรองก่อนหรือร่วมกับ vector search
- **Fallback:** ถ้าไม่มี vector index หรือ vector search ได้ผลว่าง จะใช้ rule-based filter เท่านั้น

ไฟล์หลัก: `app/services/vector_search_service.py`, `app/services/search_service.py`, `jobs/search/parse_query.py`, `jobs/search/build_filters.py`, `jobs/search/search_listings.py`

### 3.2 Vector Index (Offline)

ไฟล์: `jobs/search/build_listing_embeddings.py`

- อ่าน Gold Parquet
- สร้าง `search_text` = name + neighbourhood + room_type + bangkok_zone
- ใช้ `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` encode เป็น vector
- เขียน Parquet ที่ `data/processed/gold/listing_embeddings`
- **ไม่ต้องใช้ Spark/Java** — ใช้ pandas + pyarrow

### 3.3 Parser ตรวจจับ

- `room_type`, `price_max`/`price range`, `location`, `zone_code`, `landmark`, `bedrooms`, `accommodates`
- `near bts` / `near mrt`, sort intent (`cheap`, `popular`)
- รองรับไทย: `แถว`, `ใกล้`, `ย่าน`, `ราคา`, `งบ`, `ไม่เกิน`, `บาท`

### 3.4 Search Filter ที่รองรับ

`neighbourhood_eq`, `neighbourhood_in`, `price_lte`/`price_gte`, `room_type`, `distance_lt`, `distance_to_nearest_bts_lt`, `distance_to_nearest_mrt_lt`, `bedrooms_gte`, `accommodates_gte`, sort by `price` หรือ `popularity_score`

## 4) Zone Mapping Logic

ไฟล์: `configs/bangkok_zone_mapping.json`, `configs/zone_mapping.py`, `configs/geo_intelligence.py`

ใช้สำหรับ: map neighbourhood → zone_code ตอน ETL, detect zone จาก alias ตอน parse, expand zone → neighbourhood ตอน search

## 5) Price Prediction Logic

ไฟล์: `jobs/ml/train_price_model.py`, `app/services/prediction_service.py`

### 5.1 Features

Categorical: `room_type`, `bangkok_zone`  
Numeric: `minimum_nights`, `number_of_reviews`, `reviews_per_month`, `availability_365`, distance features, `transit_accessibility_score`, `is_tourist_area_num`

### 5.2 Pipeline

StringIndexer → OneHotEncoder → VectorAssembler → RandomForestRegressor

### 5.3 ข้อจำกัด

- **ต้องใช้ Spark/Java** — ถ้ารันแบบ `USE_PANDAS=1` (ไม่มี Java) หน้า Price Prediction จะแสดง error
- รันผ่าน Docker หรือติดตั้ง Java เพื่อใช้ฟีเจอร์นี้

## 6) Recommendation Logic

ไฟล์: `app/pages/recommendations.py`, `app/services/recommendation_service.py`

2 โหมด:

1. **Source-listing:** เลือก listing ต้นทาง → หาที่พักคล้ายกัน (zone, room_type, price, distance, transit, tourist-area similarity)
2. **Zone + Price:** เลือกโซนและช่วงราคา → จัดอันดับจาก budget closeness, transit accessibility, popularity

**ไม่ใช้ ML model** — ใช้ rule-based scoring

## 7) Pandas Fallback (เมื่อไม่มี Java)

เมื่อ `USE_PANDAS=1` ใน `.env` หรือ Java ไม่พร้อมใช้งาน:

- `analytics_service` ใช้ `pd.read_parquet` แทน Spark
- `search_listings_pandas` แทน `search_listings`
- `vector_search` ใช้ `_vector_search_pandas` (pandas + numpy)
- `recommendation_service` ใช้ pandas logic
- **Price Prediction** ไม่ทำงาน — แสดง error แนะนำให้ติดตั้ง Java หรือใช้ Docker

## 8) Streamlit UI Logic

### 8.1 เมนู (st.navigation)

ไฟล์: `app/main.py`

กำหนดเมนูเอง: หน้าหลัก, แดชบอร์ด, ค้นหาภาษาธรรมชาติ, ทำนายราคา, แนะนำที่พัก

### 8.2 หน้า Dashboard

ไฟล์: `app/pages/dashboard.py`

แสดง KPIs, charts (neighbourhood, room type, price vs distance, zone, BTS/MRT, tourist area), geo map

### 8.3 Natural Language Search

ไฟล์: `app/pages/natural_language_search.py`

แสดง preview, parsed query, filters, filter logic, ตารางผลลัพธ์ (พร้อม `similarity_score` ถ้าใช้ vector search)

### 8.4 Price Prediction

ไฟล์: `app/pages/price_prediction.py`

ฟอร์ม area, room_type, minimum_nights, reviews, availability → แสดงราคาที่คาดการณ์ (ต้องมี Java/Spark)

### 8.5 Recommendations

ไฟล์: `app/pages/recommendations.py`

2 tabs: เลือกตามโซนและราคา, เลือกจากประกาศต้นทาง

## 9) Docker Runtime Logic

ไฟล์: `docker-compose.yml`, `scripts/bootstrap.sh`, `infra/streamlit/Dockerfile`

### Services

- **minio:** Object storage (S3-compatible)
- **spark:** Spark runtime (tail -f)
- **streamlit:** แอปหลัก (มี Java ใน image)

### Bootstrap

1. ถ้าไม่มี gold/model → รัน ETL + train model
2. ถ้ามี gold และ **ไม่มี** vector index → รัน `build_listing_embeddings.py` (ครั้งแรกอาจใช้เวลา 5–10 นาที)
3. ถ้ามี vector index แล้ว → ข้าม build embeddings
4. สตาร์ท Streamlit ที่ `0.0.0.0:8501`

## 10) คำสั่งใช้งาน

### รัน Docker (แนะนำ — มี Java)

```bash
docker-compose up --build
```

### รัน Local (ต้องมี Java หรือใช้ USE_PANDAS=1)

```bash
# ติดตั้ง dependencies
pip install -r requirements.txt

# Build vector index (ใช้ pandas, ไม่ต้องมี Java)
python jobs/search/build_listing_embeddings.py

# รัน Streamlit
streamlit run app/main.py
```

### Environment Variables สำคัญ

| ตัวแปร | ความหมาย |
|--------|----------|
| `USE_PANDAS` | 1/true = ใช้ pandas แทน Spark (เมื่อไม่มี Java) |
| `APP_GOLD_DATA_PATH` | path ของ Gold Parquet |
| `APP_VECTOR_INDEX_PATH` | path ของ listing embeddings |
| `APP_EMBEDDING_MODEL` | ชื่อ model สำหรับ embedding |

## 11) เครื่องมือที่ใช้

- **Runtime:** Docker, MinIO, PySpark, Python
- **ML/Embedding:** Spark MLlib, sentence-transformers
- **App:** Streamlit
- **Validation:** scripts ใน `scripts/` เช่น `validate_search_queries.py`, `validate_geo_search_queries.py`
