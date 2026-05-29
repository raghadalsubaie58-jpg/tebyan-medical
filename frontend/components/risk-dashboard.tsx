"use client"

import { useEffect, useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown, CheckCircle2, ShieldAlert, AlertTriangle, Info } from "lucide-react"
import { RadialBarChart, RadialBar, Cell, ResponsiveContainer } from "recharts"
import type { AnalysisResult } from "@/app/page"

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"

// ── Types ─────────────────────────────────────────────────────────────────

interface RiskScore {
  condition:      string
  score:          number
  level:          "low" | "moderate" | "high" | "critical"
  confidence:     "high" | "medium" | "low"
  label_ar:       string
  factors:        string[]
  recommendation: string
  source:         "rules" | "ml_xgboost" | "ml_rf"
}

interface RiskReport {
  risks:         RiskScore[]
  top_risk:      { condition: string; score: number; level: string; label_ar: string } | null
  overall_ar:    string
  features_used: { count: number; names: string[] }
}

// ── Constants ─────────────────────────────────────────────────────────────

const LEVEL_COLOUR: Record<string, string> = {
  low:      "#22c55e",
  moderate: "#f59e0b",
  high:     "#ef4444",
  critical: "#7c3aed",
}

const LEVEL_LABEL_AR: Record<string, string> = {
  low:      "منخفض",
  moderate: "متوسط",
  high:     "مرتفع",
  critical: "حرج",
}

const CONFIDENCE_CFG = {
  high: {
    label: "ثقة عالية",
    dot:   "bg-green-500",
    ring:  "bg-green-500/10 border-green-500/20 text-green-700 dark:text-green-400",
    note:  "تم تحليل التقرير بثقة عالية بناءً على بيانات واضحة وكافية.",
  },
  medium: {
    label: "ثقة متوسطة",
    dot:   "bg-amber-500",
    ring:  "bg-amber-500/10 border-amber-500/20 text-amber-700 dark:text-amber-400",
    note:  "بعض النتائج قد تكون تقديرية — بعض القيم الطبية لم تُستخرج بوضوح.",
  },
  low: {
    label: "ثقة منخفضة",
    dot:   "bg-red-500",
    ring:  "bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-400",
    note:  "دقة التحليل منخفضة بسبب غموض التقرير أو نقص البيانات. يُنصح برفع صورة أوضح.",
  },
}

// ── Gauge ─────────────────────────────────────────────────────────────────

function RiskGauge({ score, level }: { score: number; level: string }) {
  const colour = LEVEL_COLOUR[level] ?? "#94a3b8"
  const data   = [{ value: score }, { value: 100 - score }]
  return (
    <div className="relative h-[68px] w-[68px] shrink-0">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%" cy="50%"
          innerRadius="65%" outerRadius="100%"
          startAngle={180} endAngle={-180}
          data={data} barSize={8}
        >
          <RadialBar dataKey="value" cornerRadius={4} background={{ fill: "hsl(var(--muted))" }}>
            {data.map((_, i) => <Cell key={i} fill={i === 0 ? colour : "transparent"} />)}
          </RadialBar>
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[17px] font-bold leading-none" style={{ color: colour }}>{score}</span>
        <span className="text-[8px] text-muted-foreground mt-0.5">{LEVEL_LABEL_AR[level]}</span>
      </div>
    </div>
  )
}

// ── Confidence badge ───────────────────────────────────────────────────────

function ConfidenceBadge({ confidence }: { confidence: "high" | "medium" | "low" }) {
  const cfg = CONFIDENCE_CFG[confidence] ?? CONFIDENCE_CFG.low
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${cfg.ring}`}>
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${cfg.dot}`} />
      {cfg.label}
    </span>
  )
}

// ── Risk card ─────────────────────────────────────────────────────────────

function RiskCard({ risk, delay }: { risk: RiskScore; delay: number }) {
  const [open, setOpen] = useState(false)
  const colour  = LEVEL_COLOUR[risk.level] ?? "#94a3b8"
  const conf    = risk.confidence ?? "low"
  const confCfg = CONFIDENCE_CFG[conf]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      className="rounded-xl border border-border bg-card overflow-hidden"
    >
      {/* Header — always visible */}
      <button
        className="w-full flex items-center gap-3 p-4 text-right hover:bg-muted/30 transition-colors"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
      >
        <RiskGauge score={risk.score} level={risk.level} />

        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm text-foreground leading-snug">{risk.label_ar}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-semibold text-white"
              style={{ backgroundColor: colour }}
            >
              {LEVEL_LABEL_AR[risk.level]}
            </span>
            <ConfidenceBadge confidence={conf} />
            {risk.source !== "rules" && (
              <span className="rounded-full border border-violet-500/20 bg-violet-500/10 px-2 py-0.5 text-[10px] font-medium text-violet-500">
                ML
              </span>
            )}
          </div>
        </div>

        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-muted-foreground shrink-0"
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </button>

      {/* Expandable details */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-4 pb-4 pt-3 space-y-3">

              {/* Confidence note */}
              {conf === "low" && (
                <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/8 px-3 py-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                  <p className="text-xs leading-relaxed text-amber-700 dark:text-amber-300">{confCfg.note}</p>
                </div>
              )}
              {conf === "medium" && (
                <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2">
                  <Info className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
                  <p className="text-xs leading-relaxed text-muted-foreground">{confCfg.note}</p>
                </div>
              )}

              {/* Why this assessment */}
              {risk.factors.length > 0 && (
                <div>
                  <p className="flex items-center gap-1.5 text-xs font-semibold text-foreground mb-2">
                    <span className="h-3 w-1 rounded-full" style={{ backgroundColor: colour }} />
                    لماذا ظهر هذا التقييم؟
                  </p>
                  <ul className="space-y-1.5">
                    {risk.factors.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                        <span className="mt-[5px] h-1.5 w-1.5 rounded-full shrink-0" style={{ backgroundColor: colour }} />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendation */}
              {risk.recommendation && (
                <div className="rounded-lg border border-border bg-muted/40 px-3 py-2.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">التوصية</p>
                  <p className="text-xs leading-relaxed text-foreground">{risk.recommendation}</p>
                </div>
              )}

              {/* Disclaimer */}
              <p className="text-[10px] leading-relaxed text-muted-foreground/50">
                هذا التقييم مساعد وليس تشخيصاً طبياً — القرار النهائي دائماً لطبيبك.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Data quality bar ───────────────────────────────────────────────────────

function DataQualityBar({ featuresUsed }: { featuresUsed: { count: number; names: string[] } }) {
  const MAX_FEATURES = 18
  const pct     = Math.min(Math.round((featuresUsed.count / MAX_FEATURES) * 100), 100)
  const quality = pct >= 60 ? "high" : pct >= 30 ? "medium" : "low"
  const barColor = quality === "high" ? "#22c55e" : quality === "medium" ? "#f59e0b" : "#ef4444"
  const cfg     = CONFIDENCE_CFG[quality]

  return (
    <div className="rounded-lg border border-border bg-muted/20 px-3 py-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-[10px] font-medium text-muted-foreground">جودة البيانات المستخرجة</p>
        <span className={`text-[10px] font-bold ${cfg.ring.split(" ").find(c => c.startsWith("text-")) ?? ""}`}>
          {pct}%
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
          className="h-full rounded-full"
          style={{ backgroundColor: barColor }}
        />
      </div>
      <p className="mt-1 text-[10px] text-muted-foreground">
        تم استخراج {featuresUsed.count} قيمة طبية من أصل ~{MAX_FEATURES} قيمة ممكنة
      </p>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

export function RiskDashboard({ analysis }: { analysis: AnalysisResult }) {
  const [report,  setReport]  = useState<RiskReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)
  const [visible, setVisible] = useState(false)

  const fetchRisk = useCallback(() => {
    if (!analysis?.findings?.length) return
    setLoading(true)
    setError(null)
    fetch(`${BACKEND}/api/risk`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ findings: analysis.findings }),
    })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then((data: RiskReport) => setReport(data))
      .catch(() => setError("تعذّر تحميل مؤشرات الصحة"))
      .finally(() => setLoading(false))
  }, [analysis])

  useEffect(() => { fetchRisk() }, [fetchRisk])

  if (!analysis?.findings?.length) return null

  const significantRisks = (report?.risks ?? []).filter(r => r.score >= 20)
  const hasRisks         = significantRisks.length > 0
  const allClear         = !!report && !hasRisks && !loading

  return (
    <div className="mt-6">
      {/* Toggle */}
      <button
        onClick={() => setVisible(v => !v)}
        className="flex w-full items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium transition-colors hover:bg-muted/50"
      >
        <span className="flex items-center gap-2">
          {allClear
            ? <CheckCircle2 className="w-4 h-4 text-green-500" />
            : <ShieldAlert  className="w-4 h-4 text-amber-500" />
          }
          مؤشرات الصحة
          {report && (
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
              hasRisks
                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                : "bg-green-500/10 text-green-600 dark:text-green-400"
            }`}>
              {hasRisks ? `${significantRisks.length} تنبيه` : "لا تنبيهات"}
            </span>
          )}
        </span>
        <motion.div
          animate={{ rotate: visible ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-muted-foreground"
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {visible && (
          <motion.div
            key="panel"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-3">

              {/* Data quality */}
              {report?.features_used && (
                <DataQualityBar featuresUsed={report.features_used} />
              )}

              {/* Overall summary */}
              {report?.overall_ar && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`rounded-xl border px-4 py-3 text-sm leading-relaxed ${
                    hasRisks
                      ? "border-amber-500/20 bg-amber-500/5 text-foreground"
                      : "border-green-500/20 bg-green-500/5 text-foreground"
                  }`}
                >
                  {report.overall_ar}
                </motion.div>
              )}

              {/* Loading */}
              {loading && (
                <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" strokeLinecap="round" />
                  </svg>
                  جارٍ تحليل المؤشرات الصحية...
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="flex flex-col items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3">
                  <p className="text-sm text-destructive">{error}</p>
                  <button
                    onClick={fetchRisk}
                    className="rounded-lg bg-destructive/15 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/25 transition-colors"
                  >
                    إعادة المحاولة
                  </button>
                </div>
              )}

              {/* Risk cards sorted by score */}
              {(report?.risks ?? [])
                .slice()
                .sort((a, b) => b.score - a.score)
                .map((risk, i) => (
                  <RiskCard key={risk.condition} risk={risk} delay={i * 0.06} />
                ))}

              {/* All clear */}
              {allClear && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-xl border border-green-500/20 bg-green-500/5 px-4 py-5 text-center"
                >
                  <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-500" />
                  <p className="text-sm font-semibold text-green-700 dark:text-green-400 mb-1">
                    قيمك تبدو جيدة
                  </p>
                  <p className="text-xs text-muted-foreground">
                    لم يُرصد أي مؤشر خطر بارز بناءً على البيانات المتاحة.
                    <br />واصل التحاليل الدورية للاطمئنان.
                  </p>
                </motion.div>
              )}

              {/* Global disclaimer */}
              <p className="px-2 text-center text-[10px] leading-relaxed text-muted-foreground/50">
                هذه المؤشرات تقييم مساعد مبني على البيانات المستخرجة — وليست تشخيصاً طبياً نهائياً.
                دائماً استشر طبيبك المختص.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
