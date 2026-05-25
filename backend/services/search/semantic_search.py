"""
SemanticSearchService — replaces PGVectorStore in main.py.
Wraps Supabase REST pgvector with typed SearchResult output.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field

import requests as http_requests

log = logging.getLogger("tebyan.semantic_search")

from .embedding_service import embed_query
from .query_parser import parse_query


@dataclass
class SearchResult:
    content: str
    score: float
    source: str
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"SearchResult(score={self.score:.3f}, "
            f"source={self.source!r}, "
            f"content={self.content[:60]!r})"
        )


class SemanticSearchService:
    """
    Unified interface over Supabase pgvector REST API.
    Handles embedding, vector search, metadata filtering, and score boosting.
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        match_threshold: float = 0.3,
    ) -> None:
        self._url = supabase_url.rstrip("/")
        self._key = supabase_key
        self._threshold = match_threshold
        self._headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }

    # ── Low-level vector search ────────────────────────────────────────────

    def _vector_search(
        self,
        query: str,
        k: int = 10,
        filter_meta: dict | None = None,
    ) -> list[SearchResult]:
        vec = embed_query(query)
        payload = {
            "query_embedding": vec,
            "match_threshold": self._threshold,
            "match_count": k,
            "filter": filter_meta or {},
        }
        try:
            r = http_requests.post(
                f"{self._url}/rest/v1/rpc/match_documents",
                headers=self._headers,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            return [
                SearchResult(
                    content=row["content"],
                    score=float(row["similarity"]),
                    source=(row.get("metadata") or {}).get("source", ""),
                    metadata=row.get("metadata") or {},
                )
                for row in r.json()
            ]
        except Exception as e:
            log.error("vector search failed: %s", e)
            return []

    # ── Public search ──────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        k: int = 10,
        topic_type: str | None = None,
    ) -> list[SearchResult]:
        """
        Search with optional topic_type metadata filter.
        Boosts panel-specific results if panel is detected from query.
        """
        parsed = parse_query(query)
        filter_meta = {"topic_type": topic_type} if topic_type else {}

        # Primary search
        seen: dict[str, SearchResult] = {}
        for r in self._vector_search(query, k=k, filter_meta=filter_meta):
            key = r.content[:80]
            if key not in seen or seen[key].score < r.score:
                seen[key] = r

        # Boosted search for detected panel
        if parsed.panel_type and not topic_type:
            for r in self._vector_search(
                query, k=min(k, 5), filter_meta={"panel_type": parsed.panel_type}
            ):
                key = r.content[:80]
                r.score = min(r.score + 0.1, 1.0)
                if key not in seen or seen[key].score < r.score:
                    seen[key] = r

        filtered = [r for r in seen.values() if r.score >= self._threshold]
        return sorted(filtered, key=lambda r: r.score, reverse=True)

    # ── Utility ────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Return total document count in the pgvector store."""
        try:
            r = http_requests.get(
                f"{self._url}/rest/v1/documents",
                headers={**self._headers, "Prefer": "count=exact", "Range": "0-0"},
                timeout=10,
            )
            return int(r.headers.get("Content-Range", "0/0").split("/")[-1])
        except Exception:
            return 0
