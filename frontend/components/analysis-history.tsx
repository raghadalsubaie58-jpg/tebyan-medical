"use client"

import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { AnalysisResult } from "@/app/page"

interface SavedAnalysis {
  id:         string
  summary:    string
  findings:   AnalysisResult["findings"]
  report:     AnalysisResult["report"]
  created_at: string
}

interface AnalysisHistoryProps {
  sessionId:      string
  refreshTrigger: number
  onSelect:       (a: SavedAnalysis) => void
  onCompare:      (a: SavedAnalysis, b: SavedAnalysis) => void
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)  return "الآن"
  if (m < 60) return `منذ ${m} دقيقة`
  const h = Math.floor(m / 60)
  if (h < 24) return `منذ ${h} ساعة`
  const d = Math.floor(h / 24)
  return `منذ ${d} يوم`
}

export function AnalysisHistory({ sessionId, refreshTrigger, onSelect, onCompare }: AnalysisHistoryProps) {
  const [analyses, setAnalyses]     = useState<SavedAnalysis[]>([])
  const [loading, setLoading]       = useState(false)
  const [open, setOpen]             = useState(false)
  const [selected, setSelected]     = useState<string[]>([])

  const fetchAnalyses = useCallback(async () => {
    if (!sessionId || sessionId === "anonymous") return
    setLoading(true)
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
      const params = new URLSearchParams({ session_id: sessionId })
      const r = await fetch(`${base}/api/analyses/list?${params}`)
      if (r.ok) {
        const d = await r.json()
        setAnalyses(d.analyses ?? [])
      }
    } catch {}
    finally { setLoading(false) }
  }, [sessionId])

  useEffect(() => { if (open) fetchAnalyses() }, [open, fetchAnalyses])
  useEffect(() => { if (refreshTrigger > 0) fetchAnalyses() }, [refreshTrigger, fetchAnalyses])

  const toggleSelect = (id: string) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 2 ? [...prev, id] : [prev[1], id]
    )
  }

  const handleCompare = () => {
    const [a, b] = selected.map(id => analyses.find(x => x.id === id)!)
    if (a && b) { onCompare(a, b); setOpen(false) }
  }

  const abnormalCount = (a: SavedAnalysis) => a.findings?.filter(f => f.status !== "normal").length ?? 0

  if (!sessionId || sessionId === "anonymous") return null

  return (
    <>
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
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, x: 300 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 300 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed top-0 left-0 h-full w-full max-w-sm glass-strong border-r border-border/40 shadow-2xl z-50 flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-border/30">
                <div>
                  <h2 className="text-lg font-bold text-foreground">سجل التحاليل</h2>
                </div>
                <button onClick={() => setOpen(false)} className="w-8 h-8 rounded-xl bg-muted/50 flex items-center justify-center hover:bg-muted transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Compare bar */}
              {selected.length === 2 && (
                <div className="mx-4 mt-4 p-3 rounded-2xl bg-primary/10 flex items-center justify-between">
                  <p className="text-sm text-primary font-medium">تحليلان محددان للمقارنة</p>
                  <button onClick={handleCompare} className="text-xs px-3 py-1.5 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors">
                    قارن
                  </button>
                </div>
              )}
              {selected.length === 1 && (
                <p className="text-xs text-muted-foreground text-center mt-3 px-4">اختر تحليلاً ثانياً للمقارنة</p>
              )}

              {/* List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {loading && (
                  <div className="flex items-center justify-center py-12">
                    <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                      className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
                  </div>
                )}

                {!loading && analyses.length === 0 && (
                  <div className="text-center py-16 space-y-3">
                    <div className="w-16 h-16 mx-auto rounded-3xl bg-muted/50 flex items-center justify-center">
                      <svg className="w-8 h-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                      </svg>
                    </div>
                    <p className="text-sm text-muted-foreground">لا توجد تحاليل محفوظة بعد</p>
                    <p className="text-xs text-muted-foreground/70">ارفع تحليلاً وسيُحفظ تلقائياً</p>
                  </div>
                )}

                {!loading && analyses.map((a, i) => {
                  const abn = abnormalCount(a)
                  const isSelected = selected.includes(a.id)
                  return (
                    <motion.div
                      key={a.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
                        isSelected ? "border-primary/50 bg-primary/5" : "border-border/30 bg-background/50"
                      }`}
                    >
                      <div className="p-3.5">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex-1">
                            <p className="text-sm font-medium text-foreground line-clamp-2">{a.summary}</p>
                            <p className="text-xs text-muted-foreground mt-0.5">{timeAgo(a.created_at)}</p>
                          </div>
                          <label className="shrink-0 flex items-center">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelect(a.id)}
                              className="w-4 h-4 accent-primary cursor-pointer"
                              title="تحديد للمقارنة"
                            />
                          </label>
                        </div>

                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-muted/60 text-muted-foreground">
                            {a.findings?.length ?? 0} فحص
                          </span>
                          {abn > 0 && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-destructive/10 text-destructive">
                              {abn} غير طبيعي
                            </span>
                          )}
                        </div>

                        <button
                          onClick={() => { onSelect({ ...a, report: a.report ?? {} as AnalysisResult["report"] }); setOpen(false) }}
                          className="mt-3 w-full text-xs py-1.5 rounded-xl bg-primary/10 text-primary font-medium hover:bg-primary/20 transition-colors"
                        >
                          عرض النتائج
                        </button>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
