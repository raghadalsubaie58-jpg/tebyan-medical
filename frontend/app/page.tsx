"use client"

import { useState, useCallback, useEffect } from "react"
import { useAuth } from "@/lib/auth-context"
import { Header } from "@/components/header"
import { HeroSection } from "@/components/hero-section"
import { UploadSection } from "@/components/upload-section"
import { ResultsSection } from "@/components/results-section"
import { TermsSection } from "@/components/terms-section"
import { RecommendationsSection } from "@/components/recommendations-section"
import { AboutSection } from "@/components/about-section"
import { Footer } from "@/components/footer"
import { ChatBot } from "@/components/chat-bot"
import { AnalysisHistory } from "@/components/analysis-history"
import { CompareAnalyses } from "@/components/compare-analyses"

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
    general:          string
    abnormal_details: Record<string, string>[]
    tips:             string[]
    rag_confidence?:  "عالية" | "متوسطة" | "منخفضة" | "لا يوجد"
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

export default function Home() {
  const { user } = useAuth()
  const [sessionId, setSessionId] = useState("anonymous")
  const [result, setResult]               = useState<AnalysisResult | null>(null)
  const [refreshHistory, setRefreshHistory] = useState(0)
  const [compareData, setCompareData]     = useState<{ a: SavedAnalysis; b: SavedAnalysis } | null>(null)

  useEffect(() => {
    const id = user?.email ?? user?.id ?? getOrCreateSessionId()
    setSessionId(id)
  }, [user])

  const handleResult = useCallback(async (r: AnalysisResult) => {
    setResult(r)

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
      const res = await fetch(`${backendUrl}/api/analyses/save`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          findings:   r.findings,
          summary:    r.summary,
          report:     r.report,
        }),
      })
      if (!res.ok) {
        const err = await res.text()
        console.error("[save]", res.status, err)
      } else {
        setRefreshHistory(n => n + 1)
      }
    } catch (e) {
      console.error("[save] network error", e)
    }
  }, [sessionId])

  const handleHistorySelect = (a: SavedAnalysis) => {
    setResult({ findings: a.findings, summary: a.summary, report: a.report })
  }

  return (
    <main className="min-h-screen">
      <Header
        extraActions={
          <AnalysisHistory
            sessionId={sessionId}
            refreshTrigger={refreshHistory}
            onSelect={handleHistorySelect}
            onCompare={(a, b) => setCompareData({ a, b })}
          />
        }
      />
      <HeroSection />
      <UploadSection onResult={handleResult} />
      <ResultsSection result={result} />
      <TermsSection result={result} />
      <RecommendationsSection result={result} />
      <AboutSection />
      <Footer />
      <ChatBot analysisResult={result} />

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
