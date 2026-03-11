"""
Build vector embeddings for listings from Gold dataset for semantic search.
Writes (id, embedding) Parquet to vector_index_path for use by vector_search_service.
Uses pandas + pyarrow (no Spark/Java required).
"""
import sys
from pathlib import Path

# Add project root to path so configs/app imports work when run directly
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd

from configs.settings import settings

BATCH_SIZE = 512


def main():
    gold_path = Path(settings.gold_data_path)
    if not gold_path.exists():
        print(f"[build_listing_embeddings] Gold path not found: {gold_path}")
        return

    df = pd.read_parquet(gold_path)
    for col in ["id", "name", "neighbourhood", "room_type"]:
        if col not in df.columns:
            raise ValueError(f"Gold missing column: {col}")
    if "bangkok_zone" not in df.columns:
        df["bangkok_zone"] = ""

    df["search_text"] = (
        df["name"].fillna("").astype(str)
        + " "
        + df["neighbourhood"].fillna("").astype(str)
        + " "
        + df["room_type"].fillna("").astype(str)
        + " "
        + df["bangkok_zone"].fillna("").astype(str)
    ).str.strip()

    if df.empty:
        print("[build_listing_embeddings] No rows in gold. Skipping.")
        return

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(settings.embedding_model_name)

    all_ids = df["id"].astype("int64").tolist()
    texts = df["search_text"].fillna("").tolist()
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vecs = model.encode(batch, convert_to_numpy=True)
        for j in range(len(batch)):
            all_embeddings.append(vecs[j].astype(float).tolist())

    out_df = pd.DataFrame({"id": all_ids, "embedding": all_embeddings})

    out_path = Path(settings.vector_index_path)
    out_path.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(out_path / "data.parquet", index=False)
    print(f"[build_listing_embeddings] Wrote {len(out_df)} embeddings to {out_path}")


if __name__ == "__main__":
    main()
