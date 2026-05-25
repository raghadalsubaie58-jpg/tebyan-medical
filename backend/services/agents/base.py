"""
Agent base classes and shared context for the Tebyan multi-agent system.

Each agent:
  - Receives AgentContext (shared mutable state)
  - Executes its task, writes results back into context
  - Emits structured log entries
  - Supports retry with exponential backoff
  - Can declare hard failures vs soft degradations
"""
from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("tebyan.agents")


# ── Shared agent context (mutable, passed between agents) ─────────────────

@dataclass
class AgentMemory:
    """Per-session short-term memory. Agents can store and retrieve facts."""
    _store: dict[str, Any] = field(default_factory=dict, repr=False)

    def remember(self, key: str, value: Any) -> None:
        self._store[key] = value

    def recall(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def as_dict(self) -> dict:
        return dict(self._store)


@dataclass
class AgentLogEntry:
    agent: str
    status: str          # "ok" | "error" | "skipped" | "degraded"
    duration_ms: float
    message: str = ""
    attempts: int = 1


@dataclass
class AgentContext:
    """
    Shared state passed through the full agent pipeline.
    Agents read their inputs from this object and write their outputs back.
    """
    # ── Inputs ──────────────────────────────────────────────────────────────
    file_bytes:     bytes = b""
    file_type:      str   = ""        # "pdf" | "image"
    analysis_type:  str   = "شامل"
    session_id:     str   = ""

    # ── OCR Agent output ────────────────────────────────────────────────────
    raw_text:       str   = ""

    # ── Extraction Agent output ──────────────────────────────────────────────
    findings_raw:   list  = field(default_factory=list)
    findings:       list[dict] = field(default_factory=list)

    # ── Classification Agent output ──────────────────────────────────────────
    panel_code:     str   = ""
    panel_confidence: str = "low"
    all_panels:     list[str] = field(default_factory=list)

    # ── Medical Reasoning Agent output ───────────────────────────────────────
    rag_context:    str   = ""
    rag_confidence: str   = "لا يوجد"
    panel_context:  str   = ""
    report_raw:     dict  = field(default_factory=dict)

    # ── Recommendation Agent output ──────────────────────────────────────────
    recommendations: list[dict] = field(default_factory=list)

    # ── Safety Agent output ──────────────────────────────────────────────────
    report: dict = field(default_factory=dict)

    # ── Observability ────────────────────────────────────────────────────────
    logs:   list[AgentLogEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    memory: AgentMemory = field(default_factory=AgentMemory)

    def log_step(self, agent: str, status: str, duration_ms: float,
                 message: str = "", attempts: int = 1) -> None:
        entry = AgentLogEntry(agent=agent, status=status, duration_ms=round(duration_ms, 1),
                              message=message, attempts=attempts)
        self.logs.append(entry)
        level = logging.ERROR if status == "error" else logging.INFO
        log.log(level, "[%s] %s | %.0fms | %s", agent, status.upper(), duration_ms, message)

    def serialize_logs(self) -> list[dict]:
        return [
            {"agent": e.agent, "status": e.status, "ms": e.duration_ms,
             "msg": e.message, "attempts": e.attempts}
            for e in self.logs
        ]


# ── Agent base class ───────────────────────────────────────────────────────

class AgentBase(ABC):
    """
    Abstract base for all pipeline agents.
    Subclasses implement _execute(ctx) and override name/max_retries.
    """
    name: str = "agent"
    max_retries: int = 2
    retry_delay: float = 0.3   # seconds, doubles each retry

    def run(self, ctx: AgentContext) -> AgentContext:
        """
        Execute the agent with retry logic.
        Returns the (mutated) context.
        """
        t0 = time.perf_counter()
        last_exc: Exception | None = None
        delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            try:
                self._execute(ctx)
                ms = (time.perf_counter() - t0) * 1000
                ctx.log_step(self.name, "ok", ms, attempts=attempt)
                return ctx
            except _SoftDegradation as exc:
                # Non-fatal: log and continue (partial result is acceptable)
                ms = (time.perf_counter() - t0) * 1000
                ctx.log_step(self.name, "degraded", ms, str(exc), attempts=attempt)
                log.warning("[%s] soft degradation: %s", self.name, exc)
                return ctx
            except Exception as exc:
                last_exc = exc
                log.warning("[%s] attempt %d/%d failed: %s", self.name, attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay = min(delay * 2, 5.0)

        ms = (time.perf_counter() - t0) * 1000
        ctx.errors.append(f"{self.name}: {last_exc}")
        ctx.log_step(self.name, "error", ms, str(last_exc), attempts=self.max_retries)
        self._on_failure(ctx, last_exc)
        return ctx

    @abstractmethod
    def _execute(self, ctx: AgentContext) -> None:
        """Agent logic. Mutates ctx. Raise exception on failure."""

    def _on_failure(self, ctx: AgentContext, exc: Exception) -> None:
        """Override to provide graceful fallback on final failure."""


class _SoftDegradation(Exception):
    """Raised by an agent when it completes partially — not a fatal error."""
