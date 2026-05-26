"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import {
  Eye, EyeOff, Mail, Lock, LogIn,
  Sparkles, ShieldCheck, Brain, Microscope, ChevronLeft,
} from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth-context"

const FEATURES = [
  { icon: Brain,       text: "تحليل ذكي للتقارير الطبية بدقة علمية" },
  { icon: ShieldCheck, text: "خصوصية تامة — بياناتك لا تُشارك أبداً" },
  { icon: Microscope,  text: "مرجعية طبية محدّثة لأكثر من 50 فحصاً" },
]

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show:   (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.45, ease: [0.22, 1, 0.36, 1] } }),
}

export default function LoginPage() {
  const router   = useRouter()
  const { signIn, loading: authLoading } = useAuth()

  const [email,        setEmail]        = useState("")
  const [password,     setPassword]     = useState("")
  const [showPass,     setShowPass]     = useState(false)
  const [loading,      setLoading]      = useState(false)
  const [fieldErr,     setFieldErr]     = useState<{ email?: string; password?: string }>({})

  // Show one-time messages from query string (verified, reset, error)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get("verified") === "1") toast.success("تم التحقق من بريدك الإلكتروني — يمكنك تسجيل الدخول الآن ✓")
    if (params.get("reset")    === "1") toast.success("تم تحديث كلمة المرور بنجاح ✓")
    if (params.get("error"))            toast.error("رابط التحقق غير صالح أو منتهي الصلاحية")
  }, [])

  const validate = () => {
    const err: typeof fieldErr = {}
    if (!email)                                          err.email    = "البريد الإلكتروني مطلوب"
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) err.email    = "صيغة البريد غير صحيحة"
    if (!password)                                       err.password = "كلمة المرور مطلوبة"
    else if (password.length < 6)                        err.password = "6 أحرف على الأقل"
    setFieldErr(err)
    return !Object.keys(err).length
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    const { error } = await signIn(email, password)
    setLoading(false)

    if (error) {
      const msg = error.message.includes("Invalid login") ? "البريد الإلكتروني أو كلمة المرور غير صحيحة"
        : error.message.includes("Email not confirmed")   ? "يرجى تأكيد بريدك الإلكتروني أولاً"
        : error.message.includes("Too many")              ? "محاولات كثيرة — يرجى الانتظار قليلاً"
        : "حدث خطأ، يرجى المحاولة مرة أخرى"
      toast.error(msg)
      return
    }

    const next = new URLSearchParams(window.location.search).get("next") || "/"
    router.push(next)
  }

  return (
    <div className="min-h-screen flex">

      {/* ── Left panel: Brand (desktop only) ─────────────────────────── */}
      <motion.aside
        initial={{ opacity: 0, x: -32 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="hidden lg:flex lg:w-[44%] relative flex-col justify-between p-14 overflow-hidden"
      >
        {/* Panel gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/15 via-primary/5 to-transparent" />
        <div className="absolute bottom-0 left-0 w-80 h-80 rounded-full bg-primary/8 blur-3xl" />

        {/* Logo */}
        <div className="relative z-10">
          <Link href="/" className="inline-flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-glow-primary group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold text-foreground">تبيان الطبي</span>
          </Link>
        </div>

        {/* Headline + features */}
        <div className="relative z-10 space-y-10">
          <div className="space-y-4">
            <h1 className="text-4xl font-bold leading-snug text-foreground">
              منصتك الطبية
              <br />
              <span className="text-primary">الذكية والموثوقة</span>
            </h1>
            <p className="text-muted-foreground text-base leading-relaxed max-w-xs">
              حلّل تقاريرك المخبرية بفهم عميق مدعوم بأحدث تقنيات الذكاء الاصطناعي الطبي
            </p>
          </div>

          <ul className="space-y-4">
            {FEATURES.map(({ icon: Icon, text }, i) => (
              <motion.li
                key={i}
                custom={i}
                initial="hidden"
                animate="show"
                variants={fadeUp}
                className="flex items-center gap-3"
              >
                <div className="w-9 h-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-4 h-4 text-primary" />
                </div>
                <span className="text-sm text-foreground/80">{text}</span>
              </motion.li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 text-xs text-muted-foreground/60">
          © 2025 تبيان الطبي — جميع الحقوق محفوظة
        </p>
      </motion.aside>

      {/* ── Right panel: Form ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 lg:p-12">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex justify-center mb-8">
            <Link href="/" className="inline-flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shadow-glow-primary">
                <Sparkles className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold text-foreground">تبيان الطبي</span>
            </Link>
          </div>

          {/* Glass card */}
          <div className="glass-strong rounded-3xl p-8 shadow-2xl shadow-black/10">

            {/* Header */}
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-foreground mb-1.5">مرحباً بعودتك</h2>
              <p className="text-sm text-muted-foreground">سجّل دخولك للوصول إلى تحاليلك الطبية</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>

              {/* Email */}
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
                    onChange={e => { setEmail(e.target.value); setFieldErr(p => ({ ...p, email: undefined })) }}
                    className={`w-full pr-10 pl-4 py-3 rounded-2xl text-sm bg-input border transition-colors outline-none
                      focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground
                      ${fieldErr.email ? "border-destructive focus:border-destructive focus:ring-destructive/20" : "border-border/60"}`}
                  />
                </div>
                <AnimatePresence>
                  {fieldErr.email && (
                    <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      className="text-xs text-destructive">
                      {fieldErr.email}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="text-sm font-medium text-foreground">كلمة المرور</label>
                  <Link href="/forgot-password" className="text-xs text-teal-800 dark:text-teal-300 hover:underline underline-offset-2 transition-colors">
                    نسيتِ كلمة المرور؟
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  <input
                    id="password"
                    type={showPass ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={password}
                    onChange={e => { setPassword(e.target.value); setFieldErr(p => ({ ...p, password: undefined })) }}
                    className={`w-full pr-10 pl-10 py-3 rounded-2xl text-sm bg-input border transition-colors outline-none
                      focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground
                      ${fieldErr.password ? "border-destructive focus:border-destructive focus:ring-destructive/20" : "border-border/60"}`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(v => !v)}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    aria-label={showPass ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
                  >
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <AnimatePresence>
                  {fieldErr.password && (
                    <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      className="text-xs text-destructive">
                      {fieldErr.password}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>

              {/* Submit */}
              <motion.button
                whileHover={{ scale: loading || authLoading ? 1 : 1.015 }}
                whileTap={{   scale: loading || authLoading ? 1 : 0.985 }}
                type="submit"
                disabled={loading || authLoading}
                className="w-full py-3.5 rounded-2xl text-sm font-semibold text-primary-foreground gradient-primary shadow-glow-primary hover:opacity-90 transition-opacity disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    جارٍ تسجيل الدخول...
                  </>
                ) : (
                  <>
                    <LogIn className="w-4 h-4" />
                    تسجيل الدخول
                  </>
                )}
              </motion.button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border/50" />
              </div>
              <div className="relative flex justify-center">
                <span className="px-3 text-xs text-muted-foreground bg-card">أو</span>
              </div>
            </div>

            {/* Register link */}
            <p className="text-center text-sm text-muted-foreground">
              ليس لديك حساب؟{" "}
              <Link href="/register" className="text-teal-800 dark:text-teal-300 font-medium hover:underline underline-offset-2">
                إنشاء حساب مجاني
              </Link>
            </p>
          </div>

          {/* Back to home */}
          <div className="text-center mt-6">
            <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <ChevronLeft className="w-3.5 h-3.5" />
              العودة إلى الصفحة الرئيسية
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
