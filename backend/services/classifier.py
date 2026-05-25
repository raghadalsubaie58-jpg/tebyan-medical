"""
Medical Report Classifier — rule-based panel detection from extracted findings.
Works on structured findings list (not raw text) for higher precision.
Supports multi-panel detection (e.g., CBC + Thyroid in the same report).
"""
from __future__ import annotations
from dataclasses import dataclass

# ── Panel keyword signatures ─────────────────────────────────────────────────
# Each panel has primary markers (weight=2) and secondary markers (weight=1)

_PANEL_SIGNATURES: dict[str, dict] = {
    "cbc": {
        "primary":   {"hemoglobin", "hgb", "wbc", "rbc", "platelets", "plt",
                      "هيموجلوبين", "كريات بيضاء", "كريات حمراء", "صفائح"},
        "secondary": {"hematocrit", "hct", "mcv", "mch", "mchc", "neutrophils",
                      "lymphocytes", "monocytes", "eosinophils", "basophils",
                      "هيماتوكريت", "خضاب", "cbc"},
        "min_score": 2,
    },
    "thyroid": {
        "primary":   {"tsh", "ft4", "ft3", "free t4", "free t3",
                      "درقية", "غدة درقية"},
        "secondary": {"t3", "t4", "anti-tpo", "anti tpo", "thyroglobulin",
                      "tpo", "hashimoto", "هاشيموتو"},
        "min_score": 2,
    },
    "liver": {
        "primary":   {"alt", "ast", "sgpt", "sgot", "alp", "ggt",
                      "bilirubin", "albumin",
                      "كبد", "بيليروبين", "البومين"},
        "secondary": {"direct bilirubin", "indirect bilirubin", "total protein",
                      "pt", "inr", "lft", "alk phos",
                      "انزيمات", "بروتين كلي"},
        "min_score": 2,
    },
    "kidney": {
        "primary":   {"creatinine", "egfr", "gfr", "bun", "urea",
                      "كلى", "كرياتينين"},
        "secondary": {"uric acid", "cystatin", "kft", "microalbumin",
                      "يوريا", "حمض البول"},
        "min_score": 2,
    },
    "diabetes": {
        "primary":   {"glucose", "hba1c", "a1c", "fasting glucose",
                      "سكر", "سكر صيام", "سكر تراكمي"},
        "secondary": {"insulin", "homa", "homa-ir", "c-peptide",
                      "postprandial glucose", "random glucose",
                      "انسولين", "مقاومة الانسولين"},
        "min_score": 2,
    },
    "lipid": {
        "primary":   {"cholesterol", "ldl", "hdl", "triglycerides",
                      "كوليسترول", "دهون ثلاثية"},
        "secondary": {"vldl", "non-hdl", "lipoprotein", "lipid panel",
                      "دهنيات", "دهون"},
        "min_score": 2,
    },
}


@dataclass
class ClassificationResult:
    primary_panel: str          # best-match panel code
    all_panels: list[str]       # all panels detected (sorted by score)
    scores: dict[str, float]    # panel -> score
    confidence: str             # "high" | "medium" | "low"


def _normalize(name: str) -> str:
    return name.lower().strip().replace("(", "").replace(")", "").replace("-", " ")


def classify_report(findings: list[dict]) -> ClassificationResult:
    """
    Classify a report into panel types based on extracted findings.

    Args:
        findings: list of dicts with at least {"name": str}

    Returns:
        ClassificationResult with primary_panel and confidence
    """
    names = {_normalize(f.get("name", "")) for f in findings}
    scores: dict[str, float] = {}

    for panel, sig in _PANEL_SIGNATURES.items():
        score = 0.0
        for name in names:
            for kw in sig["primary"]:
                if kw in name or name in kw:
                    score += 2
                    break
            else:
                for kw in sig["secondary"]:
                    if kw in name or name in kw:
                        score += 1
                        break
        scores[panel] = score

    detected = [
        panel for panel, score in scores.items()
        if score >= _PANEL_SIGNATURES[panel]["min_score"]
    ]
    detected.sort(key=lambda p: scores[p], reverse=True)

    if not detected:
        primary = ""
        confidence = "low"
    else:
        primary = detected[0]
        top_score = scores[primary]
        if top_score >= 6:
            confidence = "high"
        elif top_score >= 3:
            confidence = "medium"
        else:
            confidence = "low"

    return ClassificationResult(
        primary_panel=primary,
        all_panels=detected,
        scores=scores,
        confidence=confidence,
    )


def classify_from_text(text: str) -> str:
    """
    Lightweight text-based classification for search queries.
    Returns panel code or empty string.
    Wraps existing detect_panel logic for backward compatibility.
    """
    from services.search.query_parser import detect_panel
    return detect_panel(text) or ""
