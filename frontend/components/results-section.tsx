"use client"

import { motion } from "framer-motion"
import type { AnalysisResult, Finding } from "@/app/page"

interface ResultsSectionProps {
  result: AnalysisResult | null
}

const statusConfig = {
  normal: { label: "طبيعي", color: "bg-success", textColor: "text-success", bgColor: "bg-success/10" },
  high:   { label: "مرتفع", color: "bg-destructive", textColor: "text-destructive", bgColor: "bg-destructive/10" },
  low:    { label: "منخفض", color: "bg-warning", textColor: "text-warning", bgColor: "bg-warning/10" },
}

const confidenceConfig = {
  "عالية":    { label: "ثقة عالية",    bg: "rgba(184,243,228,0.3)", text: "#166534", dot: "#22c55e" },
  "متوسطة":   { label: "ثقة متوسطة",   bg: "rgba(254,243,199,0.5)", text: "#854d0e", dot: "#eab308" },
  "منخفضة":   { label: "ثقة منخفضة — راجع طبيبك",  bg: "rgba(254,226,226,0.4)", text: "#991b1b", dot: "#ef4444" },
  "لا يوجد":  { label: "بدون مرجع",    bg: "rgba(241,245,249,0.8)", text: "#64748b", dot: "#94a3b8" },
}

function calcPercentage(value: string, range: string): number {
  const nums = range.match(/[\d.]+/g)
  if (!nums || nums.length < 2) return 50
  const low = parseFloat(nums[0])
  const high = parseFloat(nums[1])
  const val = parseFloat(value)
  if (isNaN(val) || isNaN(low) || isNaN(high) || high === low) return 50
  return Math.max(5, Math.min(95, ((val - low) / (high - low)) * 100))
}

export function ResultsSection({ result }: ResultsSectionProps) {
  if (!result) return null

  return (
    <section id="results" className="py-24 relative bg-muted/30">
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-primary/5 blur-3xl"
        />
      </div>

      <div className="container mx-auto px-6 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <span className="inline-block px-4 py-2 rounded-full glass text-sm text-muted-foreground mb-4">
            نتائج التحليل
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4 text-balance">
            نتائجك الطبية بوضوح
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            تحليل شامل لمؤشراتك الصحية مع شرح مبسط لكل نتيجة وتوصيات مخصصة
          </p>
        </motion.div>

        {result && (
          <>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {result.findings.map((f: Finding, index: number) => {
                const cfg = statusConfig[f.status] ?? statusConfig.normal
                const pct = calcPercentage(f.value, f.range)
                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: index * 0.08 }}
                    whileHover={{ y: -5, transition: { duration: 0.3 } }}
                    className="glass-strong rounded-3xl p-6 shadow-soft hover:shadow-glow-primary transition-all duration-500"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-foreground">{f.name}</h3>
                        {f.range && <p className="text-xs text-muted-foreground mt-0.5">المعدل: {f.range}</p>}
                      </div>
                      <div className={`px-3 py-1 rounded-full text-xs font-medium ${cfg.bgColor} ${cfg.textColor}`}>
                        {cfg.label}
                      </div>
                    </div>

                    <div className="flex items-baseline gap-2 mb-4">
                      <span className="text-3xl font-bold text-foreground">{f.value}</span>
                      {f.unit && <span className="text-muted-foreground">{f.unit}</span>}
                    </div>

                    <div className="mb-2">
                      <div className="h-2.5 rounded-full bg-muted overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: `${pct}%` }}
                          viewport={{ once: true }}
                          transition={{ duration: 1.5, delay: index * 0.08, ease: "easeOut" }}
                          className={`h-full rounded-full ${cfg.color}`}
                        />
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="mt-12 glass-strong rounded-3xl p-8 shadow-soft"
            >
              <div className="flex flex-col md:flex-row items-start gap-8">
                <div className="w-16 h-16 shrink-0 rounded-3xl gradient-primary flex items-center justify-center shadow-glow-primary">
                  <svg className="w-8 h-8 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
                  </svg>
                </div>
                <div className="flex-1 text-right">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <h3 className="text-xl font-bold text-foreground">ملخص الحالة الصحية</h3>
                    {result.report?.rag_confidence && result.report.rag_confidence !== "لا يوجد" && (() => {
                      const cfg = confidenceConfig[result.report.rag_confidence!] ?? confidenceConfig["لا يوجد"]
                      return (
                        <span
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                          style={{ background: cfg.bg, color: cfg.text }}
                        >
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: cfg.dot }} />
                          {cfg.label}
                        </span>
                      )
                    })()}
                  </div>
                  <p className="text-muted-foreground leading-relaxed mb-4">{result.summary}</p>

                  {result.report?.general && (
                    <p className="text-foreground/80 leading-relaxed text-sm mb-4">{result.report.general}</p>
                  )}

                </div>
              </div>
            </motion.div>
          </>
        )}
      </div>
    </section>
  )
}
