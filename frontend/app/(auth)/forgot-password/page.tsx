"use client"

import { useState } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { Mail, Sparkles, ChevronLeft, Send, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth-context"

export default function ForgotPasswordPage() {
  const { resetPassword } = useAuth()
  const [email,   setEmail]   = useState("")
  const [loading, setLoading] = useState(false)
  const [sent,    setSent]    = useState(false)
  const [error,   setError]   = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    if (!email) { setError("يرجى إدخال بريدك الإلكتروني"); return }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError("صيغة البريد غير صحيحة"); return }

    setLoading(true)
    const { error: err } = await resetPassword(email)
    setLoading(false)

    if (err) {
      toast.error("تعذّر إرسال البريد — تأكد من صحة العنوان وحاول مجدداً")
      return
    }
    setSent(true)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <Link href="/" className="inline-flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shadow-glow-primary">
              <Sparkles className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold text-foreground">تبيان الطبي</span>
          </Link>
        </div>

        <div className="glass-strong rounded-3xl p-8 shadow-2xl shadow-black/10">
          <AnimatePresence mode="wait">

            {/* ── Sent state ──────────────────────────────────────── */}
            {sent ? (
              <motion.div
                key="sent"
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                className="text-center py-4"
              >
                <div className="w-16 h-16 rounded-full gradient-primary shadow-glow-primary flex items-center justify-center mx-auto mb-5">
                  <CheckCircle2 className="w-8 h-8 text-primary-foreground" />
                </div>
                <h2 className="text-xl font-bold text-foreground mb-3">تحقّق من بريدك</h2>
                <p className="text-sm text-muted-foreground leading-relaxed mb-2">
                  أرسلنا رابط إعادة تعيين كلمة المرور إلى:
                </p>
                <p className="text-sm font-medium text-foreground mb-6 break-all" dir="ltr">{email}</p>
                <p className="text-xs text-muted-foreground mb-8 leading-relaxed max-w-xs mx-auto">
                  انقر على الرابط الموجود في البريد. الرابط صالح لمدة ساعة واحدة.
                  تحقّق من مجلد الرسائل غير المرغوب إن لم تجده.
                </p>
                <button
                  onClick={() => { setSent(false); setEmail("") }}
                  className="text-sm text-primary hover:underline underline-offset-2 block mx-auto mb-4"
                >
                  تجربة بريد إلكتروني آخر
                </button>
                <Link href="/login" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
                  <ChevronLeft className="w-3.5 h-3.5" />
                  العودة لتسجيل الدخول
                </Link>
              </motion.div>
            ) : (

              /* ── Form ────────────────────────────────────────────── */
              <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <div className="text-center mb-7">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4">
                    <Mail className="w-6 h-6 text-primary" />
                  </div>
                  <h2 className="text-2xl font-bold text-foreground mb-1.5">نسيت كلمة المرور؟</h2>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    أدخل بريدك الإلكتروني وسنرسل لك رابط إعادة التعيين
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                  <div className="space-y-1.5">
                    <label htmlFor="email" className="text-sm font-medium text-foreground">
                      البريد الإلكتروني
                    </label>
                    <div className="relative">
                      <Mail className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                      <input
                        id="email"
                        type="email"
                        autoComplete="email"
                        placeholder="you@example.com"
                        dir="ltr"
                        value={email}
                        onChange={e => { setEmail(e.target.value); setError("") }}
                        className={`w-full pr-10 pl-4 py-3 rounded-2xl text-sm bg-input border transition-colors outline-none
                          focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground
                          ${error ? "border-destructive focus:border-destructive focus:ring-destructive/20" : "border-border/60"}`}
                      />
                    </div>
                    <AnimatePresence>
                      {error && (
                        <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                          className="text-xs text-destructive">{error}</motion.p>
                      )}
                    </AnimatePresence>
                  </div>

                  <motion.button
                    whileHover={{ scale: loading ? 1 : 1.015 }}
                    whileTap={{   scale: loading ? 1 : 0.985 }}
                    type="submit"
                    disabled={loading}
                    className="w-full py-3.5 rounded-2xl text-sm font-semibold text-primary-foreground gradient-primary shadow-glow-primary hover:opacity-90 transition-opacity disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                        جارٍ الإرسال...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        إرسال رابط الاسترداد
                      </>
                    )}
                  </motion.button>
                </form>

                <div className="mt-6 text-center">
                  <Link href="/login" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
                    <ChevronLeft className="w-4 h-4" />
                    العودة لتسجيل الدخول
                  </Link>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  )
}
