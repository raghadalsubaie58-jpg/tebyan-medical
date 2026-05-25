"""
Risk Engine — evidence-based health risk scoring for Arabic medical reports.

Primary risks:
  - diabetes_risk     (Type 2 diabetes / prediabetes)
  - cardiovascular_risk (heart disease / atherosclerosis)
  - anemia_risk       (iron-deficiency or chronic)
  - kidney_risk       (CKD staging)
  - liver_risk        (hepatic dysfunction)
  - thyroid_risk      (hypo/hyperthyroidism)

Each risk scorer:
  1. Checks clinical thresholds (evidence-based cutoffs)
  2. Accumulates a weighted score (0–100)
  3. Provides an Arabic explanation of contributing factors
  4. Returns confidence based on how many markers are available

When sklearn/XGBoost models are placed in services/risk/models/,
they override the rule-based scores for those conditions.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .feature_extractor import FeatureExtractor, FeatureVector

log = logging.getLogger("tebyan.risk")

_EXTRACTOR = FeatureExtractor()

# ── Risk result types ──────────────────────────────────────────────────────

@dataclass
class RiskScore:
    condition:   str           # e.g. "diabetes_risk"
    score:       float         # 0–100
    level:       str           # "low" | "moderate" | "high" | "critical"
    confidence:  str           # "high" | "medium" | "low"
    label_ar:    str           # Human-readable Arabic label
    factors:     list[str]     # contributing factors (Arabic)
    recommendation: str        # 1-sentence Arabic recommendation
    source:      str = "rules" # "rules" | "ml_xgboost" | "ml_rf"


@dataclass
class RiskReport:
    risks:       list[RiskScore] = field(default_factory=list)
    top_risk:    RiskScore | None = None
    overall_ar:  str = ""
    features_used: dict = field(default_factory=dict)


# ── Helpers ────────────────────────────────────────────────────────────────

def _level(score: float) -> str:
    if score >= 70: return "critical"
    if score >= 45: return "high"
    if score >= 20: return "moderate"
    return "low"

def _level_ar(level: str) -> str:
    return {"low": "منخفض", "moderate": "متوسط", "high": "مرتفع", "critical": "حرج"}.get(level, level)

def _conf(n_markers: int, n_available: int) -> str:
    if n_available == 0: return "low"
    ratio = n_available / max(n_markers, 1)
    if ratio >= 0.7: return "high"
    if ratio >= 0.4: return "medium"
    return "low"


# ── Individual risk scorers ────────────────────────────────────────────────

def _score_diabetes(fv: FeatureVector) -> RiskScore:
    score, factors = 0.0, []
    markers = ["glucose", "hba1c", "insulin", "homa_ir"]
    available = sum(1 for m in markers if fv.has(m))

    if fv.has("hba1c"):
        a1c = fv.get("hba1c")
        if a1c >= 6.5:
            score += 50; factors.append(f"HbA1c مرتفع جداً ({a1c:.1f}%) — يدل على السكري")
        elif a1c >= 5.7:
            score += 30; factors.append(f"HbA1c حدّي ({a1c:.1f}%) — ما قبل السكري")

    if fv.has("glucose"):
        g = fv.get("glucose")
        if g >= 126:
            score += 40; factors.append(f"سكر الصيام مرتفع ({g:.0f} mg/dL) — مستوى السكري")
        elif g >= 100:
            score += 20; factors.append(f"سكر الصيام حدّي ({g:.0f} mg/dL)")

    if fv.has("homa_ir") and fv.get("homa_ir") >= 2.5:
        score += 15; factors.append("مقاومة الأنسولين مرتفعة")

    if fv.has("triglycerides") and fv.get("triglycerides") >= 200:
        score += 10; factors.append("ثلاثيات الجليسريد مرتفعة — مرتبطة بمقاومة الأنسولين")

    score = min(score, 100)
    lvl   = _level(score)
    rec   = "يُنصح بإجراء منحنى سكر واستشارة طبيب الغدد." if score >= 45 else "تابع نظامك الغذائي ومستوى السكر."
    return RiskScore(
        condition="diabetes_risk", score=round(score, 1), level=lvl,
        confidence=_conf(4, available), label_ar=f"خطر السكري — {_level_ar(lvl)}",
        factors=factors, recommendation=rec,
    )


def _score_cardiovascular(fv: FeatureVector) -> RiskScore:
    score, factors = 0.0, []
    markers = ["ldl", "hdl", "cholesterol", "triglycerides"]
    available = sum(1 for m in markers if fv.has(m))

    if fv.has("ldl"):
        ldl = fv.get("ldl")
        if ldl >= 190:
            score += 45; factors.append(f"LDL مرتفع جداً ({ldl:.0f} mg/dL)")
        elif ldl >= 160:
            score += 30; factors.append(f"LDL مرتفع ({ldl:.0f} mg/dL)")
        elif ldl >= 130:
            score += 15; factors.append(f"LDL حدّي ({ldl:.0f} mg/dL)")

    if fv.has("hdl"):
        hdl = fv.get("hdl")
        if hdl < 35:
            score += 25; factors.append(f"HDL منخفض جداً ({hdl:.0f} mg/dL) — تراجع الحماية القلبية")
        elif hdl < 40:
            score += 12; factors.append(f"HDL منخفض ({hdl:.0f} mg/dL)")

    if fv.has("triglycerides"):
        tg = fv.get("triglycerides")
        if tg >= 500:
            score += 30; factors.append(f"⚠️ ثلاثيات الجليسريد حرجة ({tg:.0f}) — خطر التهاب البنكرياس")
        elif tg >= 200:
            score += 15; factors.append(f"ثلاثيات الجليسريد مرتفعة ({tg:.0f} mg/dL)")

    if fv.has("cholesterol"):
        tc = fv.get("cholesterol")
        if tc >= 240:
            score += 15; factors.append(f"كوليسترول كلي مرتفع ({tc:.0f} mg/dL)")

    # Synergy penalty: low HDL + high LDL = double risk
    if fv.is_low("hdl") and fv.is_high("ldl"):
        score = min(score + 15, 100); factors.append("مثلث الخطر: HDL منخفض + LDL مرتفع")

    score = min(score, 100)
    lvl   = _level(score)
    rec   = "راجع طبيب القلب وتحدث عن دواء الستاتين." if score >= 45 else "تابع نظامك الغذائي وممارسة الرياضة."
    return RiskScore(
        condition="cardiovascular_risk", score=round(score, 1), level=lvl,
        confidence=_conf(4, available), label_ar=f"خطر القلب والأوعية — {_level_ar(lvl)}",
        factors=factors, recommendation=rec,
    )


def _score_anemia(fv: FeatureVector) -> RiskScore:
    score, factors = 0.0, []
    markers = ["hemoglobin", "ferritin", "iron", "mcv"]
    available = sum(1 for m in markers if fv.has(m))

    if fv.has("hemoglobin"):
        hb = fv.get("hemoglobin")
        if hb < 7:
            score += 80; factors.append(f"هيموجلوبين حرج ({hb:.1f} g/dL) — فقر دم شديد")
        elif hb < 10:
            score += 55; factors.append(f"هيموجلوبين منخفض ({hb:.1f} g/dL) — فقر دم متوسط")
        elif hb < 12:
            score += 30; factors.append(f"هيموجلوبين حدّي ({hb:.1f} g/dL) — فقر دم خفيف")

    if fv.has("ferritin"):
        fer = fv.get("ferritin")
        if fer < 12:
            score += 20; factors.append(f"فيريتين منخفض جداً ({fer:.0f} ng/mL) — نضوب مخازن الحديد")
        elif fer < 30:
            score += 10; factors.append(f"فيريتين منخفض ({fer:.0f} ng/mL)")

    if fv.has("mcv"):
        mcv = fv.get("mcv")
        if mcv < 70:
            score += 15; factors.append(f"MCV منخفض ({mcv:.0f} fL) — يدل على نقص الحديد")
        elif mcv > 100:
            score += 10; factors.append(f"MCV مرتفع ({mcv:.0f} fL) — محتمل نقص B12/فولات")

    score = min(score, 100)
    lvl   = _level(score)
    rec   = "يُنصح بإجراء فحص فيريتين وحديد وفيتامين B12 وزيارة طبيب الدم." if score >= 45 else "تابع مستوى الحديد في الفحوصات القادمة."
    return RiskScore(
        condition="anemia_risk", score=round(score, 1), level=lvl,
        confidence=_conf(4, available), label_ar=f"خطر فقر الدم — {_level_ar(lvl)}",
        factors=factors, recommendation=rec,
    )


def _score_kidney(fv: FeatureVector) -> RiskScore:
    score, factors = 0.0, []
    markers = ["creatinine", "egfr", "bun", "uric_acid"]
    available = sum(1 for m in markers if fv.has(m))

    if fv.has("egfr"):
        gfr = fv.get("egfr")
        if gfr < 15:
            score += 90; factors.append(f"eGFR حرج ({gfr:.0f}) — الفشل الكلوي G5")
        elif gfr < 30:
            score += 70; factors.append(f"eGFR منخفض جداً ({gfr:.0f}) — CKD G4")
        elif gfr < 45:
            score += 45; factors.append(f"eGFR منخفض ({gfr:.0f}) — CKD G3b")
        elif gfr < 60:
            score += 25; factors.append(f"eGFR حدّي ({gfr:.0f}) — CKD G3a")

    if fv.has("creatinine"):
        cr = fv.get("creatinine")
        if cr > 3:
            score = max(score, 60); factors.append(f"كرياتينين مرتفع جداً ({cr:.1f} mg/dL)")
        elif cr > 1.5:
            score = max(score, 30); factors.append(f"كرياتينين مرتفع ({cr:.1f} mg/dL)")

    if fv.has("bun") and fv.has("creatinine"):
        ratio = fv.get("bun") / max(fv.get("creatinine"), 0.1)
        if ratio > 20:
            score += 10; factors.append(f"نسبة BUN/Creatinine مرتفعة ({ratio:.0f}) — محتمل جفاف أو نزيف خفي")

    score = min(score, 100)
    lvl   = _level(score)
    rec   = "يُنصح بمراجعة طبيب الكلى وتجنب الأدوية الكلوية السمية." if score >= 30 else "تابع وظائف الكلى دورياً."
    return RiskScore(
        condition="kidney_risk", score=round(score, 1), level=lvl,
        confidence=_conf(4, available), label_ar=f"خطر أمراض الكلى — {_level_ar(lvl)}",
        factors=factors, recommendation=rec,
    )


def _score_liver(fv: FeatureVector) -> RiskScore:
    score, factors = 0.0, []
    markers = ["alt", "ast", "alp", "ggt", "bilirubin", "albumin"]
    available = sum(1 for m in markers if fv.has(m))

    if fv.has("alt"):
        alt = fv.get("alt")
        if alt > 500:
            score += 60; factors.append(f"ALT مرتفع جداً ({alt:.0f} U/L) — التهاب كبد حاد")
        elif alt > 100:
            score += 35; factors.append(f"ALT مرتفع ({alt:.0f} U/L)")
        elif alt > 56:
            score += 15; factors.append(f"ALT حدّي ({alt:.0f} U/L)")

    if fv.has("ast"):
        ast = fv.get("ast")
        if ast > 500:
            score += 40; factors.append(f"AST مرتفع جداً ({ast:.0f} U/L)")
        elif ast > 100:
            score += 20; factors.append(f"AST مرتفع ({ast:.0f} U/L)")

    if fv.has("bilirubin") and fv.get("bilirubin") > 3:
        score += 20; factors.append(f"بيليروبين مرتفع ({fv.get('bilirubin'):.1f} mg/dL) — اليرقان")

    if fv.has("albumin") and fv.get("albumin") < 3:
        score += 20; factors.append(f"ألبومين منخفض ({fv.get('albumin'):.1f} g/dL) — اختلال وظيفي")

    if fv.has("inr") and fv.get("inr") > 1.5:
        score += 15; factors.append(f"INR مرتفع ({fv.get('inr'):.1f}) — اضطراب التخثر الكبدي")

    score = min(score, 100)
    lvl   = _level(score)
    rec   = "يُنصح بمراجعة طبيب الجهاز الهضمي وإجراء سونار الكبد." if score >= 30 else "تابع إنزيمات الكبد دورياً."
    return RiskScore(
        condition="liver_risk", score=round(score, 1), level=lvl,
        confidence=_conf(6, available), label_ar=f"خطر أمراض الكبد — {_level_ar(lvl)}",
        factors=factors, recommendation=rec,
    )


def _score_thyroid(fv: FeatureVector) -> RiskScore:
    score, factors = 0.0, []
    markers = ["tsh", "ft4", "ft3"]
    available = sum(1 for m in markers if fv.has(m))

    if fv.has("tsh"):
        tsh = fv.get("tsh")
        if tsh > 10:
            score += 60; factors.append(f"TSH مرتفع جداً ({tsh:.2f} mIU/L) — قصور درقي حاد")
        elif tsh > 4:
            score += 30; factors.append(f"TSH مرتفع ({tsh:.2f} mIU/L) — قصور درقي خفيف")
        elif tsh < 0.1:
            score += 50; factors.append(f"TSH منخفض جداً ({tsh:.3f} mIU/L) — فرط درقي")
        elif tsh < 0.4:
            score += 25; factors.append(f"TSH منخفض ({tsh:.3f} mIU/L)")

    if fv.has("ft4") and fv.is_low("ft4"):
        score += 20; factors.append(f"FT4 منخفض ({fv.get('ft4'):.2f}) — تأكيد قصور درقي")

    score = min(score, 100)
    lvl   = _level(score)
    rec   = "يُنصح بمراجعة طبيب الغدد الصماء وفحص Anti-TPO." if score >= 30 else "تابع مستوى TSH دورياً."
    return RiskScore(
        condition="thyroid_risk", score=round(score, 1), level=lvl,
        confidence=_conf(3, available), label_ar=f"خطر أمراض الغدة الدرقية — {_level_ar(lvl)}",
        factors=factors, recommendation=rec,
    )


# ── ML model loader (optional override) ───────────────────────────────────

def _try_load_ml_model(condition: str):
    """
    Load a trained sklearn/XGBoost model from services/risk/models/.
    Returns the model if found, else None (falls back to rules).
    """
    model_path = Path(__file__).parent / "models" / f"{condition}.pkl"
    if not model_path.exists():
        return None
    try:
        import pickle
        with open(model_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        log.warning("[risk] failed to load ML model %s: %s", condition, e)
        return None


# ── Main engine ────────────────────────────────────────────────────────────

class RiskEngine:
    """
    Computes multi-condition health risk from a findings list.
    Uses evidence-based rule scorers by default.
    ML models (XGBoost/RandomForest) auto-loaded from services/risk/models/
    when available and override rule scores for that condition.
    """

    _SCORERS = [
        ("diabetes_risk",       _score_diabetes),
        ("cardiovascular_risk", _score_cardiovascular),
        ("anemia_risk",         _score_anemia),
        ("kidney_risk",         _score_kidney),
        ("liver_risk",          _score_liver),
        ("thyroid_risk",        _score_thyroid),
    ]

    def __init__(self):
        self._extractor = FeatureExtractor()
        self._ml_models: dict = {}
        for cond, _ in self._SCORERS:
            m = _try_load_ml_model(cond)
            if m:
                self._ml_models[cond] = m
                log.info("[risk] ML model loaded for %s", cond)

    def assess(self, findings: list[dict]) -> RiskReport:
        fv   = self._extractor.extract(findings)
        risks: list[RiskScore] = []

        for cond, scorer in self._SCORERS:
            try:
                rs = scorer(fv)
                # Override with ML model if available and conditions are met
                if cond in self._ml_models and fv.values:
                    rs = self._ml_predict(cond, fv, rs)
                if rs.factors:   # only include risks with evidence
                    risks.append(rs)
            except Exception as e:
                log.warning("[risk] scorer %s failed: %s", cond, e)

        risks.sort(key=lambda r: r.score, reverse=True)
        top = risks[0] if risks else None

        overall = self._overall_summary(risks)
        return RiskReport(
            risks=risks,
            top_risk=top,
            overall_ar=overall,
            features_used={"count": len(fv.values), "names": list(fv.values.keys())},
        )

    def _ml_predict(self, cond: str, fv: FeatureVector, fallback: RiskScore) -> RiskScore:
        """Override rule score with ML prediction if confidence is sufficient."""
        try:
            model = self._ml_models[cond]
            import numpy as np
            feature_names = list(_EXTRACTOR._FEATURE_MAP.keys()) if hasattr(_EXTRACTOR, "_FEATURE_MAP") else list(fv.values.keys())
            x = np.array([[fv.get(f) for f in feature_names]])
            # Handle NaN via median imputation
            col_means = np.nanmedian(x, axis=0)
            inds = np.where(np.isnan(x))
            x[inds] = np.take(col_means, inds[1])
            prob = float(model.predict_proba(x)[0][1])
            ml_score = round(prob * 100, 1)
            return RiskScore(
                condition=fallback.condition, score=ml_score, level=_level(ml_score),
                confidence="high", label_ar=fallback.label_ar.replace(_level_ar(fallback.level), _level_ar(_level(ml_score))),
                factors=fallback.factors, recommendation=fallback.recommendation,
                source="ml_xgboost",
            )
        except Exception as e:
            log.warning("[risk] ML predict failed for %s: %s — using rules", cond, e)
            return fallback

    @staticmethod
    def _overall_summary(risks: list[RiskScore]) -> str:
        if not risks:
            return "لم يُكتشف أي خطر صحي بارز من النتائج المتاحة."
        critical = [r for r in risks if r.level == "critical"]
        high     = [r for r in risks if r.level == "high"]
        if critical:
            return f"تنبيه: مستوى خطر حرج في {', '.join(r.label_ar.split(' — ')[0] for r in critical)}. يُنصح بمراجعة الطبيب فوراً."
        if high:
            return f"مستوى خطر مرتفع في {', '.join(r.label_ar.split(' — ')[0] for r in high)}. يُنصح بمتابعة طبية قريبة."
        moderate = [r for r in risks if r.level == "moderate"]
        if moderate:
            return f"بعض المؤشرات تستدعي المتابعة: {', '.join(r.label_ar.split(' — ')[0] for r in moderate)}."
        return "المؤشرات الصحية ضمن الحدود المقبولة. استمر في التحاليل الدورية."
