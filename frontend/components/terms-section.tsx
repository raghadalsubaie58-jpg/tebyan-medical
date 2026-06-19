"use client"

import { motion } from "framer-motion"
import type { AnalysisResult } from "@/app/page"

interface TermsSectionProps {
  result: AnalysisResult | null
}

function StatusIcon({ status }: { status: string }) {
  const isHigh = status === "مرتفع" || status === "high"
  return (
    <svg className="w-7 h-7 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
      {isHigh ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
      ) : (
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6L9 12.75l4.306-4.307a11.95 11.95 0 015.814 5.519l2.74 1.22m0 0l-5.94 2.28m5.94-2.28l-2.28-5.941" />
      )}
    </svg>
  )
}

export function TermsSection({ result }: TermsSectionProps) {
  if (!result) return null

  const abnormal = result.report?.abnormal_details ?? []

  return (
    <motion.section
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7 }}
      id="help"
      className="py-24 relative"
    >
      {/* Background — hidden on mobile for performance */}
      <div className="absolute inset-0 overflow-hidden hidden md:block">
        <motion.div
          animate={{ x: [0, 40, 0], y: [0, -30, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
          style={{ willChange: "transform" }}
          className="absolute top-20 left-1/4 w-72 h-72 rounded-full bg-secondary/15 blur-3xl"
        />
        <motion.div
          animate={{ x: [0, -30, 0], y: [0, 40, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          style={{ willChange: "transform" }}
          className="absolute bottom-20 right-1/4 w-80 h-80 rounded-full bg-primary/10 blur-3xl"
        />
      </div>

      <div className="container mx-auto px-6 relative z-10">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <span className="inline-block px-4 py-2 rounded-full glass text-sm text-muted-foreground mb-4">
            قاموس طبي مبسط
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4 text-balance">
            تبسيط المصطلحات
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            نحوّل المصطلحات الطبية المعقدة إلى لغة عربية واضحة وسهلة الفهم لمساعدتك على فهم حالتك الصحية
          </p>
        </motion.div>

        {abnormal.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="max-w-lg mx-auto"
          >
            <div className="group glass-strong rounded-3xl p-6 h-full shadow-soft hover:shadow-glow-secondary transition-all duration-500">
              <div className="flex items-start gap-4 mb-4">
                <div className="w-14 h-14 rounded-2xl bg-secondary/30 flex items-center justify-center text-2xl">
                  ✅
                </div>
                <div>
                  <h3 className="text-lg font-bold text-foreground">جميع القيم طبيعية</h3>
                  <p className="text-sm text-muted-foreground font-mono">All Normal</p>
                </div>
              </div>
              <p className="text-muted-foreground leading-relaxed">
                لا توجد قيم غير طبيعية في تقريرك، جميع مؤشراتك ضمن المعدلات الطبيعية المعتمدة.
              </p>
            </div>
          </motion.div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {abnormal.map((item, index) => {
              const name        = item["اسم_الفحص"]       ?? `فحص ${index + 1}`
              const value       = item["النتيجة"]          ?? ""
              const normalRange = item["المعدل_الطبيعي"]   ?? ""
              const status      = item["الحالة"]           ?? ""
              const explanation = item["الشرح"]            ?? ""
              const reference   = item["المرجع"]           ?? ""

              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  whileHover={{ y: -5, transition: { duration: 0.3 } }}
                  className="group"
                >
                  <div className="glass-strong rounded-3xl p-6 h-full shadow-soft hover:shadow-glow-secondary transition-all duration-500">
                    {/* Icon & Name */}
                    <div className="flex items-start gap-4 mb-4">
                      <div className="w-14 h-14 rounded-2xl bg-secondary/30 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shrink-0">
                        <StatusIcon status={status} />
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-foreground">{name}</h3>
                        {value && normalRange && (
                          <p className="text-sm text-muted-foreground">
                            {value} · الطبيعي: {normalRange}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Explanation */}
                    <p className="text-muted-foreground leading-relaxed">
                      {explanation || `قيمة ${status === "مرتفع" ? "مرتفعة" : "منخفضة"} عن المعدل الطبيعي.`}
                    </p>

                    {/* Reference */}
                    {reference && reference !== "لا يوجد" && (
                      <p className="text-xs text-muted-foreground/60 mt-3 border-t border-border pt-3">
                        المرجع: {reference}
                      </p>
                    )}
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}
      </div>
    </motion.section>
  )
}
