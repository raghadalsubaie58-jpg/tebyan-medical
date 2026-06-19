"use client"

import { useState, useCallback, useEffect } from "react"
import dynamic from "next/dynamic"
import { motion, AnimatePresence } from "framer-motion"
import { useAuth } from "@/lib/auth-context"
import { apiPost } from "@/lib/api"
import { Header }      from "@/components/header"
import { HeroSection } from "@/components/hero-section"
import { UploadSection } from "@/components/upload-section"

// كل ما هو تحت الصفحة يُحمَّل بشكل متأخر — يحسّن وقت الاستجابة الأولية على الجوال
const ResultsSection      = dynamic(() => import("@/components/results-section").then(m => m.ResultsSection), { ssr: false })
const TermsSection        = dynamic(() => import("@/components/terms-section").then(m => m.TermsSection), { ssr: false })
const RecommendationsSection = dynamic(() => import("@/components/recommendations-section").then(m => m.RecommendationsSection), { ssr: false })
const AboutSection        = dynamic(() => import("@/components/about-section").then(m => m.AboutSection), { ssr: false })
const Footer              = dynamic(() => import("@/components/footer").then(m => m.Footer), { ssr: false })
const ChatBot             = dynamic(() => import("@/components/chat-bot").then(m => m.ChatBot), { ssr: false })
const AnalysisHistory     = dynamic(() => import("@/components/analysis-history").then(m => m.AnalysisHistory), { ssr: false })
const CompareAnalyses     = dynamic(() => import("@/components/compare-analyses").then(m => m.CompareAnalyses), { ssr: false })
const RiskDashboard       = dynamic(() => import("@/components/risk-dashboard").then(m => m.RiskDashboard), { ssr: false })

// ═══════════════════════════════════════════
// Types
// ═══════════════════════════════════════════
import type { Finding } from "@/lib/types"
export type { Finding }

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
    window.addEventListener("scroll", fn, { passive: true })
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

  // Initialize from saved preference (anti-flash script already applied the class)
  useEffect(() => {
    if (localStorage.getItem('tabyan-theme') === 'dark') setDarkMode(true)
  }, [])

  const toggleDark = useCallback(() => {
    setDarkMode(d => {
      const next = !d
      document.documentElement.classList.toggle("dark", next)
      localStorage.setItem('tabyan-theme', next ? 'dark' : 'light')
      return next
    })
  }, [])

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
      <ResultsSection result={result} />
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
