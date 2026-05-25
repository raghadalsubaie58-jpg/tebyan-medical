"""Extraction Agent — parses structured findings from raw OCR text."""
from __future__ import annotations
import re
import json
from .base import AgentBase, AgentContext, _SoftDegradation


class ExtractionAgent(AgentBase):
    name = "extraction_agent"
    max_retries = 2

    def __init__(self, groq_client, render_prompt_fn):
        self._groq   = groq_client
        self._render = render_prompt_fn

    def _execute(self, ctx: AgentContext) -> None:
        from services.agent._validators import is_valid_test, is_impossible_value, get_status

        # Step 1: regex (fast, works for structured English reports)
        pattern = r"([a-zA-Z][a-zA-Z\s#%]{2,})\s+(\d+\.?\d*)\s+([\d\.]+\s*-\s*[\d\.]+)\s*([a-zA-Z0-9^/]+)?"
        raw = [f for f in re.findall(pattern, ctx.raw_text) if is_valid_test(f[0])]

        # Step 2: LLM fallback for Arabic/unstructured reports
        if len(raw) < 2:
            raw = self._llm_extract(ctx.raw_text)

        ctx.findings_raw = raw

        # Step 3: validate + normalize
        findings = []
        for f in raw:
            name  = str(f[0]).strip()
            value = str(f[1])
            if not is_valid_test(name):
                continue
            if is_impossible_value(name, value):
                continue
            findings.append({
                "name":   name,
                "value":  value,
                "range":  str(f[2]),
                "unit":   str(f[3]) if len(f) > 3 else "",
                "status": get_status(value, f[2], name=name),
            })

        ctx.findings = findings
        ctx.memory.remember("finding_count", len(findings))

        if not findings:
            raise _SoftDegradation("No valid findings extracted")

    def _llm_extract(self, text: str) -> list:
        prompt = self._render("extraction_template", LAB_TEXT=text[:6000]) or (
            "أنت خبير في تحليل التقارير الطبية المختبرية.\n"
            "أرجع JSON array فقط. إذا لم تجد فحوصات مختبرية أرجع []\n"
            '[{"name":"...","value":"...","range":"...","unit":"..."}]\n'
            f"النص:\n{text[:6000]}"
        )
        resp = self._groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=1500,
        )
        raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        if "[" not in raw:
            return []
        raw = raw[raw.index("["):raw.rindex("]") + 1]
        extracted = json.loads(raw)
        return [
            (f.get("name", ""), f.get("value", ""), f.get("range", ""), f.get("unit", ""))
            for f in extracted if isinstance(f, dict) and f.get("name") and f.get("value")
        ]

    def _on_failure(self, ctx: AgentContext, exc: Exception) -> None:
        ctx.findings = []
