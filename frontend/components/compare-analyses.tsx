"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { AnalysisResult } from "@/app/page"

interface SavedAnalysis {
  id:         string
  summary:    string
  findings:   AnalysisResult["findings"]
  report:     AnalysisResult["report"]
  created_at: string
}

interface CompareAnalysesProps {
  a:       SavedAnalysis
  b:       SavedAnalysis
  onClose: () => void
}

function formatDate(d: string) {
  if (!d) return "—"
  return new Date(d).toLocaleDateString("ar-SA", { day: "numeric", month: "short", year: "numeric" })
}

const STATUS_CFG = {
  normal: { label: "طبيعي",  cls: "text-success bg-success/10",      dot: "bg-success"      },
  high:   { label: "مرتفع",  cls: "text-destructive bg-destructive/10", dot: "bg-destructive" },
  low:    { label: "منخفض",  cls: "text-warning bg-warning/10",       dot: "bg-warning"      },
} as const

function getStatusCfg(s: string) {
  return STATUS_CFG[s as keyof typeof STATUS_CFG] ?? STATUS_CFG.normal
}

function getTrend(rowA: AnalysisResult["findings"][0] | null, rowB: AnalysisResult["findings"][0] | null) {
  if (!rowA || !rowB) return null
  const vA = parseFloat(rowA.value)
  const vB = parseFloat(rowB.value)
  if (isNaN(vA) || isNaN(vB)) return null
  const improved = rowA.status !== "normal" && rowB.status === "normal"
  const worsened = rowA.status === "normal"  && rowB.status !== "normal"
  const diff    = vB - vA
  const deltaPct = vA !== 0 ? Math.abs((diff / vA) * 100) : 0
  if (Math.abs(diff) < 0.001) return { icon: "—", colorCls: "text-muted-foreground", direction: "stable" as const, deltaPct: 0 }
  return {
    icon:      diff > 0 ? "↑" : "↓",
    colorCls:  improved ? "text-success" : worsened ? "text-destructive" : "text-muted-foreground",
    direction: diff > 0 ? ("up" as const) : ("down" as const),
    deltaPct:  Math.round(deltaPct),
  }
}

function calcPct(value: string, range: string) {
  const nums = range?.match(/[\d.]+/g)
  if (!nums || nums.length < 2) return null
  const lo = parseFloat(nums[0]), hi = parseFloat(nums[1]), val = parseFloat(value)
  if (isNaN(val) || isNaN(lo) || isNaN(hi) || hi === lo) return null
  return Math.max(4, Math.min(96, ((val - lo) / (hi - lo)) * 100))
}

/* ─── Skeleton pieces ─── */

function Sk({ w = "100%", h = 16, rounded = "rounded-xl" }: { w?: string | number; h?: number; rounded?: string }) {
  return (
    <div
      className={`skeleton ${rounded} shrink-0`}
      style={{ width: w, height: h }}
    />
  )
}

function CompareSkeleton() {
  return (
    <motion.div
      key="skeleton"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.18 } }}
      transition={{ duration: 0.22 }}
      className="flex flex-col h-full"
    >
      {/* Header skeleton */}
      <div className="flex items-start justify-between px-6 py-5 border-b border-border shrink-0">
        <div className="space-y-2 flex-1 text-right">
          <Sk w="52%" h={20} rounded="rounded-lg" />
          <Sk w="36%" h={12} rounded="rounded-lg" />
        </div>
        <div className="skeleton rounded-xl w-9 h-9 shrink-0 ml-4" />
      </div>

      <div className="flex-1 overflow-hidden px-6 pt-5 pb-6 space-y-5">
        {/* Stat cards */}
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="rounded-2xl p-4 border border-border space-y-2 text-center">
              <Sk w="40%" h={28} rounded="rounded-lg" />
              <Sk w="60%" h={12} rounded="rounded-lg" />
            </div>
          ))}
        </div>

        {/* Column headers */}
        <div className="grid grid-cols-[1fr_100px_100px] sm:grid-cols-[1fr_160px_160px] gap-3">
          <div />
          {[0, 1].map(i => (
            <div key={i} className="rounded-2xl px-4 py-3 border border-border space-y-1.5">
              <Sk w="60%" h={10} rounded="rounded-md" />
              <Sk w="80%" h={14} rounded="rounded-md" />
              <Sk w="70%" h={10} rounded="rounded-md" />
            </div>
          ))}
        </div>

        {/* Table rows */}
        <div className="space-y-1.5">
          {[100, 85, 90, 75, 95, 80].map((w, i) => (
            <div key={i} className="grid grid-cols-[1fr_100px_100px] sm:grid-cols-[1fr_160px_160px] gap-3 items-center px-4 py-4 rounded-2xl bg-muted/20">
              <div className="space-y-1.5 text-right">
                <Sk w={`${w * 0.55}%`} h={14} rounded="rounded-lg" />
                <Sk w={`${w * 0.38}%`} h={10} rounded="rounded-lg" />
              </div>
              {[0, 1].map(j => (
                <div key={j} className="space-y-1.5 flex flex-col items-center">
                  <Sk w="50%" h={22} rounded="rounded-lg" />
                  <Sk w="60%" h={16} rounded="rounded-full" />
                  <Sk w="100%" h={6} rounded="rounded-full" />
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-border shrink-0 flex items-center justify-between">
        <Sk w={80} h={12} rounded="rounded-lg" />
        <Sk w={80} h={36} rounded="rounded-2xl" />
      </div>
    </motion.div>
  )
}

/* ─── Real content ─── */

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"

function CompareContent({
  a, b, onClose,
}: {
  a: SavedAnalysis
  b: SavedAnalysis
  onClose: () => void
}) {
  const [groqSummary, setGroqSummary]     = useState<string | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(true)

  const dateA = formatDate(a.created_at)
  const dateB = formatDate(b.created_at)

  useEffect(() => {
    setSummaryLoading(true)
    fetch(`${BACKEND}/api/compare/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        findings_a: a.findings ?? [],
        findings_b: b.findings ?? [],
        summary_a:  a.summary  ?? "",
        summary_b:  b.summary  ?? "",
        date_a:     dateA,
        date_b:     dateB,
      }),
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => setGroqSummary(d.summary ?? null))
      .catch(() => setGroqSummary(null))
      .finally(() => setSummaryLoading(false))
  }, [a.id, b.id])

  const mapA = Object.fromEntries((a.findings ?? []).map(f => [f.name, f]))
  const mapB = Object.fromEntries((b.findings ?? []).map(f => [f.name, f]))
  const allNames = [...new Set([...Object.keys(mapA), ...Object.keys(mapB)])]

  const rows = allNames.map(name => ({ name, a: mapA[name] ?? null, b: mapB[name] ?? null }))

  const improved = rows.filter(r => r.a?.status !== "normal" && r.b?.status === "normal")
  const worsened = rows.filter(r => r.a?.status === "normal"  && r.b?.status !== "normal")
  const stable   = rows.filter(r => r.a?.status === r.b?.status)

  const summaryStats = [
    { num: improved.length, label: "تحسّن",  icon: "↑", bg: "bg-success/8",      border: "border-success/20",      text: "text-success"      },
    { num: worsened.length, label: "تراجع",  icon: "!",  bg: "bg-destructive/8",  border: "border-destructive/20",  text: "text-destructive"  },
    { num: stable.length,   label: "مستقر",  icon: "→", bg: "bg-muted/60",        border: "border-border",           text: "text-muted-foreground" },
  ]

  const insights = [
    ...improved.map(r => ({
      type: "success" as const,
      icon: "↑",
      text: `تحسّن مستوى ${r.name} من ${r.a?.value ?? "—"} إلى ${r.b?.value ?? "—"} ${r.b?.unit ?? ""}`,
    })),
    ...worsened.map(r => ({
      type: "warning" as const,
      icon: "!",
      text: `تراجع مستوى ${r.name} — يُنصح بمراجعة الطبيب`,
    })),
  ]

  return (
    <motion.div
      key="content"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.15 } }}
      transition={{ duration: 0.28, ease: "easeOut" }}
      className="flex flex-col h-full"
    >
      {/* ── Header ── */}
      <div className="flex items-start justify-between px-6 py-5 border-b border-border shrink-0">
        <div className="text-right">
          <div className="flex items-center gap-2.5 flex-wrap mb-1">
            <h2 className="text-lg font-bold text-foreground">مقارنة التحاليل</h2>
            {worsened.length > 0 && (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-destructive/10 text-destructive font-semibold">
                {worsened.length} تحتاج متابعة
              </span>
            )}
            {improved.length > 0 && (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-success/10 text-success font-semibold">
                {improved.length} تحسّنت ✓
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">{dateA} مقابل {dateB}</p>
        </div>
        <button
          onClick={onClose}
          className="w-9 h-9 rounded-xl bg-muted flex items-center justify-center hover:bg-muted/70 transition-colors shrink-0 mt-0.5"
        >
          <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* ── Summary Stats ── */}
        <div className="px-6 pt-5 pb-4 grid grid-cols-3 gap-3">
          {summaryStats.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 + i * 0.06 }}
              className={`rounded-2xl p-4 border text-center ${s.bg} ${s.border}`}
            >
              <p className={`text-2xl font-bold mb-1 ${s.text}`}>{s.num}</p>
              <p className={`text-xs font-semibold ${s.text}`}>{s.label} {s.icon}</p>
            </motion.div>
          ))}
        </div>

        {/* ── Analysis Column Labels ── */}
        <div className="px-6 pb-4 grid grid-cols-[1fr_100px_100px] sm:grid-cols-[1fr_160px_160px] gap-3 items-end">
          <div />
          {[
            { label: "التحليل الأول",  date: dateA, summary: a.summary, accent: "border-primary/30 bg-primary/5" },
            { label: "التحليل الثاني", date: dateB, summary: b.summary, accent: "border-secondary/30 bg-secondary/5" },
          ].map((col, i) => (
            <div key={i} className={`rounded-2xl px-4 py-3 border text-center ${col.accent}`}>
              <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{col.label}</p>
              <p className="text-xs font-bold text-foreground mt-0.5">{col.date}</p>
              <p className="text-[10px] text-muted-foreground mt-1 line-clamp-1">{col.summary}</p>
            </div>
          ))}
        </div>

        {/* ── Comparison Rows ── */}
        <div className="px-6 pb-5 space-y-1.5">
          {rows.map((row, i) => {
            const cfgA  = row.a ? getStatusCfg(row.a.status) : null
            const cfgB  = row.b ? getStatusCfg(row.b.status) : null
            const trend = getTrend(row.a, row.b)
            const pctA  = row.a ? calcPct(row.a.value, row.a.range ?? "") : null
            const pctB  = row.b ? calcPct(row.b.value, row.b.range ?? "") : null
            const isWorsened = row.a?.status === "normal" && row.b?.status !== "normal"

            return (
              <motion.div
                key={row.name}
                initial={{ opacity: 0, x: 6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.04 }}
                className={`grid grid-cols-[1fr_100px_100px] sm:grid-cols-[1fr_160px_160px] gap-3 items-center px-4 py-4 rounded-2xl transition-colors duration-150 hover:bg-muted/40 ${
                  isWorsened ? "bg-destructive/5 border border-destructive/12" : ""
                }`}
              >
                {/* Test name */}
                <div className="text-right">
                  <p className="text-sm font-semibold text-foreground">{row.name}</p>
                  {(row.a?.unit || row.b?.unit) && (
                    <p className="text-[11px] text-muted-foreground mt-0.5">{row.a?.unit ?? row.b?.unit}</p>
                  )}
                  {(row.a?.range || row.b?.range) && (
                    <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                      طبيعي: {row.a?.range ?? row.b?.range}
                    </p>
                  )}
                </div>

                {/* Value A */}
                <div className="text-center">
                  {row.a ? (
                    <div className="space-y-1.5">
                      <p className="text-xl font-bold text-foreground">{row.a.value}</p>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full inline-block ${cfgA!.cls}`}>
                        {cfgA!.label}
                      </span>
                      {pctA !== null && (
                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${cfgA!.dot}`}
                            style={{ width: `${pctA}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground/30 text-sm">—</span>
                  )}
                </div>

                {/* Value B + trend + delta % */}
                <div className="text-center">
                  {row.b ? (
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-center gap-1.5">
                        <p className="text-xl font-bold text-foreground">{row.b.value}</p>
                        {trend && trend.direction !== "stable" && (
                          <span className={`text-sm font-bold ${trend.colorCls}`}>{trend.icon}</span>
                        )}
                      </div>
                      {trend && trend.direction !== "stable" && trend.deltaPct > 0 && (
                        <p className={`text-[10px] font-bold ${trend.colorCls}`}>
                          {trend.deltaPct}%
                        </p>
                      )}
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full inline-block ${cfgB!.cls}`}>
                        {cfgB!.label}
                      </span>
                      {pctB !== null && (
                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${cfgB!.dot}`}
                            style={{ width: `${pctB}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="text-muted-foreground/30 text-sm">—</span>
                  )}
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* ── Groq AI Summary ── */}
        <div className="px-6 pb-2">
          <div className="border-t border-border pt-5">
            <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-widest mb-3 text-right">
              ملخص ذكي مقارَن
            </p>
            {summaryLoading ? (
              <div className="space-y-2">
                <div className="skeleton h-3 rounded-lg w-full" />
                <div className="skeleton h-3 rounded-lg w-4/5 mr-auto" />
                <div className="skeleton h-3 rounded-lg w-3/5 mr-auto" />
              </div>
            ) : groqSummary ? (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-2xl bg-primary/5 border border-primary/15 text-right"
              >
                <p className="text-sm text-foreground leading-relaxed">{groqSummary}</p>
              </motion.div>
            ) : null}
          </div>
        </div>

        {/* ── Insights Section ── */}
        {insights.length > 0 && (
          <div className="px-6 pb-6">
            <div className="border-t border-border pt-5">
              <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-widest mb-4 text-right">
                تفاصيل التغيرات
              </p>
              <div className="space-y-2.5">
                {insights.map((ins, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + i * 0.07 }}
                    className={`flex items-center gap-3 p-3.5 rounded-2xl ${
                      ins.type === "success"
                        ? "bg-success/8 border border-success/15"
                        : "bg-warning/8 border border-warning/15"
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                      ins.type === "success" ? "bg-success/15" : "bg-warning/15"
                    }`}>
                      <span className={`text-sm font-bold ${
                        ins.type === "success" ? "text-success" : "text-warning"
                      }`}>
                        {ins.icon}
                      </span>
                    </div>
                    <p className="text-sm text-foreground text-right flex-1 leading-relaxed">{ins.text}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div className="px-6 py-4 border-t border-border shrink-0 flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {rows.length} فحص مقارَن
        </p>
        <button
          onClick={onClose}
          className="px-5 py-2.5 rounded-2xl bg-muted text-muted-foreground text-sm font-medium hover:bg-muted/70 transition-colors"
        >
          إغلاق
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Main export ─── */

export function CompareAnalyses({ a, b, onClose }: CompareAnalysesProps) {
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const t = setTimeout(() => setIsLoading(false), 700)
    return () => clearTimeout(t)
  }, [])

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6"
        style={{ background: "oklch(0 0 0 / 0.58)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)" }}
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 24, scale: 0.96 }}
          transition={{ type: "spring", damping: 28, stiffness: 260 }}
          onClick={e => e.stopPropagation()}
          className="w-full max-w-3xl max-h-[90vh] flex flex-col rounded-3xl overflow-hidden bg-card"
          style={{ boxShadow: "0 40px 96px -16px oklch(0 0 0 / 0.32), 0 0 0 1px oklch(0 0 0 / 0.07)" }}
        >
          <AnimatePresence mode="wait">
            {isLoading
              ? <CompareSkeleton key="skeleton" />
              : <CompareContent key="content" a={a} b={b} onClose={onClose} />
            }
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
