"""
Retriever — full RAG retrieval pipeline.

Pipeline:
  1. Parse query → detect panel/topic/language
  2. Expand to multiple queries (via query_parser + optional Groq)
  3. Vector search per query via SemanticSearchService
  4. Deduplicate + merge scores
  5. Filter by minimum score threshold
  6. Rank (Cohere or BM25)
  7. Return (results, confidence_label)
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Callable

log = logging.getLogger("tebyan.retriever")

from ..search.semantic_search import SemanticSearchService, SearchResult
from ..search.query_parser import parse_query
from .ranking import rank
from .context_builder import confidence_label


@dataclass
class RetrievalConfig:
    k: int = 10                      # candidates per query from vector search
    top_n: int = 5                   # final results after reranking
    min_score: float = 0.4           # minimum relevance threshold
    use_multi_query: bool = True     # expand to multiple queries
    topic_type: str | None = None    # pgvector metadata filter


class Retriever:
    """
    Orchestrates the full retrieval pipeline.
    Injected with SemanticSearchService and optional Cohere/Groq clients.
    """

    def __init__(
        self,
        search_service: SemanticSearchService,
        co_client=None,
        query_expander: Callable[[str], list[str]] | None = None,
    ) -> None:
        self._search = search_service
        self._co = co_client
        self._expander = query_expander   # e.g. lambda q: generate_search_queries(groq, q)

    # ── Query expansion ────────────────────────────────────────────────────

    def _expand_queries(self, query: str) -> list[str]:
        parsed = parse_query(query)
        queries = list(parsed.search_expansions)   # already includes original

        if self._expander and len(queries) < 3:
            try:
                groq_queries = self._expander(query)
                for q in groq_queries:
                    if q not in queries:
                        queries.append(q)
            except Exception as e:
                log.warning("query expansion failed: %s", e)

        return queries[:4]  # cap to avoid too many API calls

    # ── Main retrieval ─────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        config: RetrievalConfig | None = None,
    ) -> tuple[list[SearchResult], str]:
        """
        Returns (ranked_results, confidence_label_ar).
        confidence_label_ar: 'عالية' | 'متوسطة' | 'منخفضة' | 'لا يوجد'
        """
        cfg = config or RetrievalConfig()

        queries = self._expand_queries(query) if cfg.use_multi_query else [query]
        seen: dict[str, SearchResult] = {}

        for q in queries:
            for r in self._search.search(q, k=cfg.k, topic_type=cfg.topic_type):
                key = r.content[:80]
                if key not in seen or seen[key].score < r.score:
                    seen[key] = r

        filtered = [r for r in seen.values() if r.score >= cfg.min_score]
        if not filtered:
            log.warning(
                "RAG no results | query=%r threshold=%.2f candidates=%d",
                query[:60], cfg.min_score, len(seen),
            )
            return [], "لا يوجد"

        ranked = rank(filtered, query, co_client=self._co, top_n=cfg.top_n)
        conf   = confidence_label(ranked)

        top_scores = [round(r.score, 3) for r in ranked[:3]]
        sources    = list({r.source for r in ranked})
        log.info(
            "RAG retrieve | query=%r queries=%d candidates=%d top=%d "
            "conf=%s scores=%s sources=%s",
            query[:60], len(queries), len(filtered), len(ranked),
            conf, top_scores, sources,
        )
        return ranked, conf

    # ── Lightweight retrieval (no multi-query, no Cohere) ──────────────────

    def retrieve_fast(
        self,
        query: str,
        k: int = 5,
        top_n: int = 3,
    ) -> list[SearchResult]:
        """
        Optimized for chat endpoint — no query expansion, no Cohere rerank.
        Reduces latency by ~4 seconds compared to full pipeline.
        """
        results  = self._search.search(query, k=k)
        filtered = [r for r in results if r.score >= 0.35]
        if not filtered:
            log.debug("RAG fast retrieve | query=%r → 0 results above 0.35", query[:60])
            return []
        ranked = rank(filtered, query, co_client=None, top_n=top_n)
        log.debug(
            "RAG fast retrieve | query=%r candidates=%d top=%d scores=%s",
            query[:60], len(filtered), len(ranked),
            [round(r.score, 3) for r in ranked],
        )
        return ranked
