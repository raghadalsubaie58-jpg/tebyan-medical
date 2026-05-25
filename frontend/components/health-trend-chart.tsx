"use client"

import { useState, useMemo } from "react"
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceArea, ResponsiveContainer,
} from "recharts"

interface Finding {
  name: string
  value: string
  unit: string
  range: string
  status: "normal" | "high" | "low"
}
interface Analysis {
  id: string
  created_at: string
  findings: Finding[]
}

interface TrendPoint { dateLabel: string; value: number; status: "normal" | "high" | "low" }
interface TrendSeries {
  key: string
  testName: string
  unit: string
  points: TrendPoint[]
  rangeMin: number | null
  rangeMax: number | null
  alerts: string[]
}

function normKey(n: string) {
  return n.toLowerCase().trim().replace(/[()،,]/g, "").replace(/\s+/g, " ")
}

function buildSeries(analyses: Analysis[]): TrendSeries[] {
  const sorted = [...analyses].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
  const map = new Map<string, { testName: string; unit: string; points: TrendPoint[]; rangePairs: [number, number][] }>()

  for (const a of sorted) {
    const label = new Date(a.created_at).toLocaleDateString("ar-SA", { day: "numeric", month: "short" })
    for (const f of a.findings ?? []) {
      const val = parseFloat(f.value)
      if (isNaN(val)) continue
      const key = normKey(f.name)
      if (!map.has(key)) map.set(key, { testName: f.name, unit: f.unit ?? "", points: [], rangePairs: [] })
      const entry = map.get(key)!
      entry.points.push({ dateLabel: label, value: val, status: f.status })
      const nums = (f.range ?? "").match(/[\d.]+/g)
      if (nums && nums.length >= 2) entry.rangePairs.push([parseFloat(nums[0]), parseFloat(nums[1])])
    }
  }

  const series: TrendSeries[] = []
  for (const [key, entry] of map) {
    if (entry.points.length < 2) continue

    const lows  = entry.rangePairs.map(p => p[0])
    const highs = entry.rangePairs.map(p => p[1])
    const rangeMin = lows.length  ? Math.min(...lows)  : null
    const rangeMax = highs.length ? Math.max(...highs) : null

    const alerts: string[] = []
    const n = entry.points.length
    const abnormal = entry.points.filter(p => p.status !== "normal")

    if (abnormal.length === n) {
      const dir = entry.points[0].status === "high" ? "مرتفعة" : "منخفضة"
      alerts.push(`${entry.testName} ${dir} في جميع التحاليل المسجلة (${n} قراءات)`)
    } else if (abnormal.length >= 2) {
      alerts.push(`${entry.testName}: ${abnormal.length}/${n} قراءات خارج النطاق الطبيعي`)
    }

    if (n >= 3) {
      const first = entry.points[0].value
      const last  = entry.points[n - 1].value
      const pctChange = Math.abs((last - first) / (first || 1)) * 100
      if (pctChange > 15) {
        const lastStatus = entry.points[n - 1].status
        if (last > first && lastStatus === "high")
          alerts.push(`${entry.testName} في ارتفاع مستمر (↑ ${pctChange.toFixed(0)}%)`)
        else if (last < first && lastStatus === "low")
          alerts.push(`${entry.testName} في انخفاض مستمر (↓ ${pctChange.toFixed(0)}%)`)
        else if (entry.points[0].status !== "normal" && lastStatus === "normal")
          alerts.push(`${entry.testName} عاد للنطاق الطبيعي — تحسن ملحوظ`)
      }
    }

    series.push({ key, testName: entry.testName, unit: entry.unit, points: entry.points, rangeMin, rangeMax, alerts })
  }

  series.sort((a, b) => b.alerts.length - a.alerts.length || b.points.length - a.points.length)
  return series.slice(0, 10)
}

const DOT_COLOR: Record<string, string> = {
  normal: "var(--color-success, #22c55e)",
  high:   "var(--color-destructive, #ef4444)",
  low:    "var(--color-warning, #f59e0b)",
}

function CustomDot(props: { cx?: number; cy?: number; payload?: TrendPoint }) {
  const { cx = 0, cy = 0, payload } = props
  const fill = DOT_COLOR[payload?.status ?? "normal"]
  return <circle cx={cx} cy={cy} r={5} fill={fill} stroke="var(--background)" strokeWidth={2} />
}

export function HealthTrendChart({ analyses }: { analyses: Analysis[] }) {
  const series = useMemo(() => buildSeries(analyses), [analyses])
  const [activeKey, setActiveKey] = useState<string>(() => series[0]?.key ?? "")

  if (series.length === 0) return null

  const active = series.find(s => s.key === activeKey) ?? series[0]
  const allAlerts = series.flatMap(s => s.alerts)

  const yDomain = (() => {
    const vals = active.points.map(p => p.value)
    const lo = active.rangeMin != null ? Math.min(active.rangeMin, ...vals) : Math.min(...vals)
    const hi = active.rangeMax != null ? Math.max(active.rangeMax, ...vals) : Math.max(...vals)
    const pad = (hi - lo) * 0.15 || 1
    return [Math.max(0, lo - pad), hi + pad]
  })()

  return (
    <div className="mt-6 space-y-4" dir="rtl">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse shrink-0" />
        <h3 className="text-sm font-semibold text-foreground">تتبع المؤشرات الصحية</h3>
      </div>

      {/* Smart Alerts */}
      {allAlerts.length > 0 && (
        <div className="space-y-2">
          {allAlerts.slice(0, 3).map((alert, i) => (
            <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-xl bg-warning/10 border border-warning/20">
              <span className="text-warning mt-0.5 shrink-0">⚠</span>
              <p className="text-xs text-foreground/80 leading-relaxed">{alert}</p>
            </div>
          ))}
        </div>
      )}

      {/* Test selector */}
      {series.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {series.map(s => (
            <button
              key={s.key}
              onClick={() => setActiveKey(s.key)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                activeKey === s.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/70"
              }`}
            >
              {s.testName}
              {s.alerts.length > 0 && <span className="mr-1 text-warning">•</span>}
            </button>
          ))}
        </div>
      )}

      {/* Chart */}
      <div className="rounded-2xl glass border border-border/50 p-4">
        <p className="text-xs text-muted-foreground mb-3 text-left">
          {active.testName} {active.unit ? `(${active.unit})` : ""}
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={active.points} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
            <XAxis dataKey="dateLabel" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
            <YAxis domain={yDomain} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} width={40} />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: "12px",
                fontSize: "12px",
                color: "var(--foreground)",
              }}
              formatter={(v: number) => [`${v} ${active.unit}`, active.testName]}
            />
            {active.rangeMin != null && active.rangeMax != null && (
              <ReferenceArea
                y1={active.rangeMin} y2={active.rangeMax}
                fill="var(--color-success, #22c55e)" fillOpacity={0.08}
                stroke="var(--color-success, #22c55e)" strokeOpacity={0.3} strokeDasharray="4 4"
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--primary)"
              strokeWidth={2}
              dot={<CustomDot />}
              activeDot={{ r: 7 }}
            />
          </LineChart>
        </ResponsiveContainer>
        {active.rangeMin != null && active.rangeMax != null && (
          <p className="text-[10px] text-muted-foreground mt-2 text-left">
            النطاق الطبيعي: {active.rangeMin} – {active.rangeMax} {active.unit}
            <span className="mr-2 text-success">■ منطقة طبيعية</span>
          </p>
        )}
      </div>
    </div>
  )
}
