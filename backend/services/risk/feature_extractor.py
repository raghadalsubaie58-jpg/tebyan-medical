"""
Feature Extractor — converts a findings list into a normalized numeric feature vector
suitable for risk model inference (ML or rule-based).

Each feature is named, typed, and bounded so models stay interpretable.
Missing values are encoded as NaN (→ median imputation in ML pipeline).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field


# ── Feature definitions ────────────────────────────────────────────────────

# Maps canonical feature name → (list of finding name substrings to search)
_FEATURE_MAP: dict[str, list[str]] = {
    # Diabetes markers
    "glucose":        ["glucose", "سكر صيام", "fasting glucose", "blood sugar"],
    "hba1c":          ["hba1c", "a1c", "glycated", "سكر تراكمي"],
    "insulin":        ["insulin", "انسولين"],
    "homa_ir":        ["homa", "homa-ir", "مقاومة الانسولين"],
    # Lipid panel
    "cholesterol":    ["cholesterol", "total cholesterol", "كوليسترول"],
    "ldl":            ["ldl", "low density"],
    "hdl":            ["hdl", "high density"],
    "triglycerides":  ["triglycerides", "tg", "دهون ثلاثية"],
    # CBC
    "hemoglobin":     ["hemoglobin", "hgb", "هيموجلوبين"],
    "hematocrit":     ["hematocrit", "hct", "هيماتوكريت"],
    "wbc":            ["wbc", "white blood", "كريات بيضاء"],
    "platelets":      ["platelets", "plt", "صفائح"],
    "rbc":            ["rbc", "red blood", "كريات حمراء"],
    "mcv":            ["mcv"],
    "mch":            ["mch"],
    # Kidney
    "creatinine":     ["creatinine", "كرياتينين"],
    "bun":            ["bun", "blood urea nitrogen", "يوريا"],
    "uric_acid":      ["uric acid", "حمض البول"],
    "egfr":           ["egfr", "gfr", "glomerular"],
    # Liver
    "alt":            ["alt", "sgpt", "alanine"],
    "ast":            ["ast", "sgot", "aspartate"],
    "alp":            ["alp", "alkaline phosphatase"],
    "ggt":            ["ggt", "gamma"],
    "bilirubin":      ["bilirubin", "بيليروبين"],
    "albumin":        ["albumin", "البومين"],
    # Thyroid
    "tsh":            ["tsh", "thyroid stimulating", "درقية"],
    "ft4":            ["ft4", "free t4", "free thyroxine"],
    "ft3":            ["ft3", "free t3"],
    # Inflammation
    "crp":            ["crp", "c-reactive"],
    "esr":            ["esr", "erythrocyte sedimentation"],
    # Vitamins / minerals
    "vitamin_d":      ["vitamin d", "25-oh", "فيتامين د"],
    "vitamin_b12":    ["vitamin b12", "b12", "cobalamin", "فيتامين ب"],
    "ferritin":       ["ferritin", "فيريتين"],
    "iron":           ["iron", "serum iron", "حديد"],
    "calcium":        ["calcium", "كالسيوم"],
    "sodium":         ["sodium", "na+", "صوديوم"],
    "potassium":      ["potassium", "k+", "بوتاسيوم"],
    # Coagulation
    "pt":             ["pt", "prothrombin time"],
    "inr":            ["inr"],
}


@dataclass
class FeatureVector:
    values: dict[str, float] = field(default_factory=dict)   # name → numeric value or NaN
    statuses: dict[str, str] = field(default_factory=dict)   # name → "normal"|"high"|"low"

    def get(self, name: str) -> float:
        return self.values.get(name, math.nan)

    def is_abnormal(self, name: str) -> bool:
        return self.statuses.get(name, "normal") != "normal"

    def is_high(self, name: str) -> bool:
        return self.statuses.get(name) == "high"

    def is_low(self, name: str) -> bool:
        return self.statuses.get(name) == "low"

    def has(self, name: str) -> bool:
        return not math.isnan(self.get(name))


class FeatureExtractor:
    """
    Converts a list of findings dicts into a FeatureVector.
    Handles Arabic/English names via fuzzy substring matching.
    """

    def extract(self, findings: list[dict]) -> FeatureVector:
        fv = FeatureVector()
        for finding in findings:
            name_lower = (finding.get("name") or finding.get("test_name") or "").lower().strip()
            val_str    = finding.get("value", "")
            status     = finding.get("status", "normal")

            try:
                val = float(val_str)
            except (ValueError, TypeError):
                continue

            for feature, aliases in _FEATURE_MAP.items():
                if any(alias in name_lower for alias in aliases):
                    if feature not in fv.values:
                        fv.values[feature]   = val
                        fv.statuses[feature] = status
                    break

        return fv
