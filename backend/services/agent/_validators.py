"""
Shared validation helpers for the analysis pipeline.
Mirrors logic from main.py so pipeline tools stay pure and testable.
"""
from __future__ import annotations
import re

# ── Physiologically impossible bounds ─────────────────────────────────────

_IMPOSSIBLE_EXPLICIT: dict[str, tuple[float, float]] = {
    "hemoglobin":   (1.0,    25.0),
    "hgb":          (1.0,    25.0),
    "rbc":          (0.5,    10.0),
    "wbc":          (0.1,   100.0),
    "platelets":    (1.0,  2000.0),
    "plt":          (1.0,  2000.0),
    "hematocrit":   (5.0,    70.0),
    "hct":          (5.0,    70.0),
    "glucose":      (10.0, 2000.0),
    "hba1c":        (2.0,    20.0),
    "cholesterol":  (50.0, 1000.0),
    "triglycerides":(10.0, 5000.0),
    "hdl":          (5.0,   200.0),
    "ldl":          (5.0,   500.0),
    "creatinine":   (0.1,    30.0),
    "bun":          (1.0,   300.0),
    "urea":         (1.0,   300.0),
    "alt":          (1.0,  5000.0),
    "ast":          (1.0,  5000.0),
    "alp":          (1.0,  3000.0),
    "bilirubin":    (0.01,   50.0),
    "albumin":      (0.5,    10.0),
    "tsh":          (0.001, 100.0),
    "sodium":       (100.0, 180.0),
    "potassium":    (1.0,    10.0),
    "calcium":      (1.0,    20.0),
    "ferritin":     (1.0, 50000.0),
    "iron":         (5.0,   500.0),
    "crp":          (0.0,   500.0),
    "esr":          (0.0,   200.0),
    "uric_acid":    (0.5,    20.0),
    "prolactin":    (0.1,   500.0),
    "testosterone": (1.0,  2000.0),
    "pt":           (5.0,   100.0),
    "inr":          (0.5,    15.0),
}

_IGNORE_NAMES = frozenset([
    "page", "id", "patient", "date", "sex", "age", "mrn", "doctor",
    "physician", "result", "unit", "range", "validated", "approved",
    "interpretation", "ref",
])


def is_impossible_value(name: str, value: str) -> bool:
    try:
        val = float(value)
        name_lower = name.lower()
        for key, (lo, hi) in _IMPOSSIBLE_EXPLICIT.items():
            if key in name_lower:
                return val < lo or val > hi
    except Exception:
        pass
    return False


def is_valid_test(name: str) -> bool:
    n = str(name).lower()
    return not any(x in n for x in _IGNORE_NAMES) and len(str(name).strip()) > 1


def get_status(value: str, range_str: str, name: str = "") -> str:
    try:
        val = float(value)
        nums = re.findall(r"\d+\.?\d*", str(range_str))
        if len(nums) >= 2:
            lo, hi = float(nums[0]), float(nums[1])
            if val < lo:
                return "low"
            if val > hi:
                return "high"
            return "normal"
        if name:
            try:
                from medical_kb.reference.normal_ranges import classify as nr_classify
                result = nr_classify(name, val)
                if result != "unknown":
                    return result
            except Exception:
                pass
    except Exception:
        pass
    return "normal"
