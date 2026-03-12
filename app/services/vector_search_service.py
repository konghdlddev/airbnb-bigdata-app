"""Vector (semantic) search over listing embeddings with optional hybrid filters."""
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from configs.settings import settings
from jobs.search.search_listings import OUTPUT_COLUMNS, search_listings_pandas


def _vector_index_exists() -> bool:
    path = Path(settings.vector_index_path)
    if not path.exists():
        return False
    if path.is_file():
        return True
    # directory: ต้องมีไฟล์ parquet (เช่น data.parquet)
    if path.is_dir():
        parquet_files = list(path.glob("*.parquet"))
        return len(parquet_files) > 0
    return False


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load and cache the sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model_name)


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of strings; returns shape (n, dim)."""
    if not texts:
        return np.array([]).reshape(0, 384)
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True)


@lru_cache(maxsize=1)
def _load_gold_pandas() -> pd.DataFrame:
    """Load Gold data as pandas (for vector search - always use pandas, faster than Spark UDF)."""
    path = Path(settings.gold_data_path)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


@lru_cache(maxsize=1)
def _load_vector_index_pandas() -> Optional[pd.DataFrame]:
    """Load vector index once and cache (index doesn't change during session)."""
    path = Path(settings.vector_index_path)
    if not path.exists():
        return None
    # รองรับทั้ง path เป็นไฟล์หรือโฟลเดอร์ (มี data.parquet ข้างใน)
    read_path = path / "data.parquet" if path.is_dir() else path
    if not read_path.exists():
        return None
    df = pd.read_parquet(read_path)
    if "embedding" not in df.columns or "id" not in df.columns:
        return None
    return df


def _vector_search_pandas(query: str, limit: int, filters: Optional[Dict]) -> Optional[pd.DataFrame]:
    """Pandas-based vector search (always used when index exists - faster than Spark UDF)."""
    if not _vector_index_exists():
        return None
    index_df = _load_vector_index_pandas()
    if index_df is None:
        return None
    index_df = index_df.copy()
    gold_df = _load_gold_pandas()
    if filters:
        filtered = search_listings_pandas(gold_df, filters)
        allowed_ids = set(filtered["id"].unique())
        index_df = index_df[index_df["id"].isin(allowed_ids)]
    if index_df.empty:
        return pd.DataFrame()
    query_vec = embed_texts([query.strip() or " "])[0]
    # Vectorized cosine similarity (float64 for stability, avoid overflow)
    embs_list = index_df["embedding"].tolist()
    try:
        embeddings = np.array(embs_list, dtype=np.float64)
    except (ValueError, TypeError):
        embeddings = np.array(
            [np.array(e, dtype=np.float64) if e and len(e) else np.zeros(384, dtype=np.float64) for e in embs_list],
            dtype=np.float64,
        )
    # Ensure 2D: (n, 384) - handle single row or empty edge cases
    if embeddings.ndim == 1:
        embeddings = np.reshape(embeddings, (1, -1))
    # Sanitize: replace nan/inf with 0 to avoid divide-by-zero and overflow
    embeddings = np.nan_to_num(embeddings, nan=0.0, posinf=0.0, neginf=0.0, copy=False)
    q = np.array(query_vec, dtype=np.float64)
    q = np.nan_to_num(q, nan=0.0, posinf=0.0, neginf=0.0, copy=False)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=False)
    norms = np.maximum(norms, 1e-9)
    q_norm = max(float(np.linalg.norm(q)), 1e-9)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        scores = (embeddings @ q) / (norms * q_norm)
    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
    index_df = index_df.copy()
    index_df["similarity_score"] = scores
    top = index_df.nlargest(limit, "similarity_score")
    display_cols = [c for c in OUTPUT_COLUMNS if c in gold_df.columns]
    joined = top[["id", "similarity_score"]].merge(gold_df, on="id", how="inner")
    return joined[[c for c in display_cols if c in joined.columns] + ["similarity_score"]]


def vector_search(
    query: str,
    limit: int = 10,
    filters: Optional[Dict] = None,
):
    """
    Run semantic search: embed query, score by cosine similarity to listing vectors,
    optionally restrict to listings matching filters (hybrid). Returns pandas DataFrame
    with OUTPUT_COLUMNS + similarity_score.

    Always uses pandas path when vector index exists (Spark UDF is too slow for this).
    """
    if _vector_index_exists():
        return _vector_search_pandas(query, limit, filters)
    return None


