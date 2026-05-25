"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { AnalysisResult } from "@/app/page"
import { HealthTrendChart } from "./health-trend-chart"
import { apiGet, apiPost } from "@/lib/api"

interface SavedAnalysis {
  id:         string
  summary:    string
  findings:   AnalysisResult["findings"]
  report:     AnalysisResult["report"]
  created_at: string
}

interface AnalysisHistoryProps {
  sessionId?:      string
  refreshTrigger?: number
  onSelect:        (a: SavedAnalysis) => void
  onCompare:       (a: SavedAnalysis, b: SavedAnalysis) => void
  mockData?:       SavedAnalysis[]
  inline?:         boolean
}

function formatDate(s: string) {
  if (!s) return "—"
  return new Date(s).toLocaleDateString("ar-SA", { day: "numeric", month: "long", year: "numeric" })
}
function formatDateShort(s: string) {
  if (!s) return "—"
  return new Date(s).toLocaleDateString("ar-SA", { day: "numeric", month: "short" })
}
function calcPct(value: string, range: string) {
  const nums = range?.match(/[\d.]+/g)
  if (!nums || nums.length < 2) return null
  const lo = parseFloat(nums[0]), hi = parseFloat(nums[1]), val = parseFloat(value)
  if (isNaN(val) || isNaN(lo) || isNaN(hi) || hi === lo) return null
  return Math.max(4, Math.min(96, ((val - lo) / (hi - lo)) * 100))
}

const STATUS = {
  high:   { label: "مرتفع", textCls: "text-destructive", bgCls: "bg-destructive/10", barCls: "bg-destructive" },
  low:    { label: "منخفض", textCls: "text-warning",     bgCls: "bg-warning/10",     barCls: "bg-warning"     },
  normal: { label: "طبيعي", textCls: "text-success",     bgCls: "bg-success/10",     barCls: "bg-success"     },
} as const
const getS = (s: string) => STATUS[s as keyof typeof STATUS] ?? STATUS.normal

function counts(a: SavedAnalysis) {
  const f = a.findings ?? []
  return {
    total:  f.length,
    high:   f.filter(x => x.status === "high").length,
    low:    f.filter(x => x.status === "low").length,
    normal: f.filter(x => x.status === "normal").length,
  }
}

/* ─── Icons ─── */
function ScalesIcon({ className = "w-3.5 h-3.5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
    </svg>
  )
}
function ChevronIcon({ className = "w-3.5 h-3.5" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  )
}

/* ─────────────────────────────────────────────
   Compare Hint
───────────────────────────────────────────── */
function CompareHint() {
  return (
    <div className="flex justify-center">
      <div className="inline-flex items-center gap-3 px-5 py-3 rounded-full glass border border-primary/20">
        <div className="w-7 h-7 rounded-full bg-primary/12 flex items-center justify-center shrink-0">
          <ScalesIcon className="w-3.5 h-3.5 text-primary" />
        </div>
        <p className="text-sm text-muted-foreground whitespace-nowrap">
          اضغط <span className="text-foreground font-medium">«قارن»</span> على أي تحليلين لمتابعة تغيّراتك الصحية
        </p>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────
   Floating Compare Bar
───────────────────────────────────────────── */
function FloatingCompareBar({
  selected, onCompare, onCancel, fixed = false,
}: {
  selected:  SavedAnalysis[]
  onCompare: () => void
  onCancel:  () => void
  fixed?:    boolean
}) {
  return (
    <motion.div
      initial={{ y: "110%", opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: "110%", opacity: 0 }}
      transition={{ type: "spring", damping: 26, stiffness: 300 }}
      className={`p-3 z-10 ${fixed ? "fixed bottom-0 left-0 right-0" : "absolute bottom-0 left-0 right-0"}`}
    >
      <div
        className="glass-strong rounded-2xl border border-border/50 overflow-hidden"
        style={{ boxShadow: "0 -8px 40px oklch(0 0 0 / 0.14), 0 0 0 1px oklch(0 0 0 / 0.05)" }}
      >
        {selected.length === 1 ? (
          <div className="px-4 py-3 flex items-center justify-between gap-3">
            <button onClick={onCancel} className="text-xs text-muted-foreground/60 hover:text-muted-foreground transition-colors shrink-0">
              إلغاء
            </button>
            <div className="text-right">
              <div className="flex items-center gap-1.5 justify-end mb-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                <p className="text-xs font-bold text-foreground">تم تحديد تحليل واحد</p>
              </div>
              <p className="text-[11px] text-muted-foreground">حدد تحليلاً ثانياً لبدء المقارنة</p>
            </div>
          </div>
        ) : (
          <div className="px-4 pt-3 pb-3 space-y-3">
            <div className="space-y-2 text-right">
              {selected.map((s, i) => (
                <motion.div
                  key={s.id}
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.07 }}
                  className="flex items-center gap-2"
                >
                  <div className="w-4 h-4 rounded-full bg-primary text-primary-foreground text-[9px] font-bold flex items-center justify-center shrink-0">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground font-medium line-clamp-1">{s.summary}</p>
                    <p className="text-[10px] text-muted-foreground">{formatDateShort(s.created_at)}</p>
                  </div>
                </motion.div>
              ))}
            </div>
            <div className="h-px bg-border/50" />
            <div className="flex gap-2">
              <button
                onClick={onCancel}
                className="px-3 py-2 rounded-xl text-xs text-muted-foreground hover:bg-muted/50 transition-colors border border-border"
              >
                إلغاء
              </button>
              <motion.button
                whileTap={{ scale: 0.97 }}
                onClick={onCompare}
                className="flex-1 py-2 rounded-xl text-xs font-bold gradient-primary text-primary-foreground shadow-glow-primary hover:opacity-90 transition-opacity flex items-center justify-center gap-1.5"
              >
                <ScalesIcon className="w-3.5 h-3.5" />
                قارن الآن
              </motion.button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

/* ─────────────────────────────────────────────
   Inline Detail Panel
───────────────────────────────────────────── */
function InlineDetail({
  item, onUse,
}: {
  item: SavedAnalysis
  onUse: (a: SavedAnalysis) => void
}) {
  const c = counts(item)

  return (
    <div className="border-t border-border/40 bg-muted/15">
      <div className="px-6 pt-5 pb-5 space-y-4">

        {/* Header mini */}
        <div className="flex items-center justify-between text-right">
          <div className="flex gap-1.5">
            {c.high > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-destructive/10 text-destructive font-semibold">
                {c.high} مرتفع
              </span>
            )}
            {c.low > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-warning/10 text-warning font-semibold">
                {c.low} منخفض
              </span>
            )}
            {c.high === 0 && c.low === 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-success/10 text-success font-semibold">
                كل القيم طبيعية ✓
              </span>
            )}
          </div>
          <p className="text-[11px] text-muted-foreground font-medium">{formatDate(item.created_at)}</p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { num: c.normal, label: "طبيعي", bg: "bg-success/8 border-success/20",         text: "text-success"     },
            { num: c.high,   label: "مرتفع", bg: "bg-destructive/8 border-destructive/20", text: "text-destructive" },
            { num: c.low,    label: "منخفض", bg: "bg-warning/8 border-warning/20",         text: "text-warning"     },
          ].map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.88 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.04 + i * 0.05, duration: 0.2 }}
              className={`rounded-2xl border text-center py-4 ${s.bg}`}
            >
              <p className={`text-2xl font-bold ${s.text}`}>{s.num}</p>
              <p className={`text-xs font-semibold ${s.text} mt-0.5`}>{s.label}</p>
            </motion.div>
          ))}
        </div>

        {/* Summary */}
        {item.summary && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.2 }}
            className="rounded-2xl bg-card border border-border/50 px-5 py-4 text-right"
          >
            <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-widest mb-2">الملخص</p>
            <p className="text-sm text-foreground leading-relaxed">{item.summary}</p>
          </motion.div>
        )}

        {/* Mini-cards grid */}
        {item.findings && item.findings.length > 0 && (
          <div className="grid grid-cols-2 gap-2.5">
            {item.findings.map((f, i) => {
              const s   = getS(f.status)
              const pct = calcPct(f.value, f.range ?? "")
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.04, duration: 0.18 }}
                  className="rounded-2xl border border-border/50 overflow-hidden bg-card"
                  style={{
                    borderRightWidth: "3px",
                    borderRightColor: `var(--${
                      f.status === "high" ? "destructive" :
                      f.status === "low"  ? "warning"     : "success"
                    })`,
                  }}
                >
                  <div className="px-4 py-3.5">
                    <div className="flex items-start justify-between gap-1 mb-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${s.bgCls} ${s.textCls}`}>
                        {s.label}
                      </span>
                      <p className="text-xs font-semibold text-foreground text-right leading-snug">{f.name}</p>
                    </div>
                    <div className="flex items-baseline gap-1 justify-end mb-2">
                      <span className={`text-base font-bold ${s.textCls}`}>{f.value}</span>
                      {f.unit && <span className="text-xs text-muted-foreground">{f.unit}</span>}
                    </div>
                    {pct !== null && (
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.7, delay: 0.15 + i * 0.04, ease: "easeOut" }}
                          className={`h-full rounded-full ${s.barCls}`}
                        />
                      </div>
                    )}
                    {f.range && (
                      <p className="text-[10px] text-muted-foreground/55 mt-1.5 text-right">طبيعي: {f.range}</p>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}

        {(!item.findings || item.findings.length === 0) && (
          <p className="text-xs text-muted-foreground text-center py-4">لا توجد بيانات فحوصات</p>
        )}

        {/* Use button */}
        <motion.button
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onUse(item)}
          className="w-full py-4 rounded-2xl text-sm font-bold gradient-primary text-primary-foreground shadow-glow-primary hover:opacity-90 transition-opacity"
        >
          استخدم هذا التحليل
        </motion.button>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────
   Shared Card List (used in both inline & drawer)
───────────────────────────────────────────── */
function AnalysisCardList({
  analyses,
  loading,
  selected,
  expandedId,
  cardRefs,
  listRef,
  toggleExpand,
  toggleSelect,
  handleUse,
  containerClassName = "space-y-2",
}: {
  analyses:           SavedAnalysis[]
  loading:            boolean
  selected:           SavedAnalysis[]
  expandedId:         string | null
  cardRefs:           React.RefObject<Map<string, HTMLDivElement>>
  listRef:            React.RefObject<HTMLDivElement | null>
  toggleExpand:       (id: string) => void
  toggleSelect:       (a: SavedAnalysis) => void
  handleUse:          (a: SavedAnalysis) => void
  containerClassName?: string
}) {
  return (
    <div
      ref={listRef}
      className={containerClassName}
      style={{
        paddingBottom: selected.length > 0 ? "148px" : "0px",
        transition: "padding-bottom 0.3s cubic-bezier(0.22, 1, 0.36, 1)",
      }}
    >
      {loading && (
        <div className="flex justify-center py-16">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
            className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full"
          />
        </div>
      )}

      {!loading && analyses.length === 0 && (
        <div className="col-span-full text-center py-14">
          <p className="text-sm font-medium text-muted-foreground">لا توجد تحاليل محفوظة</p>
          <p className="text-xs text-muted-foreground/55 mt-1">ارفع تحليلاً وسيُحفظ تلقائياً</p>
        </div>
      )}

      {!loading && analyses.map((a, i) => {
        const c          = counts(a)
        const isExpanded = expandedId === a.id
        const selIdx     = selected.findIndex(s => s.id === a.id)
        const isChosen   = selIdx !== -1
        const selNum     = selIdx + 1
        const maxed      = selected.length >= 2 && !isChosen

        return (
          <motion.div
            key={a.id}
            ref={(el: HTMLDivElement | null) => {
              if (el) cardRefs.current.set(a.id, el)
              else cardRefs.current.delete(a.id)
            }}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: maxed ? 0.35 : 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="rounded-3xl border overflow-hidden"
            style={{
              borderColor: isChosen
                ? "var(--primary)"
                : isExpanded
                ? "color-mix(in oklch, var(--primary) 45%, var(--border))"
                : "var(--border)",
              background: isChosen
                ? "color-mix(in oklch, var(--primary) 5%, var(--card))"
                : "var(--card)",
              boxShadow: isChosen
                ? "0 0 0 1px color-mix(in oklch, var(--primary) 20%, transparent), 0 8px 32px -8px oklch(0 0 0 / 0.18)"
                : isExpanded
                ? "0 8px 32px -8px oklch(0 0 0 / 0.12)"
                : "0 1px 3px oklch(0 0 0 / 0.05), 0 4px 12px -4px oklch(0 0 0 / 0.07)",
              transition: "border-color 0.22s, background 0.22s, box-shadow 0.28s",
            }}
          >
            {/* Card body */}
            <div className="px-6 pt-6 pb-5 text-right">
              {/* Date + selection badge row */}
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-1.5">
                  {isChosen && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="w-5 h-5 rounded-full bg-primary text-primary-foreground text-[10px] font-bold flex items-center justify-center"
                    >
                      {selNum}
                    </motion.div>
                  )}
                </div>
                <span className="text-xs text-muted-foreground">{formatDate(a.created_at)}</span>
              </div>

              {/* Summary title */}
              <p className="text-base font-bold text-foreground leading-snug mb-4">{a.summary}</p>

              {/* Stats pills */}
              <div className="flex gap-2 flex-wrap justify-end">
                <span className="text-xs px-3 py-1 rounded-full bg-muted text-muted-foreground font-medium">
                  {c.total} فحص
                </span>
                {c.high > 0 && (
                  <span className="text-xs px-3 py-1 rounded-full bg-destructive/10 text-destructive font-medium">
                    {c.high} مرتفع
                  </span>
                )}
                {c.low > 0 && (
                  <span className="text-xs px-3 py-1 rounded-full bg-warning/10 text-warning font-medium">
                    {c.low} منخفض
                  </span>
                )}
                {c.high === 0 && c.low === 0 && (
                  <span className="text-xs px-3 py-1 rounded-full bg-success/10 text-success font-medium">
                    ✓ كل القيم طبيعية
                  </span>
                )}
              </div>
            </div>

            {/* Divider */}
            <div className="mx-6 h-px bg-border/50" />

            {/* Action Row */}
            <div className="px-5 py-4 flex items-center gap-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => toggleExpand(a.id)}
                className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                  isExpanded
                    ? "bg-primary/10 text-primary border border-primary/25"
                    : "bg-muted/60 text-foreground hover:bg-muted border border-transparent"
                }`}
              >
                <motion.span
                  animate={{ rotate: isExpanded ? 180 : 0 }}
                  transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                  className="inline-flex"
                >
                  <ChevronIcon className="w-4 h-4" />
                </motion.span>
                {isExpanded ? "إخفاء التفاصيل" : "عرض التفاصيل"}
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => !maxed && toggleSelect(a)}
                disabled={maxed}
                className={`flex items-center gap-2 px-5 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                  isChosen
                    ? "bg-primary/12 text-primary border border-primary/30"
                    : maxed
                    ? "text-muted-foreground/30 cursor-not-allowed border border-border/30"
                    : "glass text-muted-foreground hover:text-foreground border border-border/50 hover:border-border"
                }`}
              >
                {isChosen ? (
                  <>
                    <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                    <span>محدد</span>
                  </>
                ) : (
                  <>
                    <ScalesIcon className="w-3.5 h-3.5 shrink-0" />
                    <span>{maxed ? "اكتمل" : "قارن"}</span>
                  </>
                )}
              </motion.button>
            </div>

            {/* Expandable Detail */}
            <AnimatePresence initial={false}>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{
                    height:  { duration: 0.38, ease: [0.22, 1, 0.36, 1] },
                    opacity: { duration: 0.24 },
                  }}
                  className="overflow-hidden"
                >
                  <InlineDetail item={a} onUse={handleUse} />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )
      })}
    </div>
  )
}

/* ─────────────────────────────────────────────
   Main Component
───────────────────────────────────────────── */
export function AnalysisHistory({
  sessionId = "anonymous",
  refreshTrigger = 0,
  onSelect,
  onCompare,
  mockData,
  inline = false,
}: AnalysisHistoryProps) {
  const [analyses, setAnalyses]     = useState<SavedAnalysis[]>(mockData ?? [])
  const [loading, setLoading]       = useState(false)
  const [open, setOpen]             = useState(false)
  const [selected, setSelected]     = useState<SavedAnalysis[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [search, setSearch]         = useState("")

  const [searchScores, setSearchScores] = useState<Record<string, number> | null>(null)

  const cardRefs       = useRef<Map<string, HTMLDivElement>>(new Map())
  const listRef        = useRef<HTMLDivElement>(null)
  const searchTimer    = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => { if (mockData) setAnalyses(mockData) }, [mockData])

  const fetchAnalyses = useCallback(async () => {
    if (mockData) return
    if (!sessionId || sessionId === "anonymous") return
    setLoading(true)
    try {
      const r = await apiGet("/api/analyses/list", { session_id: sessionId })
      if (r.ok) setAnalyses((await r.json()).analyses ?? [])
    } catch {}
    finally { setLoading(false) }
  }, [sessionId, mockData])

  useEffect(() => { if (inline && !mockData) fetchAnalyses() }, [inline, fetchAnalyses, mockData])
  useEffect(() => { if (open && !mockData) fetchAnalyses() }, [open, fetchAnalyses, mockData])
  useEffect(() => { if (refreshTrigger > 0 && !mockData) fetchAnalyses() }, [refreshTrigger, fetchAnalyses, mockData])

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    if (!search.trim() || analyses.length === 0) { setSearchScores(null); return }
    searchTimer.current = setTimeout(async () => {
      try {
        const body = {
          query: search,
          analyses: analyses.map(a => ({
            id: a.id,
            summary: a.summary,
            findings_text: (a.findings ?? []).map(f => f.name).join(" "),
          })),
        }
        const r = await apiPost("/api/search", body)
        if (r.ok) {
          const data = await r.json()
          const scores: Record<string, number> = {}
          for (const item of data.results) scores[item.id] = item.score
          setSearchScores(scores)
        }
      } catch { setSearchScores(null) }
    }, 300)
  }, [search, analyses])

  const toggleSelect = (a: SavedAnalysis) => {
    setSelected(prev => {
      const exists = prev.find(s => s.id === a.id)
      if (exists) return prev.filter(s => s.id !== a.id)
      if (prev.length >= 2) return prev
      return [...prev, a]
    })
  }

  const toggleExpand = (id: string) => {
    setExpandedId(prev => {
      const next = prev === id ? null : id
      if (next) {
        setTimeout(() => {
          cardRefs.current.get(id)?.scrollIntoView({ behavior: "smooth", block: "nearest" })
        }, 120)
      }
      return next
    })
  }

  const handleCompare = () => {
    if (selected.length !== 2) return
    onCompare(selected[0], selected[1])
    setSelected([])
    setOpen(false)
    setExpandedId(null)
  }

  const handleUse = (a: SavedAnalysis) => {
    onSelect({ ...a, report: a.report ?? {} as AnalysisResult["report"] })
    setOpen(false)
    setSelected([])
    setExpandedId(null)
  }

  const closeAll = () => { setOpen(false); setSelected([]); setExpandedId(null) }

  if (!mockData && !inline && (!sessionId || sessionId === "anonymous")) return null

  /* ── INLINE MODE (mockData provided, or inline=true with real session) ── */
  if (mockData || inline) {
    const filtered = search.trim()
      ? searchScores
        ? analyses
            .filter(a => (searchScores[a.id] ?? 0) > 0)
            .sort((a, b) => (searchScores[b.id] ?? 0) - (searchScores[a.id] ?? 0))
        : analyses.filter(a =>
            a.summary.includes(search) || formatDate(a.created_at).includes(search)
          )
      : analyses

    return (
      <div className="w-full relative" dir="rtl">
        {/* Search */}
        <div className="flex justify-center mb-10">
          <div className="relative w-full max-w-2xl">
            <svg className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="ابحث في سجل التحاليل..."
              className="w-full pr-11 pl-11 py-3.5 rounded-2xl glass text-sm text-foreground placeholder:text-muted-foreground focus:outline-none border border-border/60 focus:border-primary/50 transition-colors"
            />
            {search ? (
              <button
                onClick={() => setSearch("")}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-muted flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted/70 transition-colors"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            ) : (
              <kbd className="absolute left-4 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted/80 text-muted-foreground text-[10px] font-medium border border-border/40">
                ⌘K
              </kbd>
            )}
          </div>
        </div>

        {/* Compare Hint */}
        <AnimatePresence>
          {selected.length === 0 && analyses.length > 1 && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22 }}
              className="overflow-hidden mb-8"
            >
              <CompareHint />
            </motion.div>
          )}
        </AnimatePresence>

        <AnalysisCardList
          analyses={filtered}
          loading={loading}
          selected={selected}
          expandedId={expandedId}
          cardRefs={cardRefs}
          listRef={listRef}
          toggleExpand={toggleExpand}
          toggleSelect={toggleSelect}
          handleUse={handleUse}
          containerClassName="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        />

        {analyses.length >= 2 && (
          <div className="mt-12 max-w-3xl mx-auto">
            <HealthTrendChart analyses={analyses} />
          </div>
        )}

        {/* Floating Compare Bar — fixed to bottom of viewport in inline mode */}
        <AnimatePresence>
          {selected.length > 0 && (
            <FloatingCompareBar
              selected={selected}
              onCompare={handleCompare}
              onCancel={() => setSelected([])}
              fixed={true}
            />
          )}
        </AnimatePresence>
      </div>
    )
  }

  /* ── DRAWER MODE (normal usage with sessionId) ── */
  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass text-sm font-medium text-foreground hover:bg-muted/60 transition-colors"
      >
        <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
        </svg>
        سجل التحاليل
        {analyses.length > 0 && (
          <span className="w-5 h-5 rounded-full bg-primary/15 text-primary text-xs flex items-center justify-center font-bold">
            {analyses.length}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40"
              style={{ background: "oklch(0 0 0 / 0.52)", backdropFilter: "blur(8px)", WebkitBackdropFilter: "blur(8px)" }}
              onClick={closeAll}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 280 }}
              className="fixed top-0 left-0 h-full z-50 flex flex-col bg-card"
              style={{
                width: "min(440px, 96vw)",
                borderRight: "1px solid var(--border)",
                boxShadow: "8px 0 48px oklch(0 0 0 / 0.20), 1px 0 0 var(--border)",
              }}
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
                <button onClick={closeAll} className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center hover:bg-muted/70 transition-colors">
                  <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
                <div className="text-right">
                  <h2 className="text-sm font-bold text-foreground">سجل التحاليل</h2>
                  {analyses.length > 0 && <p className="text-[11px] text-muted-foreground">{analyses.length} تحليل محفوظ</p>}
                </div>
              </div>

              <AnimatePresence>
                {selected.length === 0 && !loading && analyses.length > 1 && (
                  <motion.div
                    initial={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.22 }}
                    className="overflow-hidden shrink-0"
                  >
                    <CompareHint />
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="flex-1 overflow-y-auto px-4 py-3 relative">
                <AnalysisCardList
                  analyses={analyses}
                  loading={loading}
                  selected={selected}
                  expandedId={expandedId}
                  cardRefs={cardRefs}
                  listRef={listRef}
                  toggleExpand={toggleExpand}
                  toggleSelect={toggleSelect}
                  handleUse={handleUse}
                />
                {analyses.length >= 2 && (
                  <div className="px-1 pb-4">
                    <HealthTrendChart analyses={analyses} />
                  </div>
                )}
              </div>

              <AnimatePresence>
                {selected.length > 0 && (
                  <FloatingCompareBar
                    selected={selected}
                    onCompare={handleCompare}
                    onCancel={() => setSelected([])}
                  />
                )}
              </AnimatePresence>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
