"use client"

import { useState, useCallback, useEffect } from "react"
import dynamic from "next/dynamic"
import { motion, AnimatePresence } from "framer-motion"
import { useAuth } from "@/lib/auth-context"
import { apiPost } from "@/lib/api"
import { Header }                 from "@/components/header"
import { HeroSection }            from "@/components/hero-section"
import { UploadSection }          from "@/components/upload-section"
import { TermsSection }           from "@/components/terms-section"
import { RecommendationsSection } from "@/components/recommendations-section"
import { AboutSection }           from "@/components/about-section"
import { Footer }                 from "@/components/footer"
import { ChatBot }                from "@/components/chat-bot"
import { AnalysisHistory }        from "@/components/analysis-history"
import { ReviewHighlight }        from "@/components/review-mode"

const CompareAnalyses = dynamic(() =>
  import("@/components/compare-analyses").then((m) => m.CompareAnalyses), { ssr: false }
)
const RiskDashboard = dynamic(() =>
  import("@/components/risk-dashboard").then((m) => m.RiskDashboard), { ssr: false }
)

// ═══════════════════════════════════════════
// Types
// ═══════════════════════════════════════════
export interface Finding {
  name:   string
  value:  string
  range:  string
  unit:   string
  status: "normal" | "high" | "low"
}

export interface AnalysisResult {
  findings: Finding[]
  summary:  string
  report: {
    general:           string
    abnormal_details:  Record<string, string>[]
    tips:              string[]
    tips_categorized?: { category: string; tips: string[] }[]
    rag_confidence?:   "عالية" | "متوسطة" | "منخفضة" | "لا يوجد"
  }
}

interface SavedAnalysis {
  id:         string
  summary:    string
  findings:   Finding[]
  report:     AnalysisResult["report"]
  created_at: string
}

function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "anonymous"
  let id = localStorage.getItem("tebyan_session_id")
  if (!id) {
    id = "local_" + Math.random().toString(36).slice(2) + Date.now().toString(36)
    localStorage.setItem("tebyan_session_id", id)
  }
  return id
}

// ═══════════════════════════════════════════
// Scroll To Top
// ═══════════════════════════════════════════
function ScrollToTop() {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const fn = () => setVisible(window.scrollY > 600)
    window.addEventListener("scroll", fn)
    return () => window.removeEventListener("scroll", fn)
  }, [])
  return (
    <AnimatePresence>
      {visible && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="fixed bottom-24 right-6 z-40 w-11 h-11 rounded-2xl glass-strong shadow-soft border border-border flex items-center justify-center hover:shadow-glow-primary transition-all duration-300"
          aria-label="رجوع للأعلى"
        >
          <svg className="w-5 h-5 text-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
          </svg>
        </motion.button>
      )}
    </AnimatePresence>
  )
}

// ═══════════════════════════════════════════
// Results — grid cards + PDF export
// ═══════════════════════════════════════════
const statusCfg: Record<string, { label: string; bg: string; text: string; bar: string }> = {
  normal: { label: "طبيعي",  bg: "bg-success/10",    text: "text-success",     bar: "bg-success"    },
  high:   { label: "مرتفع", bg: "bg-destructive/10", text: "text-destructive", bar: "bg-destructive" },
  low:    { label: "منخفض", bg: "bg-warning/10",     text: "text-warning",     bar: "bg-warning"     },
}

function calcPct(value: string, range: string) {
  const nums = range.match(/[\d.]+/g)
  if (!nums || nums.length < 2) return 50
  const lo = parseFloat(nums[0]), hi = parseFloat(nums[1]), val = parseFloat(value)
  if (isNaN(val) || isNaN(lo) || isNaN(hi) || hi === lo) return 50
  return Math.max(5, Math.min(95, ((val - lo) / (hi - lo)) * 100))
}

function ImprovedResults({ result }: { result: AnalysisResult | null }) {
  const [exporting, setExporting] = useState(false)

  const handleExport = () => {
    setExporting(true)
    setTimeout(() => {
      window.print()
      setExporting(false)
    }, 300)
  }

  const handlePrint = () => window.print()

  if (!result || !result.findings?.length) return null

  return (
    <section id="results" className="py-24 relative bg-muted/30">
      <div className="absolute inset-0 overflow-hidden">
        <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-primary/5 blur-3xl" />
      </div>
      <div className="container mx-auto px-6 relative z-10">
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          transition={{ duration: 0.8 }} className="text-center mb-16">
          <span className="inline-block px-4 py-2 rounded-full glass text-sm text-muted-foreground mb-4">نتائج التحليل</span>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">نتائجك الطبية بوضوح</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">تحليل شامل لمؤشراتك الصحية مع شرح مبسط لكل نتيجة</p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {result.findings.map((f, i) => {
            const cfg = statusCfg[f.status] ?? statusCfg.normal
            const pct = calcPct(f.value, f.range)
            return (
              <motion.div key={i} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                transition={{ duration: 0.6, delay: i * 0.08 }} whileHover={{ y: -5, transition: { duration: 0.3 } }}
                className="glass-strong rounded-3xl p-6 shadow-soft hover:shadow-glow-primary transition-all duration-500">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">{f.name}</h3>
                    {f.range && <p className="text-xs text-muted-foreground mt-0.5">المعدل: {f.range}</p>}
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>{cfg.label}</div>
                </div>
                <div className="flex items-baseline gap-2 mb-4">
                  <span className="text-3xl font-bold text-foreground">{f.value}</span>
                  {f.unit && <span className="text-muted-foreground">{f.unit}</span>}
                </div>
                <div className="h-2.5 rounded-full bg-muted overflow-hidden">
                  <motion.div initial={{ width: 0 }} whileInView={{ width: `${pct}%` }} viewport={{ once: true }}
                    transition={{ duration: 1.5, delay: i * 0.08, ease: "easeOut" }} className={`h-full rounded-full ${cfg.bar}`} />
                </div>
              </motion.div>
            )
          })}
        </div>

        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.3 }} className="mt-12 glass-strong rounded-3xl p-8 shadow-soft">
          <div className="flex flex-col md:flex-row items-start gap-8">
            <div className="w-16 h-16 shrink-0 rounded-3xl gradient-primary flex items-center justify-center shadow-glow-primary">
              <svg className="w-8 h-8 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
              </svg>
            </div>
            <div className="flex-1 text-right">
              <h3 className="text-xl font-bold text-foreground mb-2">ملخص الحالة الصحية</h3>
              <p className="text-muted-foreground leading-relaxed mb-4">{result.summary}</p>
              {result.report?.general && <p className="text-foreground/80 leading-relaxed text-sm mb-5">{result.report.general}</p>}
              <ReviewHighlight changeId={8} className="flex flex-wrap gap-3">
                <motion.button whileTap={{ scale: 0.97 }} onClick={handleExport}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-2xl gradient-primary text-primary-foreground text-sm font-medium shadow-glow-primary hover:opacity-90 transition-opacity">
                  {exporting
                    ? <><motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full" />جاري التحميل...</>
                    : <><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>تحميل PDF</>}
                </motion.button>
                <motion.button whileTap={{ scale: 0.97 }} onClick={handlePrint}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-2xl glass text-foreground text-sm font-medium hover:bg-card/80 transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0l.229 2.523a1.125 1.125 0 01-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0021 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 00-1.913-.247M6.34 18H5.25A2.25 2.25 0 013 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.041 48.041 0 011.913-.247m10.5 0a48.536 48.536 0 00-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5zm-3 0h.008v.008H15V10.5z" /></svg>
                  طباعة
                </motion.button>
              </ReviewHighlight>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

// ═══════════════════════════════════════════
// الصفحة الرئيسية
// ═══════════════════════════════════════════
export default function Home() {
  const { user } = useAuth()
  const [sessionId,      setSessionId]      = useState("anonymous")
  const [result,         setResult]         = useState<AnalysisResult | null>(null)
  const [refreshHistory, setRefreshHistory] = useState(0)
  const [compareData,    setCompareData]    = useState<{ a: SavedAnalysis; b: SavedAnalysis } | null>(null)
  const [darkMode,       setDarkMode]       = useState(false)

  useEffect(() => {
    const id = user?.id ?? getOrCreateSessionId()  // UUID preferred over email for security
    setSessionId(id)
  }, [user])

  const toggleDark = useCallback(() => setDarkMode((d) => !d), [])

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode)
  }, [darkMode])

  const handleResult = useCallback(async (r: AnalysisResult) => {
    setResult(r)
    try {
      const res = await apiPost("/api/analyses/save", {
        session_id: sessionId,
        findings:   r.findings,
        summary:    r.summary,
        report:     r.report,
      })
      if (!res.ok) {
        console.error("[save]", res.status, await res.text())
      } else {
        setRefreshHistory(n => n + 1)
      }
    } catch (e) {
      console.error("[save] network error", e)
    }
  }, [sessionId])

  const handleHistorySelect = useCallback((a: SavedAnalysis) => {
    setResult({ findings: a.findings, summary: a.summary, report: a.report })
    setTimeout(() => {
      document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" })
    }, 120)
  }, [])

  return (
    <main className="min-h-screen" dir="rtl">
      <Header darkMode={darkMode} toggleDark={toggleDark} />
      <HeroSection />
      <UploadSection onResult={handleResult} />
      <ImprovedResults result={result} />
      {result && (
        <section className="py-8 relative">
          <div className="container mx-auto px-6">
            <RiskDashboard analysis={result} />
          </div>
        </section>
      )}
      <TermsSection result={result} />
      <RecommendationsSection result={result} />

      {/* History section */}
      <section id="history" className="py-24 relative overflow-hidden">
        <div className="absolute inset-0 bg-muted/25" />
        <div className="container mx-auto px-6 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass mb-6">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-sm text-muted-foreground">سجل التحاليل</span>
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">تحاليلك السابقة</h2>
            <p className="text-lg text-muted-foreground leading-relaxed max-w-xl mx-auto">
              استعرض وقارن تحاليلك لمتابعة صحتك بمرور الوقت
            </p>
          </motion.div>
          <AnalysisHistory
            sessionId={sessionId}
            refreshTrigger={refreshHistory}
            onSelect={handleHistorySelect}
            onCompare={(a, b) => setCompareData({ a, b })}
            inline
          />
        </div>
      </section>

      <AboutSection />
      <Footer />

      <ChatBot analysisResult={result} sessionId={sessionId} />
      <ScrollToTop />

      {compareData && (
        <CompareAnalyses
          a={compareData.a}
          b={compareData.b}
          onClose={() => setCompareData(null)}
        />
      )}
    </main>
  )
}
