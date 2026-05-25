"""
Fast in-memory normal range lookup.
Used for runtime validation — faster than loading JSON schemas.
"""
from __future__ import annotations

# (low, high) per gender key. Keys are lowercase, underscored.
NORMAL_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    # CBC
    "hemoglobin":    {"adult_male": (13.5, 17.5), "adult_female": (12.0, 15.5), "adult": (11.0, 17.5), "children": (11.5, 15.5)},
    "hgb":           {"adult_male": (13.5, 17.5), "adult_female": (12.0, 15.5), "adult": (11.0, 17.5)},
    "hb":            {"adult_male": (13.5, 17.5), "adult_female": (12.0, 15.5), "adult": (11.0, 17.5)},
    "wbc":           {"adult": (4.0, 11.0), "children": (5.0, 15.0)},
    "rbc":           {"adult_male": (4.5, 5.9), "adult_female": (4.0, 5.2), "adult": (4.0, 5.9)},
    "platelets":     {"adult": (150.0, 400.0)},
    "plt":           {"adult": (150.0, 400.0)},
    "hematocrit":    {"adult_male": (41.0, 53.0), "adult_female": (36.0, 48.0), "adult": (36.0, 53.0)},
    "hct":           {"adult_male": (41.0, 53.0), "adult_female": (36.0, 48.0), "adult": (36.0, 53.0)},
    "mcv":           {"adult": (80.0, 100.0)},
    "mch":           {"adult": (27.0, 33.0)},
    "mchc":          {"adult": (32.0, 36.0)},
    "neutrophils":   {"adult": (50.0, 70.0)},
    "lymphocytes":   {"adult": (20.0, 40.0)},
    "monocytes":     {"adult": (2.0, 8.0)},
    "eosinophils":   {"adult": (1.0, 4.0)},
    "basophils":     {"adult": (0.0, 1.0)},

    # Thyroid
    "tsh":           {"adult": (0.4, 4.0), "pregnant": (0.1, 2.5), "elderly": (0.4, 5.0)},
    "ft4":           {"adult": (0.8, 1.8)},
    "free_t4":       {"adult": (0.8, 1.8)},
    "ft3":           {"adult": (2.3, 4.2)},
    "free_t3":       {"adult": (2.3, 4.2)},
    "anti_tpo":      {"adult": (0.0, 34.0)},
    "anti-tpo":      {"adult": (0.0, 34.0)},

    # Liver
    "alt":           {"adult_male": (7.0, 40.0), "adult_female": (7.0, 35.0), "adult": (7.0, 40.0)},
    "sgpt":          {"adult_male": (7.0, 40.0), "adult_female": (7.0, 35.0), "adult": (7.0, 40.0)},
    "ast":           {"adult_male": (10.0, 40.0), "adult_female": (10.0, 35.0), "adult": (10.0, 40.0)},
    "sgot":          {"adult_male": (10.0, 40.0), "adult_female": (10.0, 35.0), "adult": (10.0, 40.0)},
    "alp":           {"adult": (44.0, 147.0), "children": (50.0, 350.0)},
    "ggt":           {"adult_male": (8.0, 61.0), "adult_female": (5.0, 36.0), "adult": (5.0, 61.0)},
    "bilirubin":     {"adult": (0.2, 1.2)},
    "total_bilirubin":{"adult": (0.2, 1.2)},
    "direct_bilirubin":{"adult": (0.0, 0.3)},
    "albumin":       {"adult": (3.5, 5.0)},
    "alb":           {"adult": (3.5, 5.0)},
    "total_protein": {"adult": (6.0, 8.3)},

    # Kidney
    "creatinine":    {"adult_male": (0.7, 1.3), "adult_female": (0.5, 1.1), "adult": (0.5, 1.3)},
    "bun":           {"adult": (8.0, 25.0)},
    "urea":          {"adult": (15.0, 45.0)},
    "uric_acid":     {"adult_male": (3.4, 7.0), "adult_female": (2.4, 6.0), "adult": (2.4, 7.0)},
    "egfr":          {"adult": (60.0, 999.0)},

    # Lipids
    "cholesterol":   {"adult": (0.0, 200.0)},
    "ldl":           {"adult": (0.0, 100.0)},
    "hdl":           {"adult_male": (40.0, 999.0), "adult_female": (50.0, 999.0), "adult": (40.0, 999.0)},
    "triglycerides": {"adult": (0.0, 150.0)},
    "tg":            {"adult": (0.0, 150.0)},

    # Diabetes
    "glucose":       {"adult": (70.0, 99.0)},
    "fasting_glucose":{"adult": (70.0, 99.0)},
    "hba1c":         {"adult": (4.0, 5.6)},
    "a1c":           {"adult": (4.0, 5.6)},

    # Electrolytes
    "sodium":        {"adult": (136.0, 145.0)},
    "potassium":     {"adult": (3.5, 5.0)},
    "chloride":      {"adult": (98.0, 106.0)},
    "calcium":       {"adult": (8.5, 10.5)},
    "magnesium":     {"adult": (1.7, 2.2)},
    "phosphorus":    {"adult": (2.5, 4.5)},

    # Iron studies
    "ferritin":      {"adult_male": (24.0, 336.0), "adult_female": (11.0, 307.0), "adult": (11.0, 336.0)},
    "iron":          {"adult": (60.0, 170.0)},
    "tibc":          {"adult": (250.0, 370.0)},

    # Vitamins
    "vitamin_d":     {"adult": (20.0, 50.0)},
    "vitamin_b12":   {"adult": (200.0, 900.0)},
    "b12":           {"adult": (200.0, 900.0)},
    "folate":        {"adult": (2.7, 17.0)},

    # Inflammation
    "crp":           {"adult": (0.0, 5.0)},
    "esr":           {"adult_male": (0.0, 15.0), "adult_female": (0.0, 20.0), "adult": (0.0, 20.0)},

    # Coagulation
    "pt":            {"adult": (11.0, 13.5)},
    "inr":           {"adult": (0.8, 1.2)},
    "aptt":          {"adult": (25.0, 35.0)},

    # Hormones
    "prolactin":     {"adult_male": (2.0, 18.0), "adult_female": (2.0, 29.0), "adult": (2.0, 29.0)},
    "testosterone":  {"adult_male": (300.0, 1000.0), "adult_female": (15.0, 70.0)},
    "cortisol":      {"adult": (5.0, 23.0)},
}


def lookup(name: str, gender: str = "adult") -> tuple[float, float] | None:
    """
    Fast range lookup. Returns (low, high) or None.
    name: test name (case-insensitive, spaces → underscores)
    gender: 'adult', 'adult_male', 'adult_female', 'children', 'pregnant', 'elderly'
    """
    key = name.lower().strip().replace(" ", "_").replace("-", "_").replace("/", "_")
    entry = NORMAL_RANGES.get(key)
    if not entry:
        return None
    gender_key = f"adult_{gender}" if gender in ("male", "female") else gender
    return entry.get(gender_key) or entry.get("adult")


def classify(name: str, value: float, gender: str = "adult") -> str:
    """Return 'low', 'normal', 'high', or 'unknown'."""
    rng = lookup(name, gender)
    if rng is None:
        return "unknown"
    lo, hi = rng
    if value < lo:
        return "low"
    if value > hi:
        return "high"
    return "normal"
