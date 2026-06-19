"use client"

import { useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { AnalysisResult } from "@/app/page"

interface UploadSectionProps {
  onResult:     (result: AnalysisResult) => void
  profileName?: string
  previewState?: 'file-ready' | 'analyzing' | 'done' | 'error'
}

export function UploadSection({ onResult, previewState }: UploadSectionProps) {
  const [isDragging, setIsDragging]     = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(
    previewState ? new File([''], 'CBC_Report_May2026.pdf', { type: 'application/pdf' }) : null
  )
  const [isAnalyzing, setIsAnalyzing]   = useState(previewState === 'analyzing')
  const [isDone, setIsDone]             = useState(previewState === 'done')
  const [error, setError]               = useState<string | null>(
    previewState === 'error' ? 'تعذّر الاتصال بالخادم. تأكد من تشغيل الباكند.' : null
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(true)
  }, [])
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false)
  }, [])
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false)
    if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files[0])
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFileUpload(e.target.files[0])
  }

  const handleFileUpload = async (file: File) => {
    setUploadedFile(file)
    setIsAnalyzing(true)
    setIsDone(false)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("file", file)

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
      const res = await fetch(`${backendUrl}/api/analyze`, { method: "POST", body: formData })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || "فشل التحليل")
      }

      const data: AnalysisResult = await res.json()
      onResult(data)
      setIsDone(true)

      setTimeout(() => {
        document.getElementById("results")?.scrollIntoView({ behavior: "smooth" })
      }, 300)
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذّر الاتصال بالخادم. تأكد من تشغيل الباكند.")
      setIsDone(false)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const removeFile = () => {
    setUploadedFile(null)
    setIsAnalyzing(false)
    setIsDone(false)
    setError(null)
  }

  return (
    <section id="analysis" className="py-24 relative">
      <div className="absolute inset-0 overflow-hidden hidden md:block">
        <motion.div
          animate={{ x: [0, 20, 0], y: [0, -20, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
          style={{ willChange: "transform" }}
          className="absolute top-20 right-1/4 w-64 h-64 rounded-full bg-primary/10 blur-3xl"
        />
        <motion.div
          animate={{ x: [0, -30, 0], y: [0, 30, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
          style={{ willChange: "transform" }}
          className="absolute bottom-20 left-1/4 w-80 h-80 rounded-full bg-secondary/10 blur-3xl"
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
            تحليل سريع وآمن
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4 text-balance">
            ارفع تقريرك الطبي
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            قم برفع ملفات PDF أو صور التقارير الطبية وسنقوم بتحليلها فوراً باستخدام أحدث تقنيات الذكاء الاصطناعي
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="max-w-2xl mx-auto"
        >
          {/* منطقة الرفع */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative rounded-3xl transition-all duration-500 ${
              isDragging
                ? "border-2 border-primary border-dashed bg-primary/5 scale-[1.02]"
                : "border-2 border-dashed border-border"
            }`}
          >
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={handleFileInput}
              disabled={isAnalyzing}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10 disabled:cursor-not-allowed"
              aria-label="رفع ملف"
            />

            <div className="glass-strong rounded-3xl p-12 text-center">
              <AnimatePresence mode="wait">
                {!uploadedFile ? (
                  <motion.div
                    key="upload"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="space-y-6"
                  >
                    <motion.div
                      animate={{ y: isDragging ? -10 : 0 }}
                      transition={{ duration: 0.3 }}
                      className="w-20 h-20 mx-auto rounded-3xl gradient-primary flex items-center justify-center shadow-glow-primary"
                    >
                      <svg className="w-10 h-10 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                      </svg>
                    </motion.div>
                    <div>
                      <h3 className="text-xl font-semibold text-foreground mb-2">اسحب الملفات هنا أو انقر للتحميل</h3>
                      <p className="text-muted-foreground">PDF, PNG, JPG حتى 10MB</p>
                    </div>
                    <div className="flex items-center justify-center gap-4">
                      {[
                        { icon: "PDF", color: "bg-destructive/10 text-destructive" },
                        { icon: "PNG", color: "bg-primary/10 text-primary-foreground" },
                        { icon: "JPG", color: "bg-secondary/30 text-secondary-foreground" },
                      ].map((type) => (
                        <div key={type.icon} className={`px-4 py-2 rounded-xl text-sm font-medium ${type.color}`}>
                          {type.icon}
                        </div>
                      ))}
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    key="file"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="space-y-6"
                  >
                    <div className="flex items-center justify-between p-4 rounded-2xl bg-muted/50">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
                          <svg className="w-6 h-6 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                          </svg>
                        </div>
                        <div className="text-right">
                          <div className="font-medium text-foreground">{uploadedFile.name}</div>
                          <div className="text-sm text-muted-foreground">{(uploadedFile.size / 1024 / 1024).toFixed(2)} MB</div>
                        </div>
                      </div>
                      {!isAnalyzing && (
                        <button
                          onClick={removeFile}
                          className="w-10 h-10 rounded-xl bg-destructive/10 text-destructive flex items-center justify-center hover:bg-destructive/20 transition-colors z-20 relative"
                          aria-label="إزالة الملف"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>

                    {isAnalyzing && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-center gap-3">
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                            className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full"
                          />
                          <span className="text-foreground font-medium">جاري تحليل التقرير...</span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                          <motion.div
                            initial={{ width: "0%" }}
                            animate={{ width: ["0%", "60%", "80%", "88%", "93%"] }}
                            transition={{ duration: 30, times: [0, 0.2, 0.5, 0.75, 1], ease: "easeOut" }}
                            className="h-full rounded-full gradient-primary"
                          />
                        </div>
                        <p className="text-xs text-muted-foreground text-center">يستغرق التحليل 10–30 ثانية</p>
                      </div>
                    )}

                    {isDone && !isAnalyzing && (
                      <div className="flex items-center justify-center gap-3 text-success">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-medium">تم التحليل بنجاح!</span>
                      </div>
                    )}

                    {error && !isAnalyzing && (
                      <div className="flex flex-col items-center gap-3">
                        <div className="flex items-center gap-2 text-destructive">
                          <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                          </svg>
                          <span className="font-medium text-sm">{error}</span>
                        </div>
                        <button
                          onClick={() => uploadedFile && handleFileUpload(uploadedFile)}
                          className="px-4 py-2 rounded-xl bg-primary/10 text-primary text-sm font-medium hover:bg-primary/20 transition-colors"
                        >
                          إعادة المحاولة
                        </button>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
            className="flex items-center justify-center gap-2 mt-6 text-sm text-muted-foreground"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
            <span>بياناتك آمنة ومشفرة بالكامل</span>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
