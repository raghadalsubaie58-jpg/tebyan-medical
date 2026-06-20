"""Extraction Agent — parses structured findings from raw OCR text."""
from __future__ import annotations
import re
import json
from .base import AgentBase, AgentContext, _SoftDegradation

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")

# Sample-type prefixes common in lab reports (BLOOD, SERUM, etc. at line start)
_SAMPLE_TYPE_RE = re.compile(r"^(?:URINE|BLOOD|SERUM|PLASMA|CSF|STOOL|WHOLE BLOOD)\s+", re.MULTILINE | re.IGNORECASE)


def _normalize_text(text: str) -> str:
    """Clean and normalize OCR/PDF text before extraction."""
    # Arabic-Indic digits and decimal separator
    text = text.translate(_ARABIC_DIGITS)
    text = re.sub(r"(\d),(\d)", r"\1.\2", text)

    # Normalize special dash/bullet chars to regular hyphen (used as range separators in some PDFs)
    text = text.replace("•", "-").replace("·", "-")  # • and ·
    text = text.replace("–", "-").replace("—", "-")  # – and —

    # Strip SNOMED/LOINC/ICD codes embedded in test names: [SNOMED:12345-6]
    text = re.sub(r"\[\w+:[^\]]{1,30}\]", "", text)

    # Remove column-separator " - " before a reference range.
    # Handles: "12.2 g/dl - 12-16" and "5.0 - 5-8" (letter OR digit before the separator)
    text = re.sub(r"\s+-\s+([\d\.]+\s*-\s*[\d\.]+)", r" \1", text)

    # Remove sample-type column prefixes (URINE, BLOOD, SERUM) at line start
    text = _SAMPLE_TYPE_RE.sub("", text)

    return text


class ExtractionAgent(AgentBase):
    name = "extraction_agent"
    max_retries = 2

    def __init__(self, groq_client, render_prompt_fn):
        self._groq   = groq_client
        self._render = render_prompt_fn

    def _execute(self, ctx: AgentContext) -> None:
        from services.agent._validators import is_valid_test, is_impossible_value, get_status

        normalized_text = _normalize_text(ctx.raw_text)

        # Step 1: regex — two patterns to cover different report formats
        # Name group allows letters, spaces, #, %, (, ) to capture "SODIUM ( Na )", "SGPT ( ALT )" etc.
        _name = r"([a-zA-Z][a-zA-Z\s#%()/]{2,})"
        # Pattern A: name  value  range  [unit]     e.g. "Hemoglobin  12.2  12-16  g/dL"
        pat_a = _name + r"\s+(\d+\.?\d*)\s+([\d\.]+\s*-\s*[\d\.]+)\s*([a-zA-Z0-9^³/μ%]+)?"
        # Pattern B: name  value  unit  range       e.g. "Hemoglobin  12.2  g/dl  12-16"
        pat_b = _name + r"\s+(\d+\.?\d*)\s+([a-zA-Z0-9^³/μ%/]+)\s+([\d\.]+\s*-\s*[\d\.]+)"

        matches_a = [f for f in re.findall(pat_a, normalized_text) if is_valid_test(f[0])]
        # For pat_b, reorder to (name, value, range, unit)
        matches_b = [(f[0], f[1], f[3], f[2]) for f in re.findall(pat_b, normalized_text) if is_valid_test(f[0])]

        # Merge, deduplicate by first token of name
        seen: set[str] = set()
        raw = []
        for f in matches_a + matches_b:
            key = str(f[0]).strip().lower()
            if key not in seen:
                seen.add(key)
                raw.append(f)

        # Step 2: LLM fallback for Arabic/unstructured reports
        if len(raw) < 2:
            raw = self._llm_extract(normalized_text)

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
        if not text or not text.strip():
            return []
        prompt = self._render("extraction_template", LAB_TEXT=text[:6000]) or (
            "أنت خبير في تحليل التقارير الطبية المختبرية.\n"
            "أرجع JSON array فقط. إذا لم تجد فحوصات مختبرية أرجع []\n"
            '[{"name":"...","value":"...","range":"...","unit":"..."}]\n'
            f"النص:\n{text[:6000]}"
        )
        try:
            resp = self._groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "أنت محلل تقارير طبية. أرجع JSON array فقط بدون أي نص إضافي. "
                            "لا تضف شرحاً أو مقدمة. الإخراج يجب أن يبدأ بـ [ وينتهي بـ ]."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0, max_tokens=1500,
            )
            raw = resp.choices[0].message.content.strip()
        except Exception as e:
            import logging
            logging.getLogger("tebyan.agents").error("[extraction] Groq call failed: %s", e)
            return []

        raw = raw.replace("```json", "").replace("```", "").strip()
        if "[" not in raw:
            return []

        raw = raw[raw.index("["):raw.rindex("]") + 1]
        # Fix common LLM JSON issues: trailing commas before ] or }
        raw = re.sub(r",\s*([\]}])", r"\1", raw)

        try:
            extracted = json.loads(raw)
        except json.JSONDecodeError:
            import logging
            logging.getLogger("tebyan.agents").warning("[extraction] JSON parse failed, raw=%r", raw[:300])
            return []

        if not isinstance(extracted, list):
            return []

        return [
            (f.get("name", ""), f.get("value", ""), f.get("range", ""), f.get("unit", ""))
            for f in extracted if isinstance(f, dict) and f.get("name") and f.get("value")
        ]

    def _on_failure(self, ctx: AgentContext, exc: Exception) -> None:
        ctx.findings = []
