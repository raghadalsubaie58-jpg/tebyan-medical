"""
Medical Safety Layer — PDPL-compliant output filtering.
Prevents definitive diagnoses, medication dosing, and adds mandatory disclaimers.
"""
from __future__ import annotations
import re

# ── Patterns that suggest definitive diagnosis ──────────────────────────────
_DIAGNOSIS_PATTERNS = [
    r"أنتِ?\s+مريض[ة]?\s+بـ?",
    r"لديكِ?\s+(مرض|سرطان|داء|متلازمة)",
    r"تشخيص[كِ]?\s+(هو|:)",
    r"مصاب[ة]?\s+بـ?\s+\w+",
    r"you\s+have\s+(cancer|disease|syndrome|disorder)",
    r"diagnosed\s+with",
]

# ── Patterns that suggest specific medication dosing ─────────────────────────
_MEDICATION_PATTERNS = [
    r"\d+\s*(mg|ملجم|ملغ|µg|mcg|IU)\s*(يومياً|daily|مرتين|ثلاث مرات)",
    r"(خذ|تناول|اشرب)\s+\w+\s+\d+",
    r"جرعة[كِ]?\s+(هي|:)\s+\d+",
    r"دواء\s+\w+\s+\d+\s*(mg|ملجم)",
]

# ── Emergency keywords → prepend urgent warning ──────────────────────────────
_EMERGENCY_KEYWORDS_AR = [
    "ألم صدر", "ضيق تنفس", "فقدان وعي", "نزيف حاد", "شلل",
    "تعذر التنفس", "سكتة", "نوبة قلبية", "صعوبة التنفس",
]
_EMERGENCY_KEYWORDS_EN = [
    "chest pain", "difficulty breathing", "loss of consciousness",
    "severe bleeding", "stroke", "heart attack", "paralysis",
]

# ── PDPL-compliant disclaimer (وفق PDPL السعودي) ────────────────────────────
DISCLAIMER_AR = (
    "\n\n⚕️ **تنبيه طبي:** هذه المعلومات لأغراض التوعية الصحية فقط "
    "ولا تُغني عن استشارة طبيب مختص. لا تتخذ أي قرار علاجي بناءً عليها."
)

EMERGENCY_WARNING = (
    "⚠️ **تحذير:** بعض هذه الأعراض قد تستدعي تقييماً طبياً عاجلاً. "
    "إذا كنت تعاني من أعراض حادة، توجّه فوراً لأقرب طوارئ.\n\n"
)


def _contains_pattern(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _has_emergency_keywords(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _EMERGENCY_KEYWORDS_AR + _EMERGENCY_KEYWORDS_EN)


def _soften_diagnosis(text: str) -> str:
    """Replace definitive diagnosis phrases with cautious language."""
    replacements = [
        (r"أنتِ? مريض[ة]? بـ?(\w+)", r"النتائج قد تشير إلى \1"),
        (r"لديكِ? (مرض|سرطان|داء)\s+(\w+)", r"النتائج قد تشير إلى \1 \2"),
        (r"مصاب[ة]? بـ?\s*(\w+)", r"النتائج تستدعي فحص \1"),
        (r"تشخيص[كِ]? هو\s+(\w+)", r"النتائج قد تشير إلى \1"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _remove_dosing(text: str) -> str:
    """Remove specific medication dosing instructions."""
    # Replace dosing with generic advice
    text = re.sub(
        r"(خذ|تناول)\s+\w+\s+\d+\s*(mg|ملجم|ملغ)",
        "استشر طبيبك لتحديد الجرعة المناسبة",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\d+\s*(mg|ملجم|ملغ)\s*(يومياً|daily|مرتين)",
        "(الجرعة يحددها الطبيب)",
        text,
        flags=re.IGNORECASE,
    )
    return text


def filter_analysis_report(report: dict) -> dict:
    """
    Apply safety filtering to the full analysis report dict.
    Modifies: general, abnormal_details[].شرح
    Adds: disclaimer to general
    """
    # Filter general assessment
    general = report.get("general", "")
    if _contains_pattern(general, _DIAGNOSIS_PATTERNS):
        general = _soften_diagnosis(general)
    if _contains_pattern(general, _MEDICATION_PATTERNS):
        general = _remove_dosing(general)
    report["general"] = general + DISCLAIMER_AR

    # Filter each abnormal detail explanation
    for item in report.get("abnormal_details", []):
        sharh = item.get("الشرح", "")
        if _contains_pattern(sharh, _DIAGNOSIS_PATTERNS):
            sharh = _soften_diagnosis(sharh)
        if _contains_pattern(sharh, _MEDICATION_PATTERNS):
            sharh = _remove_dosing(sharh)
        item["الشرح"] = sharh

    return report


def filter_chat_response(response_text: str, user_query: str = "") -> str:
    """
    Apply safety filtering to chat response text.
    - Softens definitive diagnoses
    - Removes medication dosing
    - Adds emergency warning if needed
    - Adds disclaimer for medical advice
    """
    text = response_text

    if _contains_pattern(text, _DIAGNOSIS_PATTERNS):
        text = _soften_diagnosis(text)

    if _contains_pattern(text, _MEDICATION_PATTERNS):
        text = _remove_dosing(text)

    # Add emergency warning if user asked about emergency symptoms
    prefix = ""
    if _has_emergency_keywords(user_query) and "⚠️" not in text[:50]:
        prefix = EMERGENCY_WARNING

    # Add disclaimer only for substantive medical responses (>100 chars)
    if len(text) > 100 and DISCLAIMER_AR not in text:
        text = text + DISCLAIMER_AR

    return prefix + text


_INJECTION_PATTERNS = [
    # Prompt override attempts
    r"ignore\s+(previous|all|above|prior)\s+(instructions?|prompts?|context)",
    r"disregard\s+(all|your|previous)\s+(instructions?|rules?|guidelines?)",
    r"you\s+are\s+now\s+(a|an|the)\s+\w+",
    r"(act|pretend|behave|roleplay)\s+as\s+(if\s+you\s+(are|were)\s+)?(\w+\s*){1,4}",
    r"forget\s+your\s+(training|guidelines?|instructions?|rules?)",
    r"(system\s+)?prompt\s*(:|=|is|says?)\s*[\"']",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    # Arabic injection patterns
    r"تجاهل\s+(التعليمات|السياق|الأوامر)",
    r"أنت\s+(الآن|الان)\s+\w+",
    r"تصرف\s+كـ?\w+",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# Characters/sequences to strip before inserting into prompts
_PROMPT_DELIMITERS = re.compile(r"(<\|.*?\|>|###|---+|===+|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>)")


def sanitize_query(query: str, max_len: int = 1000) -> str:
    """
    Strip prompt-injection attempts from user input before RAG/LLM insertion.
    Returns cleaned query; never raises.
    """
    q = query[:max_len]
    q = _PROMPT_DELIMITERS.sub(" ", q)
    if _INJECTION_RE.search(q):
        # Blank out the injection fragment but keep any preceding medical text
        q = _INJECTION_RE.sub("[محتوى محذوف]", q)
    return q.strip()


def check_emergency(user_query: str) -> str | None:
    """
    Returns an immediate emergency response string if query contains
    emergency keywords, else None.
    Only fires for very clear emergency phrases.
    """
    critical = ["ألم صدر شديد", "صعوبة تنفس حادة", "فقدان وعي", "نزيف لا يتوقف"]
    q = user_query.lower()
    if any(kw in q for kw in critical):
        return (
            "⚠️ هذه الأعراض تستدعي التوجه فوراً لأقرب طوارئ أو الاتصال بالإسعاف.\n"
            "لا تنتظر ولا تقود بنفسك. أطلب المساعدة الآن."
        )
    return None
