"""
Ranking — BM25 reranking and Cohere reranking.
Operates on SearchResult lists from SemanticSearchService.
"""
from __future__ import annotations
import logging
import re

from rank_bm25 import BM25Okapi

log = logging.getLogger("tebyan.ranking")

from ..search.semantic_search import SearchResult


def bm25_rerank(
    results: list[SearchResult],
    query: str,
    top_n: int = 5,
) -> list[SearchResult]:
    """Rerank using BM25 combined with vector scores (0.3 weight)."""
    if len(results) <= 1:
        return results[:top_n]

    tokenize = lambda t: re.findall(r"\w+", t.lower())
    corpus = [tokenize(r.content) for r in results]
    bm25 = BM25Okapi(corpus)
    bm_scores = bm25.get_scores(tokenize(query))

    mx = max(bm_scores) if max(bm_scores) > 0 else 1.0
    for r, bs in zip(results, bm_scores):
        r.score = r.score + (bs / mx) * 0.3   # fuse: vector 1.0 + BM25 0.3

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]


def cohere_rerank(
    co_client,
    results: list[SearchResult],
    query: str,
    top_n: int = 5,
) -> list[SearchResult]:
    """Rerank using Cohere rerank-v3.5. Falls back to BM25 on error."""
    if not co_client or len(results) <= 1:
        return bm25_rerank(results, query, top_n)
    try:
        docs_text = [r.content for r in results]
        resp = co_client.rerank(
            model="rerank-v3.5",
            query=query,
            documents=docs_text,
            top_n=top_n,
        )
        reranked: list[SearchResult] = []
        for item in resp.results:
            r = results[item.index]
            r.score = float(item.relevance_score)
            reranked.append(r)
        return reranked
    except Exception as e:
        log.warning("Cohere rerank failed (%s) — BM25 fallback", e)
        return bm25_rerank(results, query, top_n)


def rank(
    results: list[SearchResult],
    query: str,
    co_client=None,
    top_n: int = 5,
) -> list[SearchResult]:
    """Main entry: use Cohere if client available, else BM25."""
    if co_client:
        return cohere_rerank(co_client, results, query, top_n)
    return bm25_rerank(results, query, top_n)
