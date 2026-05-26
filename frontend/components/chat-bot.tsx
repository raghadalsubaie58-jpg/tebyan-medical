"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import type { AnalysisResult } from "@/app/page"
import { VoiceRecorder } from "./voice-recorder"
import { apiGet, apiPost } from "@/lib/api"

const WELCOME  = "مرحباً! أنا مساعدك الطبي. كيف يمكنني مساعدتك اليوم؟"

const faqQuestions = [
  { id: 1, text: "ما سبب الشعور بالتعب المستمر؟", color: "primary" },
  { id: 2, text: "كيف أرفع تحليلي؟",                color: "secondary" },
  { id: 3, text: "ماذا تنصحني لتحسين صحتي؟",        color: "muted" },
]

interface ChatBotProps {
  analysisResult?: AnalysisResult | null
  sessionId?: string
}

type Message = { role: "assistant" | "user"; content: string }

export function ChatBot({ analysisResult, sessionId = "anonymous" }: ChatBotProps) {
  const [isOpen, setIsOpen]         = useState(false)
  const [messages, setMessages]     = useState<Message[]>([{ role: "assistant", content: WELCOME }])
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping]     = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant")?.content ?? ""

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isTyping])

  // ── Load chat history when panel first opens ──────────────────
  useEffect(() => {
    if (!isOpen || historyLoaded || sessionId === "anonymous") return
    setHistoryLoaded(true)

    apiGet(`/api/chat/history/${encodeURIComponent(sessionId)}`, { limit: 30 })
      .then((r) => r.json())
      .then(({ messages: saved }: { messages: Message[] }) => {
        if (saved && saved.length > 0) {
          setMessages([{ role: "assistant", content: WELCOME }, ...saved])
        }
      })
      .catch(() => {})
  }, [isOpen, historyLoaded, sessionId])

  // ── Persist exchange to backend ───────────────────────────────
  const saveExchange = useCallback(
    (userMsg: string, assistantMsg: string) => {
      if (sessionId === "anonymous" || !assistantMsg.trim()) return
      apiPost("/api/chat/save", {
        session_id: sessionId,
        messages: [
          { role: "user",      content: userMsg },
          { role: "assistant", content: assistantMsg },
        ],
      }).catch(() => {})
    },
    [sessionId]
  )

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

    let assistantReply = ""

    try {
      const res = await apiPost("/api/chat", {
        query: text,
        history,
        analysis_context: analysisResult ? JSON.stringify(analysisResult) : "",
      })

      if (!res.ok || !res.body) throw new Error("no stream")

      setMessages((prev) => [...prev, { role: "assistant", content: "" }])
      setIsTyping(false)

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        assistantReply += chunk
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: "assistant",
            content: updated[updated.length - 1].content + chunk,
          }
          return updated
        })
      }

      saveExchange(text, assistantReply)
    } catch {
      setIsTyping(false)
      const errMsg = "تعذّر الاتصال بالخادم. تأكد من تشغيل الباكند."
      setMessages((prev) => [...prev, { role: "assistant", content: errMsg }])
    }
  }

  return (
    <>
      {/* ── Trigger button ── */}
      <motion.button
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 1.5, type: "spring", stiffness: 200, damping: 15 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-glow-primary flex items-center justify-center overflow-hidden gradient-primary"
        aria-label="فتح المساعد الذكي"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.svg key="close" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.2 }} className="w-5 h-5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </motion.svg>
          ) : (
            <motion.svg key="chat" initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.5, opacity: 0 }} transition={{ duration: 0.2 }} className="w-5 h-5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
            </motion.svg>
          )}
        </AnimatePresence>
        {!isOpen && (
          <motion.div
            animate={{ scale: [1, 1.35, 1], opacity: [0.35, 0, 0.35] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="absolute inset-0 rounded-full gradient-primary pointer-events-none"
          />
        )}
      </motion.button>

      {/* ── Chat panel ── */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.96 }}
            transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
            className="fixed bottom-24 right-6 z-50 w-[340px] max-w-[calc(100vw-2rem)] rounded-[28px] overflow-hidden glass-strong shadow-soft"
            style={{ border: "1px solid var(--border)" }}
          >
            {/* Header */}
            <div className="px-5 py-4 flex items-center gap-3 border-b border-border/50">
              <div className="w-9 h-9 rounded-full flex items-center justify-center bg-primary/15">
                <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
                </svg>
              </div>
              <div className="flex-1">
                <span className="text-sm font-semibold text-foreground">المساعد الذكي</span>
                <p className="text-[10px] text-muted-foreground">مساعد طبي ذكي</p>
              </div>
            </div>

            {/* Messages */}
            <div className="h-72 overflow-y-auto px-4 py-3 space-y-3 scroll-smooth overscroll-contain"
              style={{ scrollbarWidth: "thin", scrollbarColor: "var(--border) transparent" }}>
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
                      className={`max-w-[82%] px-3.5 py-2.5 text-foreground ${
                        msg.role === "user"
                          ? "rounded-2xl rounded-tr-lg bg-primary/12 border border-primary/20"
                          : "rounded-2xl rounded-tl-lg bg-muted border border-border/50"
                      }`}
                    >
                      <p className="text-[13px] leading-relaxed whitespace-pre-line">{msg.content}</p>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              <AnimatePresence>
                {isTyping && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex justify-end">
                    <div className="px-4 py-3 rounded-2xl rounded-tl-lg flex items-center gap-1.5 bg-muted border border-border/50">
                      {[0, 0.2, 0.4].map((delay, i) => (
                        <motion.span key={i} animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay }} className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>

            {/* FAQ quick questions */}
            <div className="px-4 pb-2">
              <div className="flex flex-wrap gap-1.5 justify-center">
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
                    className={`px-3 py-1.5 rounded-full text-[11px] font-medium text-foreground transition-all duration-200 disabled:opacity-50 border ${
                      faq.color === "primary"
                        ? "bg-primary/10 border-primary/20 hover:bg-primary/15"
                        : faq.color === "secondary"
                        ? "bg-secondary/30 border-border/50 hover:bg-secondary/40"
                        : "bg-muted border-border/50 hover:bg-muted/70"
                    }`}
                  >
                    {faq.text}
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Input */}
            <div className="px-4 pb-4 pt-2">
              <div className="flex items-center gap-2 rounded-full px-1 py-1 bg-input border border-border/60">
                <VoiceRecorder
                  onTranscription={(text) => sendMessage(text)}
                  ttsText={lastAssistantMsg}
                  disabled={isTyping}
                />
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage(inputValue)}
                  placeholder="اكتب أو انقر الميكروفون..."
                  disabled={isTyping}
                  className="flex-1 px-3 py-2 bg-transparent text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-primary/40 rounded-full disabled:opacity-50 transition-shadow"
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => sendMessage(inputValue)}
                  disabled={isTyping || !inputValue.trim()}
                  className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 disabled:opacity-50 gradient-primary shadow-glow-primary"
                  aria-label="إرسال"
                >
                  <svg className="w-3.5 h-3.5 text-primary-foreground rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
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
