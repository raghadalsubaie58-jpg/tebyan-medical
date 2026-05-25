"""Classification Agent — detects medical panel type from findings."""
from __future__ import annotations
from .base import AgentBase, AgentContext


class ClassificationAgent(AgentBase):
    name = "classification_agent"
    max_retries = 1

    def _execute(self, ctx: AgentContext) -> None:
        from services.classifier import classify_report
        from services.search.query_parser import detect_panel

        clf = classify_report(ctx.findings)
        panel = clf.primary_panel

        if not panel:
            q = ", ".join(f["name"] for f in ctx.findings)
            panel = detect_panel(q) or detect_panel(ctx.analysis_type) or ""

        ctx.panel_code       = panel
        ctx.panel_confidence = clf.confidence
        ctx.all_panels       = clf.all_panels

        ctx.memory.remember("panel", panel)
        ctx.memory.remember("all_panels", clf.all_panels)

    def _on_failure(self, ctx: AgentContext, exc: Exception) -> None:
        ctx.panel_code = ""
