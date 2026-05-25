"""
Query parser — detects language, medical panel, lab tests, and symptoms.
Includes Arabic medical synonym expansion and text normalization.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

# ══════════════════════════════════════════════════════════════════
# Arabic text normalization
# ══════════════════════════════════════════════════════════════════

def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic text for consistent matching:
    - Unify alef variants (أ إ آ → ا)
    - Remove tashkeel (diacritics)
    - Remove tatweel (ـ)
    - Unify teh marbuta and heh
    """
    text = re.sub(r"[أإآ]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"[ؐ-ًؚ-ٟ]", "", text)  # tashkeel
    text = re.sub(r"ـ", "", text)                              # tatweel
    return text.strip()


# ══════════════════════════════════════════════════════════════════
# Arabic Medical Synonym Dictionary
# Maps any Arabic/English term → canonical synonyms for expansion
# ══════════════════════════════════════════════════════════════════

_MEDICAL_SYNONYMS: dict[str, list[str]] = {
    # ── فقر الدم / Anemia ─────────────────────────────────────────
    "فقر الدم":           ["anemia", "hemoglobin low", "هيموجلوبين منخفض", "انيميا"],
    "انيميا":             ["anemia", "فقر الدم", "hemoglobin low", "هيموجلوبين"],
    "هيموجلوبين منخفض":   ["anemia", "فقر الدم", "low hemoglobin", "iron deficiency"],
    "نقص الحديد":         ["iron deficiency", "ferritin low", "فيريتين منخفض", "anemia"],
    "فقر دم":             ["anemia", "hemoglobin", "هيموجلوبين", "iron deficiency"],

    # ── السكري / Diabetes ─────────────────────────────────────────
    "مشاكل السكر":        ["diabetes", "glucose high", "HbA1c", "سكر مرتفع", "hyperglycemia"],
    "سكر مرتفع":          ["high glucose", "hyperglycemia", "diabetes", "HbA1c elevated"],
    "سكر منخفض":          ["hypoglycemia", "low glucose", "نقص السكر"],
    "نقص السكر":          ["hypoglycemia", "low glucose", "سكر منخفض"],
    "مقاومة الانسولين":   ["insulin resistance", "HOMA-IR", "prediabetes", "ما قبل السكري"],
    "ما قبل السكري":      ["prediabetes", "insulin resistance", "glucose borderline"],

    # ── الغدة الدرقية / Thyroid ───────────────────────────────────
    "خمول الغدة":         ["hypothyroidism", "TSH high", "TSH مرتفع", "قصور درقية"],
    "قصور درقية":         ["hypothyroidism", "TSH high", "خمول الغدة الدرقية"],
    "قصور الغدة الدرقيه": ["hypothyroidism", "TSH high", "خمول الغدة"],
    "نشاط الغدة":         ["hyperthyroidism", "TSH low", "TSH منخفض", "فرط درقية"],
    "فرط درقية":          ["hyperthyroidism", "TSH low", "نشاط الغدة الدرقية"],
    "هاشيموتو":           ["Hashimoto", "anti-TPO", "hypothyroidism", "autoimmune thyroid"],

    # ── الكبد / Liver ─────────────────────────────────────────────
    "مشاكل الكبد":        ["liver disease", "ALT high", "AST high", "hepatitis", "كبد دهني"],
    "كبد دهني":           ["fatty liver", "NAFLD", "ALT elevated", "hepatic steatosis"],
    "التهاب الكبد":       ["hepatitis", "ALT high", "AST high", "liver inflammation"],
    "انزيمات الكبد":      ["liver enzymes", "ALT", "AST", "ALP", "GGT"],
    "ارتفاع الانزيمات":   ["elevated liver enzymes", "ALT high", "AST high", "hepatitis"],

    # ── الكلى / Kidney ────────────────────────────────────────────
    "مشاكل الكلى":        ["kidney disease", "creatinine high", "eGFR low", "renal failure"],
    "ضعف الكلى":          ["kidney failure", "creatinine elevated", "eGFR low", "CKD"],
    "فشل كلوي":           ["renal failure", "kidney failure", "creatinine high", "eGFR critical"],
    "حصى الكلى":          ["kidney stones", "uric acid high", "calcium oxalate"],

    # ── القلب والدهون / Cardiology & Lipids ───────────────────────
    "كوليسترول مرتفع":    ["high cholesterol", "hyperlipidemia", "LDL high", "cardiovascular risk"],
    "دهون مرتفعه":        ["high triglycerides", "hyperlipidemia", "cholesterol high"],
    "خطر قلبي":           ["cardiovascular risk", "LDL high", "cholesterol", "heart disease risk"],
    "تصلب الشرايين":      ["atherosclerosis", "LDL high", "cardiovascular", "cholesterol"],

    # ── الغدد والهرمونات / Hormones ──────────────────────────────
    "نقص فيتامين د":      ["vitamin D deficiency", "low vitamin D", "bone health"],
    "نقص ب12":            ["vitamin B12 deficiency", "B12 low", "megaloblastic anemia"],
    "نقص فيتامين ب":      ["vitamin B12 deficiency", "B12 low", "folate deficiency"],

    # ── أعراض عامة / General symptoms ────────────────────────────
    "تعب وارهاق":         ["fatigue", "anemia", "vitamin deficiency", "thyroid", "تعب مزمن"],
    "تعب مزمن":           ["chronic fatigue", "anemia", "thyroid", "vitamin D deficiency"],
    "نتائج مثيرة للقلق":  ["abnormal results", "high values", "low values", "critical values"],
    "نتائج غير طبيعيه":   ["abnormal results", "out of range", "high low values"],
    "نتائج سيئه":         ["abnormal results", "critical values", "out of range"],
    "ضغط الدم":           ["blood pressure", "hypertension", "sodium", "kidney"],
    "التهاب":             ["inflammation", "CRP high", "ESR high", "WBC elevated"],
    "مناعه منخفضه":       ["low immunity", "WBC low", "lymphocytes low", "immune deficiency"],

    # ── حالة حمل / Pregnancy ─────────────────────────────────────
    "تحاليل حمل":         ["pregnancy labs", "hemoglobin pregnancy", "thyroid pregnancy", "glucose pregnancy"],
    "فقر دم حمل":         ["pregnancy anemia", "hemoglobin low pregnancy", "iron deficiency pregnancy"],
}

# Normalized lookup — built once at import
_SYNONYM_LOOKUP: dict[str, list[str]] = {
    normalize_arabic(k): v for k, v in _MEDICAL_SYNONYMS.items()
}


def expand_medical_synonyms(query: str) -> list[str]:
    """
    Find medical synonym expansions for any phrase in the query.
    Returns list of expansion strings (empty if no match).
    """
    q_norm = normalize_arabic(query.lower())
    expansions: list[str] = []
    for term, synonyms in _SYNONYM_LOOKUP.items():
        if term in q_norm:
            expansions.append(" ".join(synonyms[:4]))
    return expansions[:2]  # max 2 synonym expansions


# ══════════════════════════════════════════════════════════════════
# Keyword sets
# ══════════════════════════════════════════════════════════════════

_LAB_AR = {
    "هيموجلوبين", "خضاب الدم", "كريات حمراء", "كريات بيضاء",
    "صفائح دموية", "صفائح", "هيماتوكريت", "سكر", "سكر صيام",
    "سكر تراكمي", "كوليسترول", "دهون ثلاثية", "كرياتينين",
    "يوريا", "بيليروبين", "البومين", "بروتين", "فيريتين",
    "حديد", "فيتامين د", "فيتامين ب12", "كالسيوم", "صوديوم",
    "بوتاسيوم", "حمض البول", "فولات",
}

_LAB_EN = {
    "hemoglobin", "wbc", "rbc", "platelet", "platelets", "hematocrit",
    "glucose", "hba1c", "a1c", "cholesterol", "ldl", "hdl", "triglycerides",
    "creatinine", "bun", "urea", "bilirubin", "albumin", "alt", "ast", "alp",
    "ggt", "sgpt", "sgot", "tsh", "ft3", "ft4", "free t4", "free t3",
    "ferritin", "iron", "vitamin d", "vitamin b12", "b12", "protein",
    "calcium", "sodium", "potassium", "crp", "esr", "folate", "uric acid",
    "cbc", "lft", "kft", "inr", "pt", "egfr", "gfr", "homa-ir", "insulin",
}

_SYMPTOM_AR = {
    "الم", "تعب", "ارهاق", "دوخة", "صداع", "حمى", "سعال",
    "ضيق تنفس", "خفقان", "شحوب", "اصفرار",
    "تورم", "فقدان شهية", "غثيان", "تقيؤ", "اسهال", "امساك",
    "عطش", "برود", "نزيف", "حكة",
}

_SYMPTOM_EN = {
    "pain", "fatigue", "tired", "dizzy", "headache", "fever", "cough",
    "breathless", "palpitation", "pale", "jaundice", "swelling",
    "nausea", "vomiting", "thirst",
}

# ── Panel detection keywords ───────────────────────────────────────────────

_PANEL_KEYWORDS: dict[str, list[str]] = {
    "cbc":      ["hemoglobin", "هيموجلوبين", "wbc", "rbc", "platelet", "صفائح", "cbc",
                 "دم شامل", "hct", "hematocrit", "فقر الدم", "انيميا", "anemia"],
    "thyroid":  ["tsh", "t3", "t4", "ft3", "ft4", "درقية", "thyroid", "هرمون درقي",
                 "هاشيموتو", "جريفز", "خمول الغدة", "قصور درقية", "hypothyroidism", "hyperthyroidism"],
    "liver":    ["alt", "ast", "alp", "ggt", "bilirubin", "albumin", "كبد", "liver",
                 "بيليروبين", "sgpt", "sgot", "lft", "كبد دهني", "التهاب الكبد", "انزيمات"],
    "kidney":   ["creatinine", "bun", "urea", "كلى", "كرياتينين", "kidney", "gfr",
                 "egfr", "kft", "فشل كلوي", "حصى الكلى", "ضعف الكلى"],
    "diabetes": ["glucose", "hba1c", "سكر", "diabetes", "a1c", "سكر تراكمي",
                 "مقاومة الانسولين", "insulin", "homa", "ما قبل السكري"],
    "lipid":    ["cholesterol", "ldl", "hdl", "triglycerides", "كوليسترول",
                 "دهون", "دهنيات", "كوليسترول مرتفع", "تصلب الشرايين"],
}

_PANEL_EXPANSIONS: dict[str, str] = {
    "cbc":      "CBC complete blood count hemoglobin WBC RBC platelets anemia iron deficiency",
    "thyroid":  "thyroid function TSH T4 T3 hypothyroidism hyperthyroidism Hashimoto autoimmune",
    "liver":    "liver function ALT AST ALP bilirubin albumin hepatitis cirrhosis fatty liver",
    "kidney":   "kidney renal function creatinine BUN urea GFR eGFR nephrology CKD",
    "diabetes": "diabetes blood glucose HbA1c insulin resistance glycemic prediabetes HOMA-IR",
    "lipid":    "lipid cholesterol LDL HDL triglycerides cardiovascular risk atherosclerosis",
}


# ══════════════════════════════════════════════════════════════════
# Data class
# ══════════════════════════════════════════════════════════════════

@dataclass
class ParsedQuery:
    original:           str
    normalized:         str
    language:           str
    detected_tests:     list[str] = field(default_factory=list)
    detected_symptoms:  list[str] = field(default_factory=list)
    panel_type:         str | None = None
    topic_type:         str | None = None
    search_expansions:  list[str] = field(default_factory=list)
    synonym_matches:    list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════

def _detect_language(text: str) -> str:
    ar = len(re.findall(r"[؀-ۿ]", text))
    en = len(re.findall(r"[a-zA-Z]", text))
    if ar > en * 1.5:
        return "ar"
    if en > ar * 1.5:
        return "en"
    return "mixed"


def _detect_panel(text_lower: str) -> str | None:
    for panel, kws in _PANEL_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in kws):
            return panel
    return None


def detect_panel(text: str) -> str | None:
    """Public wrapper — accepts raw text, handles normalization internally."""
    norm = normalize_arabic(text.lower())
    result = _detect_panel(norm)
    if not result:
        result = _detect_panel(text.lower())
    return result


# ══════════════════════════════════════════════════════════════════
# Main function
# ══════════════════════════════════════════════════════════════════

def parse_query(query: str) -> ParsedQuery:
    norm_query = normalize_arabic(query)
    lower      = norm_query.lower()
    lang       = _detect_language(query)

    # Lab test detection (normalized)
    detected_tests: list[str] = []
    for kw in _LAB_AR | _LAB_EN:
        if normalize_arabic(kw.lower()) in lower:
            detected_tests.append(kw)

    # Symptom detection (normalized)
    detected_symptoms: list[str] = []
    for kw in _SYMPTOM_AR | _SYMPTOM_EN:
        if normalize_arabic(kw.lower()) in lower:
            detected_symptoms.append(kw)

    panel = detect_panel(query)

    topic_type = (
        "lab_test" if detected_tests
        else "symptom" if detected_symptoms
        else None
    )

    # ── Build search expansions ────────────────────────────────────
    expansions: list[str] = [query]

    # 1. Synonym expansion (Arabic medical synonyms)
    synonym_expansions = expand_medical_synonyms(query)
    synonym_matches    = synonym_expansions[:]
    expansions.extend(synonym_expansions)

    # 2. Panel expansion (bilingual medical terms)
    if panel and panel in _PANEL_EXPANSIONS:
        expansions.append(_PANEL_EXPANSIONS[panel])

    # 3. Detected EN test names
    if detected_tests:
        en_tests = [t for t in detected_tests if re.search(r"[a-zA-Z]", t)]
        if en_tests:
            expansions.append(" ".join(en_tests[:5]))

    return ParsedQuery(
        original=query,
        normalized=norm_query,
        language=lang,
        detected_tests=list(set(detected_tests)),
        detected_symptoms=list(set(detected_symptoms)),
        panel_type=panel,
        topic_type=topic_type,
        search_expansions=list(dict.fromkeys(expansions))[:4],
        synonym_matches=synonym_matches,
    )
