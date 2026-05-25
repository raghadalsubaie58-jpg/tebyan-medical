"""
In-memory TTL cache for expensive operations (RAG retrieval, embeddings).
LRU + TTL strategy. Thread-safe.
Replace with Redis when deploying multi-process.

Usage:
    cache = TTLCache()
    result = cache.get("rag:some_query")
    if result is None:
        result = expensive_call(...)
        cache.set("rag:some_query", result, ttl=300)
"""
from __future__ import annotations

import re
import time
import threading
import hashlib
import json
from collections import OrderedDict
from typing import Any


# ── Arabic normalization for consistent cache keys ─────────────────────────

_ARABIC_NORM = str.maketrans(
    "أإآاٱ" "ىي" "ة" "ؤئء",
    "aaaaa" "يي" "ه" "ووء",
)
_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Normalize Arabic text for cache key stability."""
    text = text.strip().lower()
    text = text.translate(_ARABIC_NORM)
    text = _WHITESPACE.sub(" ", text)
    return text


# ── Cache implementation ───────────────────────────────────────────────────

class TTLCache:
    """
    LRU cache with per-entry TTL and observable metrics.
    max_size: maximum number of entries.
    default_ttl: seconds before an entry expires.
    """

    def __init__(self, max_size: int = 512, default_ttl: int = 300) -> None:
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock      = threading.Lock()
        self._max       = max_size
        self._ttl       = default_ttl
        self._hits      = 0
        self._misses    = 0
        self._evictions = 0

    def _is_expired(self, expires_at: float) -> bool:
        return time.monotonic() > expires_at

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None
            value, expires_at = self._store[key]
            if self._is_expired(expires_at):
                del self._store[key]
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            expires_at = time.monotonic() + (ttl if ttl is not None else self._ttl)
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expires_at)
            if len(self._store) > self._max:
                self._store.popitem(last=False)
                self._evictions += 1

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            now   = time.monotonic()
            alive = sum(1 for _, (_, exp) in self._store.items() if exp > now)
            total = self._hits + self._misses
            return {
                "size":      len(self._store),
                "alive":     alive,
                "max":       self._max,
                "hits":      self._hits,
                "misses":    self._misses,
                "evictions": self._evictions,
                "hit_rate":  round(self._hits / total, 3) if total else 0.0,
            }


# ── Specialized caches ─────────────────────────────────────────────────────

# RAG context results (expensive: embedding + pgvector + Cohere)
rag_cache = TTLCache(max_size=256, default_ttl=300)   # 5-minute TTL

# Chat medical-query intent check
intent_cache = TTLCache(max_size=1024, default_ttl=600)  # 10-minute TTL

# Global KB search results (pgvector hit — ~5 s each)
search_cache = TTLCache(max_size=512, default_ttl=120)  # 2-minute TTL


def rag_cache_key(query: str, panel: str = "", topic_type: str = "") -> str:
    """
    Deterministic, normalized cache key for a RAG retrieval call.
    Normalization: Arabic chars unified, whitespace collapsed, lowercased.
    """
    norm_q = _normalize(query[:300])
    raw    = json.dumps({"q": norm_q, "panel": panel.lower(), "tt": topic_type.lower()},
                        sort_keys=True, ensure_ascii=False)
    return "rag:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def intent_cache_key(query: str) -> str:
    norm_q = _normalize(query[:200])
    return "intent:" + hashlib.sha256(norm_q.encode()).hexdigest()[:16]
