"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { AnalysisResult } from "@/app/page"

const faqQuestions = [
  { id: 1, text: "ما سبب الشعور بالتعب المستمر؟", color: "green" },
  { id: 2, text: "كيف أرفع تحليلي؟", color: "pink" },
  { id: 3, text: "ماذا تنصحني لتحسين صحتي؟", color: "mixed" },
]

interface ChatBotProps {
  analysisResult?: AnalysisResult | null
}

type Message = { role: "assistant" | "user"; content: string }

export function ChatBot({ analysisResult }: ChatBotProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "مرحباً! أنا مساعدك الطبي. كيف يمكنني مساعدتك اليوم؟" },
  ])
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isTyping])

  const sendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return

    const userMessage: Message = { role: "user", content: text }
    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setInputValue("")
    setIsTyping(true)

    const history = updatedMessages.slice(0, -1).map((m) => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: text,
          history,
          analysis_context: analysisResult ? JSON.stringify(analysisResult) : "",
        }),
      })

      if (!res.ok || !res.body) throw new Error("no stream")

      setMessages((prev) => [...prev, { role: "assistant", content: "" }])
      setIsTyping(false)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: "assistant",
            content: updated[updated.length - 1].content + chunk,
          }
          return updated
        })
      }
    } catch {
      setIsTyping(false)
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "تعذّر الاتصال بالخادم. تأكد من تشغيل الباكند." },
      ])
    }
  }

  return (
    <>
      <motion.button
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 1.5, type: "spring", stiffness: 200, damping: 15 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center overflow-hidden"
        style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #a8e8d8 50%, #FFD7EC 100%)" }}
        aria-label="فتح المساعد الذكي"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.svg key="close" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.2 }} className="w-5 h-5 text-[#111111]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </motion.svg>
          ) : (
            <motion.svg key="chat" initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.5, opacity: 0 }} transition={{ duration: 0.2 }} className="w-5 h-5 text-[#111111]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
            </motion.svg>
          )}
        </AnimatePresence>
        {!isOpen && (
          <motion.div animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0, 0.3] }} transition={{ duration: 3, repeat: Infinity }} className="absolute inset-0 rounded-full" style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #FFD7EC 100%)" }} />
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="fixed bottom-24 right-6 z-50 w-[320px] max-w-[calc(100vw-3rem)] rounded-[28px] overflow-hidden"
            style={{
              background: "rgba(255,255,255,0.92)",
              backdropFilter: "blur(24px)",
              WebkitBackdropFilter: "blur(24px)",
              boxShadow: "0 4px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.02)",
              border: "1px solid rgba(255,255,255,0.8)",
            }}
          >
            {/* Header */}
            <div className="px-5 py-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-full flex items-center justify-center" style={{ background: "linear-gradient(135deg, rgba(184,243,228,0.5) 0%, rgba(255,215,236,0.5) 100%)" }}>
                <svg className="w-4 h-4 text-[#111111]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
                </svg>
              </div>
              <div className="flex-1">
                <span className="text-sm font-medium text-[#111111]">المساعد الذكي</span>
                {analysisResult && (
                  <p className="text-[10px] text-emerald-600 mt-0.5">متصل بتحليلك الأخير</p>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="h-56 overflow-y-auto px-4 pb-3 space-y-3">
              <AnimatePresence mode="popLayout">
                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    transition={{ duration: 0.3 }}
                    className={`flex ${msg.role === "user" ? "justify-start" : "justify-end"}`}
                  >
                    <div
                      className={`max-w-[82%] px-3.5 py-2.5 ${msg.role === "user" ? "rounded-2xl rounded-tr-lg" : "rounded-2xl rounded-tl-lg"}`}
                      style={{
                        background: msg.role === "user"
                          ? "linear-gradient(135deg, rgba(184,243,228,0.6) 0%, rgba(184,243,228,0.4) 100%)"
                          : "rgba(249,250,251,0.95)",
                        color: "#111111",
                      }}
                    >
                      <p className="text-[13px] leading-relaxed whitespace-pre-line">{msg.content}</p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              <AnimatePresence>
                {isTyping && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex justify-end">
                    <div className="px-4 py-3 rounded-2xl rounded-tl-lg flex items-center gap-1.5" style={{ background: "rgba(249,250,251,0.95)" }}>
                      {[0, 0.2, 0.4].map((delay, i) => (
                        <motion.span key={i} animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay }} className="w-1.5 h-1.5 rounded-full bg-[#9CA3AF]" />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>

            {/* FAQ */}
            <div className="px-4 pb-2">
              <div className="flex flex-wrap gap-2 justify-center">
                {faqQuestions.map((faq, i) => (
                  <motion.button
                    key={faq.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 + i * 0.06 }}
                    whileHover={{ scale: 1.03, y: -1 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => sendMessage(faq.text)}
                    disabled={isTyping}
                    className="px-3 py-1.5 rounded-full text-[11px] font-medium text-[#333333] transition-all duration-200 disabled:opacity-50"
                    style={{
                      background: faq.color === "green"
                        ? "linear-gradient(135deg, rgba(184,243,228,0.45) 0%, rgba(184,243,228,0.25) 100%)"
                        : faq.color === "pink"
                        ? "linear-gradient(135deg, rgba(255,215,236,0.45) 0%, rgba(255,215,236,0.25) 100%)"
                        : "linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(249,250,251,0.9) 100%)",
                      border: "1px solid rgba(0,0,0,0.03)",
                    }}
                  >
                    {faq.text}
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Input */}
            <div className="px-4 pb-4">
              <div className="flex items-center gap-2 rounded-full px-1 py-1" style={{ background: "rgba(249,250,251,0.8)", border: "1px solid rgba(0,0,0,0.04)" }}>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage(inputValue)}
                  placeholder="اكتب سؤالك الطبي..."
                  disabled={isTyping}
                  className="flex-1 px-3 py-2 bg-transparent text-[13px] text-[#111111] placeholder:text-[#BABABA] focus:outline-none disabled:opacity-50"
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => sendMessage(inputValue)}
                  disabled={isTyping || !inputValue.trim()}
                  className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 disabled:opacity-50"
                  style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #a8e8d8 100%)" }}
                  aria-label="إرسال"
                >
                  <svg className="w-3.5 h-3.5 text-[#111111] rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                  </svg>
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
