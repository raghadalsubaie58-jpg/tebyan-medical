"""
Context builder — assembles retrieved SearchResults into a prompt-ready string.
Manages token budget and adds source attribution.
"""
from __future__ import annotations

from ..search.semantic_search import SearchResult

_SEPARATOR = "\n\n---\n\n"
_CHARS_PER_TOKEN = 4  # rough estimate for Arabic+English mixed text


def build_context(
    results: list[SearchResult],
    max_tokens: int = 2000,
    include_source: bool = True,
) -> str:
    """
    Assemble top results into a context string.
    Stays within max_tokens budget (estimated by char count / 4).
    """
    if not results:
        return ""

    budget = max_tokens * _CHARS_PER_TOKEN
    parts: list[str] = []
    used = 0

    for r in results:
        chunk = r.content.strip()
        if not chunk:
            continue
        if include_source and r.source:
            chunk = f"[{r.source}]\n{chunk}"
        chunk_len = len(chunk)
        if used + chunk_len > budget:
            break
        parts.append(chunk)
        used += chunk_len + len(_SEPARATOR)

    return _SEPARATOR.join(parts)


def confidence_label(results: list[SearchResult]) -> str:
    """
    Return Arabic confidence label based on top-5 scores.
    عالية / متوسطة / منخفضة / لا يوجد
    """
    if not results:
        return "لا يوجد"
    top = sorted([r.score for r in results], reverse=True)[:5]
    avg = sum(top) / len(top)
    if avg > 0.70:
        return "عالية"
    if avg > 0.45:
        return "متوسطة"
    return "منخفضة"


def build_analysis_context(
    results: list[SearchResult],
    panel_context: str = "",
    max_tokens: int = 2500,
) -> str:
    """
    Build context for the analysis endpoint.
    Prepends panel reference ranges before retrieved docs.
    """
    parts: list[str] = []
    if panel_context:
        parts.append(f"[مراجع اللوحة الطبية]\n{panel_context}")
    rag = build_context(results, max_tokens=max_tokens - len(panel_context) // _CHARS_PER_TOKEN)
    if rag:
        parts.append(rag)
    return _SEPARATOR.join(parts) if parts else ""
