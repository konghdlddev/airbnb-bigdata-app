#!/usr/bin/env bash
set -euo pipefail

GOLD_PATH="${APP_GOLD_DATA_PATH:-data/processed/gold/listings}"
MODEL_PATH="${APP_MODEL_PATH:-models/price_prediction}"

needs_pipeline=0
if [[ ! -d "$GOLD_PATH" ]] || [[ -z "$(find "$GOLD_PATH" -type f 2>/dev/null | head -n 1)" ]]; then
  needs_pipeline=1
fi

if [[ ! -d "$MODEL_PATH" ]] || [[ -z "$(find "$MODEL_PATH" -type f 2>/dev/null | head -n 1)" ]]; then
  needs_pipeline=1
fi

if [[ "$needs_pipeline" -eq 1 ]]; then
  echo "[bootstrap] No processed data/model found. Running full ETL + training..."
  python jobs/etl/ingest_to_minio.py
  python jobs/etl/clean_data.py
  python jobs/etl/feature_engineering.py
  python jobs/etl/build_gold_dataset.py
  python jobs/ml/train_price_model.py
else
  echo "[bootstrap] Found existing gold dataset and model. Skipping ETL/training."
fi

VECTOR_INDEX_PATH="${APP_VECTOR_INDEX_PATH:-data/processed/gold/listing_embeddings}"
if [[ -d "$GOLD_PATH" ]] && [[ -n "$(find "$GOLD_PATH" -type f 2>/dev/null | head -n 1)" ]]; then
  if [[ -d "$VECTOR_INDEX_PATH" ]] && [[ -n "$(find "$VECTOR_INDEX_PATH" -type f 2>/dev/null | head -n 1)" ]]; then
    echo "[bootstrap] Vector index exists. Skipping build_listing_embeddings."
  else
    echo "[bootstrap] Building listing embeddings for vector search (อาจใช้เวลา 5–10 นาทีครั้งแรก)..."
    python jobs/search/build_listing_embeddings.py
  fi
fi

echo "[bootstrap] Starting Streamlit on 0.0.0.0:8501"
exec streamlit run app/main.py --server.address=0.0.0.0 --server.port=8501
