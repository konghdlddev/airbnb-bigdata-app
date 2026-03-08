# Big Data Analytics and Natural Language Search for Airbnb Listings in Bangkok

This project analyzes Airbnb Bangkok listing data using Apache Spark, stores curated data in MinIO (S3-compatible), trains a Spark MLlib model for price prediction, and serves a Streamlit web app with dashboard, search, and prediction pages.

## Tech Stack

- Python 3
- Apache Spark (PySpark)
- MinIO (S3-compatible storage)
- Streamlit
- Docker + Docker Compose

## Project Structure

```text
airbnb-bigdata-app/
  docker-compose.yml
  .env
  README.md
  infra/
    spark/Dockerfile
    streamlit/Dockerfile
  configs/
    settings.py
    spark_session.py
    minio_client.py
    query_rules.json
  data/raw/
    airbnb_bangkok.csv
  jobs/
    etl/
      ingest_to_minio.py
      clean_data.py
      feature_engineering.py
      build_gold_dataset.py
    search/
      parse_query.py
      build_filters.py
      search_listings.py
    ml/
      train_price_model.py
      evaluate_model.py
      predict_price.py
  app/
    main.py
    pages/
      dashboard.py
      natural_language_search.py
      price_prediction.py
    services/
      analytics_service.py
      search_service.py
      prediction_service.py
    components/
      charts.py
      tables.py
      metrics.py
```

## Dataset

Place the dataset at:

`data/raw/airbnb_bangkok.csv`

Expected columns include:

- id, name, host_id, host_name, neighbourhood, latitude, longitude
- room_type, price, minimum_nights, number_of_reviews
- last_review, reviews_per_month
- calculated_host_listings_count, availability_365
- number_of_reviews_ltm

## How It Works

1. ETL pipeline reads raw CSV and performs cleaning and feature engineering.
2. Gold dataset is saved as Parquet to `data/processed/gold/listings/`.
3. Gold dataset and model artifacts are uploaded to MinIO bucket `airbnb-data`.
4. Dataset is enriched with `zone_code` using `configs/bangkok_zone_mapping.json`.
5. Natural language search can detect Bangkok zones (from aliases) and expand them into neighbourhood filters.
6. Price model is trained with Spark MLlib RandomForestRegressor using zone-aware features.
7. Streamlit app runs with 3 pages: dashboard, natural language search, price prediction.

## Zone Search

The Natural Language Search page supports Bangkok zone aliases defined in:

- `configs/bangkok_zone_mapping.json`

When a query mentions a zone alias, the parser returns `zone_code` and the search engine expands it to a neighbourhood list.

Example:

- Query: `room in sukhumvit`
- Parsed zone: `SUK` (Sukhumvit Zone)
- Expanded neighbourhoods: `Vadhana`, `Khlong Toei`, `Phra Khanong`

Spark filtering behavior:

```python
df.filter(df.neighbourhood.isin(["Vadhana", "Khlong Toei", "Phra Khanong"]))
```

Supported example queries:

- `room in sukhumvit`
- `cheap room near rama 9`
- `private room bang na`
- `room in old town`

In Streamlit Natural Language Search, you will see:

- `Parsed Zone` (for example, `Detected Zone: Sukhumvit Zone`)
- `Neighbourhoods used` (the expanded list)
- Parsed query JSON and applied filters JSON
- Human-readable filter logic (`WHERE ...`)

## Run Guide

### 1) Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Dataset file at `data/raw/airbnb_bangkok.csv`

### 2) Start the full stack

```bash
docker compose up --build
```

This command starts:

- `minio` (S3-compatible data lake)
- `spark` (Spark runtime container)
- `streamlit` (web app)

### 3) What happens on first startup

- `streamlit` runs bootstrap logic before app launch.
- If processed data/model are missing, it automatically runs:
  - `jobs/etl/ingest_to_minio.py`
  - `jobs/etl/clean_data.py`
  - `jobs/etl/feature_engineering.py`
  - `jobs/etl/build_gold_dataset.py`
  - `jobs/ml/train_price_model.py`
- Then Streamlit starts.

### 4) Faster subsequent startup

- If both paths already contain files:
  - `data/processed/gold/listings/`
  - `models/price_prediction/`
- ETL/training are skipped automatically and Streamlit starts quickly.

### 5) Open the services

- Streamlit: http://localhost:8501
- MinIO Console: http://localhost:9001

### 6) Common commands

```bash
# Start in detached mode
docker compose up -d --build

# View logs (all services)
docker compose logs -f

# View logs (streamlit only)
docker compose logs -f streamlit

# Stop services
docker compose down
```

### 7) Re-run full ETL + training from scratch

Use this when you changed dataset or pipeline logic and want a clean rebuild:

```bash
rm -rf data/processed/gold/listings models/price_prediction
docker compose up --build
```

### 8) Run jobs manually inside container

```bash
docker compose exec streamlit bash

# inside container
python jobs/etl/clean_data.py
python jobs/etl/feature_engineering.py
python jobs/ml/train_price_model.py
```

### 9) Quick troubleshooting

- App is slow on first run: expected, ETL + model training are running.
- `No such file data/raw/airbnb_bangkok.csv`: verify dataset path and filename.
- Streamlit page opens but no data: check `streamlit` logs for ETL errors.
- MinIO unavailable: verify port `9000/9001` are not occupied by other services.

## MinIO Defaults

- Username: `minioadmin`
- Password: `minioadmin123`
- Bucket: `airbnb-data`

## Notes

- On first startup, the Streamlit container automatically runs ETL and model training before launching the UI.
- On subsequent startups, if `data/processed/gold/listings/` and `models/price_prediction/` already exist, ETL/training are skipped for faster app loading.
- You can run jobs manually inside the Streamlit container if needed.
