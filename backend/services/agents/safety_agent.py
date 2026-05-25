"""Safety Agent — PDPL-compliant output filtering + disclaimer injection."""
from __future__ import annotations
from .base import AgentBase, AgentContext


class SafetyAgent(AgentBase):
    name = "safety_agent"
    max_retries = 1

    def _execute(self, ctx: AgentContext) -> None:
        from services.safety import filter_analysis_report
        ctx.report = filter_analysis_report(ctx.report)
        ctx.memory.remember("safety_applied", True)

    def _on_failure(self, ctx: AgentContext, exc: Exception) -> None:
        # Safety must not crash the pipeline — log and continue
        from services.safety import DISCLAIMER_AR
        if ctx.report.get("general"):
            ctx.report["general"] = ctx.report["general"] + DISCLAIMER_AR
