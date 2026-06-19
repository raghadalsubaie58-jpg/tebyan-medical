"""
Medical Reasoning Agent — retrieves RAG context + generates structured report.
Implements Chain-of-Thought via panel-specific prompts.
"""
from __future__ import annotations
import json
from .base import AgentBase, AgentContext


_TYPE_HINTS = {
    "دم شامل":        "CBC complete blood count hemoglobin WBC RBC platelets",
    "سكر وكوليسترول": "glucose HbA1c cholesterol LDL HDL triglycerides",
    "كلى وكبد":       "creatinine BUN urea ALT AST bilirubin GFR albumin",
    "هرمونات":        "TSH T3 T4 testosterone estradiol FSH LH prolactin",
    "شامل":           "clinical pathology lab results blood tests",
}

_PANEL_PROMPTS = {
    "cbc":      "templates/cbc_analysis_prompt",
    "thyroid":  "templates/thyroid_analysis_prompt",
    "liver":    "templates/liver_analysis_prompt",
    "kidney":   "templates/kidney_analysis_prompt",
    "diabetes": "templates/diabetes_analysis_prompt",
    "lipid":    "templates/lipid_analysis_prompt",
}

_JSON_FORMAT = (
    '{"تقييم_عام":"جملتان عن الحالة",'
    '"قيم_غير_طبيعية":[{"اسم_الفحص":"","النتيجة":"","المعدل_الطبيعي":"","الحالة":"","الشرح":"","المرجع":""}],'
    '"توصيات":[{"category":"","tips":["",""]}]}'
)


class MedicalReasoningAgent(AgentBase):
    name = "reasoning_agent"
    max_retries = 2

    def __init__(self, groq_client, retriever, kb, render_prompt_fn, retrieval_config_cls):
        self._groq      = groq_client
        self._retriever = retriever
        self._kb        = kb
        self._render    = render_prompt_fn
        self._cfg_cls   = retrieval_config_cls

    def _execute(self, ctx: AgentContext) -> None:
        self._retrieve(ctx)
        self._analyze(ctx)

    def _retrieve(self, ctx: AgentContext) -> None:
        from services.rag.context_builder import build_analysis_context
        from services.cache import rag_cache, rag_cache_key

        hint = _TYPE_HINTS.get(ctx.analysis_type, _TYPE_HINTS["شامل"])
        q    = f"{hint}: " + ", ".join(f["name"] for f in ctx.findings)

        cache_key = rag_cache_key(q, ctx.panel_code)
        cached    = rag_cache.get(cache_key)
        if cached:
            ctx.rag_context, ctx.rag_confidence, ctx.panel_context = cached
            return

        rag_results, conf = self._retriever.retrieve(
            q,
            self._cfg_cls(k=8, use_multi_query=False,
                          topic_type="lab_test" if ctx.panel_code else None),
        )
        panel_ctx = self._kb.build_panel_context(ctx.panel_code) if ctx.panel_code else ""
        context   = build_analysis_context(rag_results, panel_context=panel_ctx)

        ctx.rag_context, ctx.rag_confidence, ctx.panel_context = context, conf, panel_ctx
        if context:
            rag_cache.set(cache_key, (context, conf, panel_ctx), ttl=300)

    def _analyze(self, ctx: AgentContext) -> None:
        prompt_name = _PANEL_PROMPTS.get(ctx.panel_code, "system_analysis")
        prompt = self._render(
            prompt_name,
            FINDINGS=json.dumps(ctx.findings, ensure_ascii=False),
            RAG_CONTEXT=ctx.rag_context or "لا توجد مراجع",
            PATIENT_CONTEXT="",
            SYSTEM_FORMAT=_JSON_FORMAT,
        ) or (
            f"أنت طبيب مختبر خبير. أرجع JSON فقط — ابدأ بـ {{.\n"
            f"النتائج: {json.dumps(ctx.findings, ensure_ascii=False)}\n"
            f"المراجع: {ctx.rag_context or 'لا توجد مراجع'}\n\n{_JSON_FORMAT}"
        )

        resp = self._groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=1200,
        )
        raw = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        if "{" in raw:
            raw = raw[raw.index("{"):raw.rindex("}") + 1]
        rd = json.loads(raw)

        ctx.report_raw = rd
        ctx.report = {
            "general":          rd.get("تقييم_عام", ""),
            "abnormal_details": rd.get("قيم_غير_طبيعية", []),
            "tips_categorized": rd.get("توصيات", []),
            "tips":             rd.get("نصائح", []),
            "rag_confidence":   ctx.rag_confidence,
        }

    def _on_failure(self, ctx: AgentContext, exc: Exception) -> None:
        abnormal = [f for f in ctx.findings if f.get("status") != "normal"]
        ctx.report = {
            "general": "القيم التي تحتاج انتباهاً: " + "، ".join(f["name"] for f in abnormal[:3]) if abnormal else "جميع القيم ضمن المعدل الطبيعي ✓",
            "abnormal_details": [
                {"اسم_الفحص": f["name"], "النتيجة": f["value"], "المعدل_الطبيعي": f["range"],
                 "الحالة": "مرتفع" if f["status"] == "high" else "منخفض",
                 "الشرح": f"قيمة {'مرتفعة' if f['status'] == 'high' else 'منخفضة'} عن المعدل.",
                 "المرجع": "لا يوجد"}
                for f in abnormal
            ],
            "tips": [], "rag_confidence": ctx.rag_confidence,
        }
