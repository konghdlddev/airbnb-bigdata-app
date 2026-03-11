"""Vector (semantic) search over listing embeddings with optional hybrid filters."""
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType

from app.services.analytics_service import _spark, _use_pandas, load_gold_dataframe
from configs.settings import settings
from jobs.search.search_listings import OUTPUT_COLUMNS, search_listings, search_listings_pandas


def _vector_index_exists() -> bool:
    path = Path(settings.vector_index_path)
    if not path.exists():
        return False
    if path.is_file():
        return True
    return path.is_dir() and any(path.iterdir())


def _make_cos_sim_fn(broadcast_vec):
    q = broadcast_vec.value

    def cos_sim(emb):
        if emb is None or not emb:
            return 0.0
        a = np.array(emb, dtype=float)
        b = np.array(q, dtype=float)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na < 1e-9 or nb < 1e-9:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    return cos_sim


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


def _vector_search_pandas(query: str, limit: int, filters: Optional[Dict]) -> Optional[pd.DataFrame]:
    """Pandas-based vector search when Spark unavailable."""
    if not _vector_index_exists():
        return None
    path = Path(settings.vector_index_path)
    if path.is_dir():
        index_df = pd.read_parquet(path)
    else:
        index_df = pd.read_parquet(path)
    if "embedding" not in index_df.columns or "id" not in index_df.columns:
        return None
    gold_df = load_gold_dataframe()
    if filters:
        filtered = search_listings_pandas(gold_df, filters)
        allowed_ids = set(filtered["id"].unique())
        index_df = index_df[index_df["id"].isin(allowed_ids)]
    query_vec = embed_texts([query.strip() or " "])[0]
    def cos_sim(emb):
        if emb is None or (isinstance(emb, (list, np.ndarray)) and len(emb) == 0):
            return 0.0
        a = np.array(emb, dtype=float)
        b = np.array(query_vec, dtype=float)
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-9 or nb < 1e-9:
            return 0.0
        return float(np.dot(a, b) / (na * nb))
    index_df = index_df.copy()
    index_df["similarity_score"] = index_df["embedding"].apply(cos_sim)
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
    """
    if _use_pandas():
        return _vector_search_pandas(query, limit, filters)
    if not _vector_index_exists():
        return None
    spark = _spark()
    index_df = spark.read.parquet(settings.vector_index_path)
    if "embedding" not in index_df.columns or "id" not in index_df.columns:
        return None

    if filters:
        gold_df = load_gold_dataframe()
        filtered_df = search_listings(gold_df, filters).select("id").distinct()
        index_df = index_df.join(filtered_df, "id", "inner")

    query_vec = embed_texts([query.strip() or " "])[0]
    broadcast_vec = spark.sparkContext.broadcast(query_vec.tolist())

    from pyspark.sql.functions import udf

    cos_sim = _make_cos_sim_fn(broadcast_vec)
    cos_udf = udf(cos_sim, DoubleType())
    scored = index_df.withColumn("similarity_score", cos_udf(F.col("embedding")))
    top = scored.orderBy(F.col("similarity_score").desc()).limit(limit)

    gold_df = load_gold_dataframe()
    display_cols = [c for c in OUTPUT_COLUMNS if c in gold_df.columns]
    joined = top.join(gold_df, "id", "inner").select(
        *[F.col(c) for c in display_cols],
        F.col("similarity_score"),
    )
    return joined.toPandas()


