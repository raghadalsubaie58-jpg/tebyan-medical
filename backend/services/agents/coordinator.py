"""
AgentCoordinator — orchestrates the full multi-agent medical analysis pipeline.

Agent execution order:
  1. OCRAgent          — raw text extraction
  2. ExtractionAgent   — structured findings
  3. ClassificationAgent — panel detection
  4. MedicalReasoningAgent — RAG + LLM analysis
  5. SafetyAgent        — PDPL compliance

Each agent can soft-degrade (partial result) or hard-fail (triggers fallback).
The coordinator collects structured logs for observability.
"""
from __future__ import annotations
import time
import logging
from dataclasses import dataclass

from .base import AgentContext
from .ocr_agent import OCRAgent
from .extraction_agent import ExtractionAgent
from .classification_agent import ClassificationAgent
from .reasoning_agent import MedicalReasoningAgent
from .safety_agent import SafetyAgent

log = logging.getLogger("tebyan.coordinator")


@dataclass
class CoordinatorResult:
    findings:      list[dict]
    summary:       str
    report:        dict
    panel_code:    str
    logs:          list[dict]
    ok:            bool  = True
    error:         str   = ""
    total_ms:      float = 0.0


class AgentCoordinator:
    """
    Builds and runs the agent pipeline from injected dependencies.
    Agents are constructed once and reused across requests.
    """

    def __init__(self, groq_client, retriever, kb, render_prompt_fn,
                 retrieval_config_cls, vision_key: str = ""):
        self._agents = [
            OCRAgent(vision_key),
            ExtractionAgent(groq_client, render_prompt_fn),
            ClassificationAgent(),
            MedicalReasoningAgent(groq_client, retriever, kb, render_prompt_fn, retrieval_config_cls),
            SafetyAgent(),
        ]

    def run(self, file_bytes: bytes, file_type: str,
            analysis_type: str = "شامل", session_id: str = "") -> CoordinatorResult:
        t0  = time.perf_counter()
        ctx = AgentContext(
            file_bytes=file_bytes,
            file_type=file_type,
            analysis_type=analysis_type,
            session_id=session_id,
        )

        for agent in self._agents:
            ctx = agent.run(ctx)
            # Hard stop if OCR or extraction completely failed
            if agent.name in ("ocr_agent", "extraction_agent") and not ctx.findings and agent.name == "extraction_agent":
                if not ctx.findings:
                    log.error("[coordinator] extraction failed — aborting pipeline")
                    return CoordinatorResult(
                        findings=[], summary="", report={}, panel_code="",
                        logs=ctx.serialize_logs(), ok=False,
                        error="لم نتمكن من قراءة قيم التحاليل من الملف.",
                        total_ms=(time.perf_counter() - t0) * 1000,
                    )

        total_ms = (time.perf_counter() - t0) * 1000
        log.info("[coordinator] done | %.0fms | agents=%d | errors=%d",
                 total_ms, len(self._agents), len(ctx.errors))

        abnormal = [f for f in ctx.findings if f.get("status") != "normal"]
        summary  = (
            "القيم التي تحتاج انتباهاً: " + "، ".join(f["name"] for f in abnormal[:3])
            if abnormal else "جميع القيم ضمن المعدل الطبيعي ✓"
        )

        return CoordinatorResult(
            findings=ctx.findings,
            summary=summary,
            report=ctx.report,
            panel_code=ctx.panel_code,
            logs=ctx.serialize_logs(),
            ok=True,
            total_ms=total_ms,
        )
