"""
Grounding — citation extraction and source attribution.
Converts SearchResults into citable source references.
"""
from __future__ import annotations
from dataclasses import dataclass

from ..search.semantic_search import SearchResult

_SOURCE_URLS: dict[str, str] = {
    "MedlinePlus": "https://medlineplus.gov",
    "TibyanLabs":  "",
}


@dataclass
class Citation:
    source: str
    content_preview: str   # first 120 chars
    score: float
    url: str | None = None
    chunk_type: str | None = None
    specialty: str | None = None


def extract_citations(results: list[SearchResult]) -> list[Citation]:
    """Convert ranked SearchResults to deduplicated citations."""
    citations: list[Citation] = []
    seen_sources: set[str] = set()

    for r in results:
        meta = r.metadata
        source = r.source or meta.get("source", "Unknown")
        url = meta.get("url") or _SOURCE_URLS.get(source)

        citations.append(Citation(
            source=source,
            content_preview=r.content[:120].strip(),
            score=r.score,
            url=url or None,
            chunk_type=meta.get("chunk_type"),
            specialty=meta.get("specialty"),
        ))
        seen_sources.add(source)

    return citations


def format_citations_arabic(citations: list[Citation]) -> str:
    """Human-readable Arabic citation list for injection into prompts."""
    if not citations:
        return ""
    lines: list[str] = ["**المصادر:**"]
    seen: set[str] = set()
    for c in citations:
        key = c.source
        if key in seen:
            continue
        seen.add(key)
        if c.url:
            lines.append(f"- [{c.source}]({c.url})")
        else:
            lines.append(f"- {c.source}")
    return "\n".join(lines)


def has_high_confidence_sources(citations: list[Citation]) -> bool:
    """True if at least one citation has score >= 0.7."""
    return any(c.score >= 0.7 for c in citations)
