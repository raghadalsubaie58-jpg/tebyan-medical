"""
Centralized embedding service — singleton HuggingFaceEmbeddings with LRU query cache.
All parts of the app embed through here so the model is loaded only once.
"""
from __future__ import annotations
import logging
from functools import lru_cache

log = logging.getLogger("tebyan.embeddings")

EMBED_MODEL = "intfloat/multilingual-e5-large"

# LRU query cache — avoids re-embedding repeated queries
_cache: dict[str, list[float]] = {}
_MAX_CACHE = 500


@lru_cache(maxsize=1)
def get_embeddings():
    """Return the singleton HuggingFaceEmbeddings instance."""
    from langchain_huggingface import HuggingFaceEmbeddings
    emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    log.info("Embedding model loaded: %s", EMBED_MODEL)
    return emb


def embed_query(text: str) -> list[float]:
    """Embed a single query string with LRU caching."""
    if text not in _cache:
        if len(_cache) >= _MAX_CACHE:
            _cache.pop(next(iter(_cache)))
        _cache[text] = get_embeddings().embed_query(text)
    return _cache[text]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of documents (no caching — for ingest only)."""
    return get_embeddings().embed_documents(texts)


def cache_size() -> int:
    return len(_cache)


def clear_cache() -> None:
    _cache.clear()
