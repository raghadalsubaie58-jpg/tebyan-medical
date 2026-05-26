"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  RadialBarChart, RadialBar, Cell,
  ResponsiveContainer, Tooltip,
} from "recharts"
import type { AnalysisResult } from "@/app/page"

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"

// ── Types ─────────────────────────────────────────────────────────────────

interface RiskScore {
  condition:      string
  score:          number       // 0–100
  level:          "low" | "moderate" | "high" | "critical"
  confidence:     number       // 0–1
  label_ar:       string
  factors:        string[]
  recommendation: string
  source:         "rule" | "ml"
}

interface RiskReport {
  risks:          RiskScore[]
  top_risk:       RiskScore | null
  overall_ar:     string
  features_used:  number
}

// ── Level colours ─────────────────────────────────────────────────────────

const LEVEL_COLOUR: Record<string, string> = {
  low:      "#22c55e",   // green-500
  moderate: "#f59e0b",   // amber-500
  high:     "#ef4444",   // red-500
  critical: "#7c3aed",   // violet-600
}

const LEVEL_LABEL_AR: Record<string, string> = {
  low:      "منخفض",
  moderate: "متوسط",
  high:     "مرتفع",
  critical: "حرج",
}

// ── Sub-components ────────────────────────────────────────────────────────

function RiskGauge({ score, level }: { score: number; level: string }) {
  const colour = LEVEL_COLOUR[level] ?? "#94a3b8"
  const data = [{ name: "risk", value: score }, { name: "rest", value: 100 - score }]

  return (
    <div className="relative h-28 w-28">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%" cy="50%"
          innerRadius="70%" outerRadius="100%"
          startAngle={180} endAngle={-180}
          data={data}
          barSize={10}
        >
          <RadialBar dataKey="value" cornerRadius={5} background={{ fill: "#1e293b" }}>
            {data.map((_, i) => (
              <Cell key={i} fill={i === 0 ? colour : "transparent"} />
            ))}
          </RadialBar>
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold" style={{ color: colour }}>{score}</span>
        <span className="text-[10px] text-muted-foreground">{LEVEL_LABEL_AR[level]}</span>
      </div>
    </div>
  )
}


function RiskCard({ risk, delay }: { risk: RiskScore; delay: number }) {
  const [open, setOpen] = useState(false)
  const colour = LEVEL_COLOUR[risk.level] ?? "#94a3b8"

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      className="rounded-xl border border-border bg-card p-4 cursor-pointer select-none"
      onClick={() => setOpen((v) => !v)}
    >
      <div className="flex items-center gap-4">
        <RiskGauge score={risk.score} level={risk.level} />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm">{risk.label_ar}</p>
          <div className="mt-1 flex items-center gap-2">
            <span
              className="rounded-full px-2 py-0.5 text-[11px] font-medium text-white"
              style={{ backgroundColor: colour }}
            >
              {LEVEL_LABEL_AR[risk.level]}
            </span>
            <span className="text-xs text-muted-foreground">
              ثقة {Math.round(risk.confidence * 100)}%
            </span>
            {risk.source === "ml" && (
              <span className="rounded-full bg-violet-500/20 px-2 py-0.5 text-[10px] text-violet-400">
                ML
              </span>
            )}
          </div>
        </div>
        <span className="text-muted-foreground text-xs">{open ? "▲" : "▼"}</span>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="details"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-2 border-t border-border pt-3">
              {risk.factors.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">العوامل:</p>
                  <ul className="space-y-0.5">
                    {risk.factors.map((f, i) => (
                      <li key={i} className="text-xs text-foreground/80 flex gap-1">
                        <span className="mt-0.5 shrink-0" style={{ color: colour }}>•</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {risk.recommendation && (
                <div className="rounded-lg bg-muted p-2 text-xs leading-relaxed">
                  {risk.recommendation}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}


// ── Main component ────────────────────────────────────────────────────────

interface RiskDashboardProps {
  analysis: AnalysisResult
}

export function RiskDashboard({ analysis }: RiskDashboardProps) {
  const [report, setReport]     = useState<RiskReport | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [visible, setVisible]   = useState(false)

  useEffect(() => {
    if (!analysis?.findings?.length) return

    setLoading(true)
    setError(null)

    fetch(`${BACKEND}/api/risk`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ findings: analysis.findings }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: RiskReport) => setReport(data))
      .catch(() => setError("تعذّر تحميل تقرير المخاطر"))
      .finally(() => setLoading(false))
  }, [analysis])

  // Show panel only when there's data or loading
  if (!analysis?.findings?.length) return null

  const significantRisks = (report?.risks ?? []).filter((r) => r.score >= 20)

  return (
    <div className="mt-6">
      {/* Toggle button */}
      <button
        onClick={() => setVisible((v) => !v)}
        className="flex w-full items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium transition-colors hover:bg-muted/50"
      >
        <span className="flex items-center gap-2">
          <span className="text-base">⚠️</span>
          تقييم مخاطر الأمراض
          {report && (
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
              {significantRisks.length} مؤشر
            </span>
          )}
        </span>
        <span className="text-muted-foreground">{visible ? "▲" : "▼"}</span>
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
              {/* Overall summary */}
              {report?.overall_ar && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm leading-relaxed"
                >
                  {report.overall_ar}
                </motion.div>
              )}

              {loading && (
                <div className="flex items-center justify-center py-8 text-muted-foreground text-sm gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" strokeLinecap="round" />
                  </svg>
                  جاري التحليل...
                </div>
              )}

              {error && (
                <div className="flex flex-col items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3">
                  <p className="text-sm text-destructive">{error}</p>
                  <button
                    onClick={() => {
                      setError(null)
                      setLoading(true)
                      fetch(`${BACKEND}/api/risk`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ findings: analysis.findings }),
                      })
                        .then((r) => { if (!r.ok) throw new Error(); return r.json() })
                        .then((data: RiskReport) => setReport(data))
                        .catch(() => setError("تعذّر تحميل تقرير المخاطر"))
                        .finally(() => setLoading(false))
                    }}
                    className="text-xs px-3 py-1.5 rounded-lg bg-destructive/15 text-destructive hover:bg-destructive/25 transition-colors font-medium"
                  >
                    إعادة المحاولة
                  </button>
                </div>
              )}

              {/* Risk cards (sorted by score desc) */}
              {(report?.risks ?? [])
                .slice()
                .sort((a, b) => b.score - a.score)
                .map((risk, i) => (
                  <RiskCard key={risk.condition} risk={risk} delay={i * 0.06} />
                ))}

              {report && significantRisks.length === 0 && !loading && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-xl border border-green-500/20 bg-green-500/10 px-4 py-3 text-sm text-green-600 dark:text-green-400"
                >
                  ✅ لا توجد مؤشرات خطر بارزة بناءً على نتائج هذا التحليل
                </motion.p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
