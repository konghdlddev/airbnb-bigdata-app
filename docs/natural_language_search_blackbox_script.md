# สคริปต์พูดอธิบาย (Blackbox) — Natural Language Search

สคริปต์สำหรับนำเสนอ/อธิบายฟีเจอร์ Natural Language Search แบบ Blackbox ครอบคลุม Logic, Code และ Tools

---

## 1) ภาพรวม Blackbox

**Input:** ข้อความค้นหาภาษาธรรมชาติ เช่น  
`"ห้องส่วนตัวใกล้ BTS สุขุมวิท ราคาไม่เกิน 1500"`

**Output:** ตาราง listings ที่ตรงกับเงื่อนไข พร้อม similarity score (ถ้าใช้ vector search)

**กล่องดำหลัก 3 ขั้นตอน:**
1. **Parse** — แปลงข้อความเป็น structured intent
2. **Build Filters** — สร้างเงื่อนไข WHERE สำหรับการกรอง
3. **Search** — ค้นหาแบบ Vector (semantic) หรือ Filter-only

---

## 2) Logic — ตรรกะการทำงาน

### 2.1 Flow แบบ Blackbox

```
[User Query] 
    → Parse Query (regex + rules + geo_intelligence)
    → Structured Intent (zone_code, room_type, price_max, near_bts_km, ...)
    → Build Filters (dict ของเงื่อนไข WHERE)
    → Search
        ├─ มี Vector Index? 
        │   ├─ ใช่ → Vector Search (embed query, cosine similarity) + Filter (hybrid)
        │   └─ ไม่ → Filter-only Search
        └─ ผลว่าง + มีคำว่า "ใกล้/แถว"? 
            → Fallback: ผ่อนปรนเงื่อนไขพื้นที่ แล้วค้นใหม่
    → [Result DataFrame]
```

### 2.2 สิ่งที่ Parser ตรวจจับได้

| ประเภท | ตัวอย่างคำค้น | Output ใน parsed |
|--------|----------------|------------------|
| room_type | ห้องส่วนตัว, entire home | `room_type: "Private room"` |
| price | ราคาไม่เกิน 1500, งบ 1200 | `price_max: 1500` |
| location/zone | แถวบางนา, ย่านราชเทวี | `zone_code`, `neighbourhood_in` |
| landmark | ใกล้สยาม, near siam | `landmark_key`, `distance_threshold_km` |
| transit | ใกล้ BTS, near MRT | `near_bts_km: 1.0`, `near_mrt_km: 1.0` |
| bedrooms | 2 bedrooms | `bedrooms: 2` |
| accommodates | for 4 people | `accommodates: 4` |
| sort | cheap, นิยม | `sort_intent: "cheap"` หรือ `"popular"` |

### 2.3 Fallback Logic

- ถ้า **ไม่มี vector index** → ใช้ filter-only search
- ถ้า **vector search คืนผลว่าง** → fallback ไป filter-only
- ถ้า **filter-only ได้ผลว่าง** และ query มีคำว่า "ใกล้/แถว" พร้อมเงื่อนไขพื้นที่ → **ผ่อนปรน** (ลบ zone/neighbourhood/distance) แล้วค้นใหม่

---

## 3) Code — โครงสร้างไฟล์และหน้าที่

### 3.1 ไฟล์หลัก

| ไฟล์ | หน้าที่ |
|------|---------|
| `app/pages/natural_language_search.py` | UI: text input, แสดง parsed, filters, filter_logic, ตารางผลลัพธ์ |
| `app/services/search_service.py` | Orchestration: เรียก parse → build_filters → vector_search หรือ filter-only |
| `app/services/vector_search_service.py` | Vector search: embed query, cosine similarity, hybrid filter |
| `jobs/search/parse_query.py` | แปลงข้อความเป็น structured intent (regex + rules) |
| `jobs/search/build_filters.py` | แปลง intent เป็น dict ของ filter conditions |
| `jobs/search/search_listings.py` | กรอง DataFrame (Spark หรือ pandas) ตาม filters |
| `jobs/search/build_listing_embeddings.py` | Offline job: สร้าง embedding index จาก Gold data |

### 3.2 Config ที่ใช้

| Config | ใช้สำหรับ |
|--------|-----------|
| `configs/query_rules.json` | room_type_aliases, price_hints, location_aliases, location_prepositions |
| `configs/bangkok_zones.json` | zone → neighbourhood_aliases, landmark_refs |
| `configs/bangkok_landmarks.json` | landmark aliases สำหรับ detect "ใกล้สยาม" ฯลฯ |
| `configs/bangkok_transit.json` | สถานี BTS/MRT (ใช้ใน ETL สำหรับ distance features) |
| `configs/geo_intelligence.py` | detect_zone_from_query, detect_landmark_from_query, neighbourhood_to_zone_map |
| `configs/zone_mapping.py` | map_neighbourhood_to_zone_code |

### 3.3 การเรียกใช้หลัก

```python
# ใน natural_language_search.py
parsed, filters, filter_logic, result_df = run_natural_language_search(query, limit=10)

# ใน search_service.py
parsed = parse_query(query)
filters = build_filters(parsed)
result_pdf = vector_search(query, limit=limit, filters=filters)  # หรือ filter-only
```

### 3.4 รายละเอียดการทำงานของ `vector_search_service.py`

ไฟล์ `app/services/vector_search_service.py` ทำหน้าที่ **Vector (Semantic) Search** — ค้นหาจากความหมายของข้อความโดยใช้ embedding และ cosine similarity

#### 3.4.1 ฟังก์ชันหลัก

| ฟังก์ชัน | หน้าที่ |
|----------|---------|
| `_vector_index_exists()` | ตรวจสอบว่ามีไฟล์/โฟลเดอร์ vector index ที่ path ที่กำหนดหรือไม่ |
| `get_embedding_model()` | โหลดโมเดล sentence-transformers (cache ด้วย `@lru_cache`) |
| `embed_texts(texts)` | แปลง list ของข้อความเป็น numpy array ของ vectors (shape n×384) |
| `_make_cos_sim_fn(broadcast_vec)` | สร้างฟังก์ชันคำนวณ cosine similarity สำหรับ Spark UDF |
| `_vector_search_pandas(...)` | Vector search แบบ pandas (เมื่อ `USE_PANDAS=1` หรือไม่มี Java) |
| `vector_search(...)` | ฟังก์ชันหลัก — รับ query, limit, filters แล้วคืน DataFrame |

#### 3.4.2 Flow การทำงานของ `vector_search()`

```
1. ตรวจสอบ _use_pandas()
   ├─ ใช่ → เรียก _vector_search_pandas() แล้ว return
   └─ ไม่ → ใช้ Spark path ต่อ

2. ตรวจสอบ _vector_index_exists()
   └─ ไม่มี → return None (ให้ search_service fallback ไป filter-only)

3. โหลด vector index
   spark.read.parquet(settings.vector_index_path)
   └─ ต้องมี columns: id, embedding

4. Hybrid Filter (ถ้ามี filters)
   ├─ โหลด Gold DataFrame
   ├─ search_listings(gold_df, filters) → filtered_df
   ├─ index_df.join(filtered_df.select("id"), "id", "inner")
   └─ เหลือเฉพาะ listings ที่ผ่าน filter

5. Embed query
   query_vec = embed_texts([query])[0]  # vector 384 มิติ

6. คำนวณ Cosine Similarity (Spark)
   ├─ broadcast query_vec ไปทุก worker
   ├─ UDF: cos_sim(emb) = dot(a,b) / (||a|| * ||b||)
   ├─ index_df.withColumn("similarity_score", cos_udf(embedding))
   └─ orderBy(similarity_score.desc()).limit(limit)

7. Join กับ Gold เพื่อได้ columns แสดงผล
   top.join(gold_df, "id", "inner").select(OUTPUT_COLUMNS, similarity_score)

8. return joined.toPandas()
```

#### 3.4.3 Flow การทำงานของ `_vector_search_pandas()`

ใช้เมื่อไม่มี Spark/Java (`USE_PANDAS=1`):

```
1. ตรวจสอบ _vector_index_exists() → ไม่มี return None

2. โหลด index: pd.read_parquet(vector_index_path)
   - รองรับทั้ง path เป็นไฟล์หรือโฟลเดอร์ (อ่านโฟลเดอร์ได้)

3. ตรวจสอบ columns: id, embedding

4. โหลด Gold DataFrame

5. Hybrid Filter (ถ้ามี filters)
   search_listings_pandas(gold_df, filters) → allowed_ids
   index_df = index_df[index_df["id"].isin(allowed_ids)]

6. Embed query
   query_vec = embed_texts([query])[0]

7. คำนวณ similarity แบบ pandas
   index_df["similarity_score"] = index_df["embedding"].apply(cos_sim)
   - cos_sim(emb) = dot(emb, query_vec) / (||emb|| * ||query_vec||)

8. เรียงและตัด top
   top = index_df.nlargest(limit, "similarity_score")

9. Join กับ Gold
   top[["id","similarity_score"]].merge(gold_df, on="id", how="inner")

10. return DataFrame ที่มี OUTPUT_COLUMNS + similarity_score
```

#### 3.4.4 สูตร Cosine Similarity

```
cos_sim(a, b) = (a · b) / (||a|| × ||b||)
```

- `a` = embedding ของ listing (จาก vector index)
- `b` = embedding ของ query
- ค่าอยู่ระหว่าง -1 ถึง 1 ยิ่งใกล้ 1 ยิ่งมีความหมายคล้ายกัน
- กรณี emb เป็น None หรือว่าง → return 0.0
- กรณี norm < 1e-9 (เกือบศูนย์) → return 0.0 ป้องกัน division by zero

#### 3.4.5 โครงสร้าง Vector Index (Parquet)

| Column | ประเภท | ความหมาย |
|--------|--------|----------|
| `id` | int64 | listing id (FK ไป Gold) |
| `embedding` | list[float] | vector 384 มิติ จาก sentence-transformers |

สร้างโดย `jobs/search/build_listing_embeddings.py` จาก `search_text` = name + neighbourhood + room_type + bangkok_zone

#### 3.4.6 การเลือก Spark vs Pandas

| เงื่อนไข | ใช้ |
|----------|-----|
| `_use_pandas()` = True | `_vector_search_pandas()` |
| `_use_pandas()` = False | Spark path (ต้องมี Java) |

---

## 4) Tools — เครื่องมือและไลบรารี

### 4.1 ไลบรารีหลัก

| Library | ใช้สำหรับ |
|---------|-----------|
| **sentence-transformers** | โมเดล `paraphrase-multilingual-MiniLM-L12-v2` สำหรับ embed ข้อความ → vector 384 มิติ |
| **numpy** | คำนวณ cosine similarity ระหว่าง query vector กับ listing embeddings |
| **pandas** | โหลด Gold data, กรอง, join กับ vector index (เมื่อ USE_PANDAS=1) |
| **pyarrow** | อ่าน/เขียน Parquet (vector index) |
| **PySpark** | กรอง Gold DataFrame และ vector index (เมื่อมี Java) |
| **re (regex)** | ดึง room_type, price, location, bedrooms, accommodates จาก query |
| **Streamlit** | UI: text_input, st.code, show_dataframe |

### 4.2 Environment Variables

| ตัวแปร | ความหมาย |
|--------|----------|
| `APP_GOLD_DATA_PATH` | path ของ Gold Parquet |
| `APP_VECTOR_INDEX_PATH` | path ของ listing embeddings (Parquet) |
| `APP_EMBEDDING_MODEL` | ชื่อ model สำหรับ embedding |
| `USE_PANDAS` | 1 = ใช้ pandas แทน Spark (เมื่อไม่มี Java) |

---

## 5) สรุปประโยคสำหรับพูด (Elevator Pitch)

> "Natural Language Search รับข้อความค้นหาภาษาธรรมชาติ เช่น 'ห้องส่วนตัวใกล้ BTS สุขุมวิท ราคาไม่เกิน 1500' แล้วผ่าน Parser ที่ใช้ regex และ config rules แปลงเป็น structured intent เช่น zone_code, room_type, price_max, near_bts_km จากนั้น build_filters แปลงเป็นเงื่อนไข WHERE ถ้ามี vector index ระบบจะ embed query แล้วคำนวณ cosine similarity กับ listing embeddings (semantic search) พร้อมกรองด้วย filters (hybrid) ถ้าไม่มี vector index จะใช้ filter-only search แทน ผลลัพธ์คือตาราง listings ที่ตรงกับเงื่อนไข"

---

## 6) ไดอะแกรม Blackbox (สำหรับอธิบาย)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Natural Language Search                        │
├─────────────────────────────────────────────────────────────────┤
│  INPUT: "ห้องส่วนตัวใกล้ BTS สุขุมวิท ราคาไม่เกิน 1500"           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  BLACKBOX 1: Parse Query                                          │
│  - regex + query_rules.json + geo_intelligence                   │
│  OUTPUT: {zone_code, room_type, price_max, near_bts_km, ...}     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  BLACKBOX 2: Build Filters                                        │
│  - build_filters(parsed) → {neighbourhood_in, price_lte, ...}     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  BLACKBOX 3: Search                                                │
│  - มี vector index? → Vector Search + Filter (hybrid)             │
│  - ไม่มี? → Filter-only (search_listings)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  OUTPUT: DataFrame (listings + similarity_score ถ้าใช้ vector)   │
└─────────────────────────────────────────────────────────────────┘
```

---

*เอกสารนี้ใช้สำหรับนำเสนอหรืออธิบายฟีเจอร์ Natural Language Search แบบ Blackbox*
