"use client"

import { motion, AnimatePresence } from "framer-motion"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts"
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
  return new Date(d).toLocaleDateString("ar-SA", { day: "numeric", month: "short", year: "numeric" })
}

function buildChartData(a: SavedAnalysis, b: SavedAnalysis) {
  const mapA = Object.fromEntries((a.findings ?? []).map(f => [f.name, f]))
  const mapB = Object.fromEntries((b.findings ?? []).map(f => [f.name, f]))
  const names = [...new Set([...Object.keys(mapA), ...Object.keys(mapB)])]

  return names
    .filter(n => {
      const va = parseFloat(mapA[n]?.value ?? "")
      const vb = parseFloat(mapB[n]?.value ?? "")
      return !isNaN(va) || !isNaN(vb)
    })
    .map(n => {
      const fa = mapA[n]
      const fb = mapB[n]
      const va = parseFloat(fa?.value ?? "NaN")
      const vb = parseFloat(fb?.value ?? "NaN")
      return {
        name:   n.length > 14 ? n.slice(0, 13) + "…" : n,
        fullName: n,
        [formatDate(a.created_at)]: isNaN(va) ? null : va,
        [formatDate(b.created_at)]: isNaN(vb) ? null : vb,
        statusA: fa?.status ?? "normal",
        statusB: fb?.status ?? "normal",
        unit:    fa?.unit ?? fb?.unit ?? "",
      }
    })
}

const statusColor = { normal: "#22c55e", high: "#ef4444", low: "#eab308" }

export function CompareAnalyses({ a, b, onClose }: CompareAnalysesProps) {
  const chartData = buildChartData(a, b)
  const dateA = formatDate(a.created_at)
  const dateB = formatDate(b.created_at)

  const improved = chartData.filter(d => {
    const vA = d[dateA] as number | null
    const vB = d[dateB] as number | null
    return vA != null && vB != null && d.statusA !== "normal" && d.statusB === "normal"
  })
  const worsened = chartData.filter(d => {
    const vA = d[dateA] as number | null
    const vB = d[dateB] as number | null
    return vA != null && vB != null && d.statusA === "normal" && d.statusB !== "normal"
  })

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.93, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.93, y: 20 }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          onClick={e => e.stopPropagation()}
          className="glass-strong rounded-3xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border/30">
            <div>
              <h2 className="text-xl font-bold text-foreground">مقارنة التحاليل</h2>
            </div>
            <button onClick={onClose} className="w-9 h-9 rounded-xl bg-muted/50 flex items-center justify-center hover:bg-muted transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-4">
              {[{ analysis: a, date: dateA, label: "التحليل الأول" }, { analysis: b, date: dateB, label: "التحليل الثاني" }].map(({ analysis, date, label }) => {
                const abn = analysis.findings?.filter(f => f.status !== "normal").length ?? 0
                return (
                  <div key={analysis.id} className="rounded-2xl border border-border/30 bg-background/50 p-4">
                    <p className="text-xs text-muted-foreground mb-1">{label}</p>
                    <p className="text-sm font-semibold text-foreground">{date}</p>
                    <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{analysis.summary}</p>
                    <div className="flex gap-2 mt-2 flex-wrap">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-muted/50 text-muted-foreground">{analysis.findings?.length ?? 0} فحص</span>
                      {abn > 0 && <span className="text-xs px-2 py-0.5 rounded-full bg-destructive/10 text-destructive">{abn} غير طبيعي</span>}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Trend summary */}
            {(improved.length > 0 || worsened.length > 0) && (
              <div className="grid grid-cols-2 gap-3">
                {improved.length > 0 && (
                  <div className="rounded-2xl bg-success/10 border border-success/20 p-3">
                    <p className="text-xs font-medium text-success mb-1">تحسّنت ({improved.length})</p>
                    {improved.map(d => <p key={d.fullName} className="text-xs text-success/80">{d.fullName}</p>)}
                  </div>
                )}
                {worsened.length > 0 && (
                  <div className="rounded-2xl bg-destructive/10 border border-destructive/20 p-3">
                    <p className="text-xs font-medium text-destructive mb-1">تراجعت ({worsened.length})</p>
                    {worsened.map(d => <p key={d.fullName} className="text-xs text-destructive/80">{d.fullName}</p>)}
                  </div>
                )}
              </div>
            )}

            {/* Chart */}
            {chartData.length > 0 ? (
              <div>
                <p className="text-sm font-medium text-foreground mb-3">مقارنة القيم</p>
                <div className="rounded-2xl bg-background/60 border border-border/20 p-4" style={{ direction: "ltr" }}>
                  <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 40)}>
                    <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(0,0,0,0.06)" />
                      <XAxis type="number" tick={{ fontSize: 11 }} />
                      <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 10 }} />
                      <Tooltip
                        formatter={(v, name) => [v, name]}
                        contentStyle={{ borderRadius: 12, border: "1px solid rgba(0,0,0,0.08)", fontSize: 12 }}
                      />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Bar dataKey={dateA} fill="#B8F3E4" radius={[0, 4, 4, 0]} maxBarSize={18} />
                      <Bar dataKey={dateB} fill="#7dd3c8" radius={[0, 4, 4, 0]} maxBarSize={18} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : (
              <p className="text-center text-sm text-muted-foreground py-8">لا توجد قيم رقمية قابلة للمقارنة</p>
            )}

            {/* Table */}
            {chartData.length > 0 && (
              <div>
                <p className="text-sm font-medium text-foreground mb-3">جدول المقارنة</p>
                <div className="rounded-2xl border border-border/30 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted/40">
                        <th className="text-right px-4 py-2.5 font-medium text-muted-foreground">الفحص</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground text-center">{dateA}</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground text-center">{dateB}</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground text-center">التغيير</th>
                      </tr>
                    </thead>
                    <tbody>
                      {chartData.map((d, i) => {
                        const vA = d[dateA] as number | null
                        const vB = d[dateB] as number | null
                        const diff = vA != null && vB != null ? (vB - vA).toFixed(2) : null
                        const pct  = vA != null && vB != null && vA !== 0
                          ? ((vB - vA) / Math.abs(vA) * 100).toFixed(1)
                          : null
                        return (
                          <tr key={d.fullName} className={i % 2 === 0 ? "bg-background/30" : "bg-muted/10"}>
                            <td className="px-4 py-2.5 font-medium text-foreground">{d.fullName}</td>
                            <td className="px-4 py-2.5 text-center">
                              <span className={`inline-flex items-center gap-1 ${d.statusA !== "normal" ? "text-destructive" : "text-success"}`}>
                                <span className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor[d.statusA as keyof typeof statusColor] ?? "#94a3b8" }} />
                                {vA ?? "—"} {d.unit}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-center">
                              <span className={`inline-flex items-center gap-1 ${d.statusB !== "normal" ? "text-destructive" : "text-success"}`}>
                                <span className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor[d.statusB as keyof typeof statusColor] ?? "#94a3b8" }} />
                                {vB ?? "—"} {d.unit}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-center text-xs">
                              {diff != null ? (
                                <span className={parseFloat(diff) > 0 ? "text-destructive" : parseFloat(diff) < 0 ? "text-success" : "text-muted-foreground"}>
                                  {parseFloat(diff) > 0 ? "+" : ""}{diff} ({pct}%)
                                </span>
                              ) : "—"}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
