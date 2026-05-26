"use client"

import { useState } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import {
  Eye, EyeOff, Mail, Lock, User as UserIcon,
  Sparkles, CheckCircle2, ChevronLeft, UserPlus,
} from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth-context"

const STEPS_BENEFITS = [
  "تحليل فوري لتقاريرك المخبرية",
  "شرح مبسّط لكل فحص",
  "حفظ سجلّك الطبي بأمان",
  "مقارنة التقارير عبر الزمن",
]

export default function RegisterPage() {
  const { signUp } = useAuth()

  const [fullName,     setFullName]     = useState("")
  const [email,        setEmail]        = useState("")
  const [password,     setPassword]     = useState("")
  const [confirmPass,  setConfirmPass]  = useState("")
  const [showPass,     setShowPass]     = useState(false)
  const [showConfirm,  setShowConfirm]  = useState(false)
  const [loading,      setLoading]      = useState(false)
  const [verified,     setVerified]     = useState(false)  // show email-sent state
  const [fieldErr,     setFieldErr]     = useState<Record<string, string>>({})

  const passwordStrength = (() => {
    if (!password) return 0
    let score = 0
    if (password.length >= 8)              score++
    if (/[A-Z]/.test(password))            score++
    if (/[0-9]/.test(password))            score++
    if (/[^A-Za-z0-9]/.test(password))    score++
    return score
  })()

  const strengthLabel = ["ضعيفة جداً", "ضعيفة", "متوسطة", "قوية", "قوية جداً"][passwordStrength]
  const strengthColor = ["bg-destructive", "bg-orange-500", "bg-warning", "bg-success", "bg-success"][passwordStrength]

  const validate = () => {
    const err: Record<string, string> = {}
    if (!fullName.trim())                                    err.fullName    = "الاسم مطلوب"
    if (!email)                                              err.email       = "البريد الإلكتروني مطلوب"
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))     err.email       = "صيغة البريد غير صحيحة"
    if (!password)                                           err.password    = "كلمة المرور مطلوبة"
    else if (password.length < 6)                            err.password    = "6 أحرف على الأقل"
    if (!confirmPass)                                        err.confirmPass = "يرجى تأكيد كلمة المرور"
    else if (password !== confirmPass)                       err.confirmPass = "كلمتا المرور غير متطابقتين"
    setFieldErr(err)
    return !Object.keys(err).length
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    const { error, needsVerification } = await signUp(email, password, fullName.trim())
    setLoading(false)

    if (error) {
      const msg = error.message.includes("already registered") ? "هذا البريد الإلكتروني مسجّل مسبقاً"
        : error.message.includes("Password should")            ? "كلمة المرور يجب أن تكون 6 أحرف على الأقل"
        : error.message
      toast.error(msg)
      return
    }

    if (needsVerification) {
      setVerified(true)
    } else {
      // Immediately logged in (email confirmation disabled)
      window.location.href = "/"
    }
  }

  const clearErr = (key: string) => setFieldErr(p => { const c = { ...p }; delete c[key]; return c })

  // ── Email sent state ──────────────────────────────────────────────────────
  if (verified) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1,    y: 0  }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="glass-strong rounded-3xl p-10 shadow-2xl max-w-sm w-full text-center"
        >
          <div className="w-16 h-16 rounded-full gradient-primary shadow-glow-primary flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-8 h-8 text-primary-foreground" />
          </div>
          <h2 className="text-xl font-bold text-foreground mb-3">تحقّق من بريدك</h2>
          <p className="text-sm text-muted-foreground leading-relaxed mb-2">
            أرسلنا رابط التفعيل إلى
          </p>
          <p className="text-sm font-medium text-foreground mb-6 break-all" dir="ltr">{email}</p>
          <p className="text-xs text-muted-foreground mb-8 leading-relaxed">
            افتح البريد وانقر على الرابط لتفعيل حسابك.
            تحقّق من مجلد الرسائل غير المرغوب إن لم تجده.
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 font-medium hover:underline underline-offset-2"
          >
            <ChevronLeft className="w-4 h-4" />
            العودة لتسجيل الدخول
          </Link>
        </motion.div>
      </div>
    )
  }

  // ── Registration form ─────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex">

      {/* Left panel: Benefits */}
      <motion.aside
        initial={{ opacity: 0, x: -32 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="hidden lg:flex lg:w-[44%] relative flex-col justify-between p-14 overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-primary/15 via-primary/5 to-transparent" />
        <div className="absolute bottom-0 left-0 w-80 h-80 rounded-full bg-primary/8 blur-3xl" />

        <div className="relative z-10">
          <Link href="/" className="inline-flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-glow-primary group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold text-foreground">تبيان الطبي</span>
          </Link>
        </div>

        <div className="relative z-10 space-y-10">
          <div className="space-y-4">
            <h1 className="text-4xl font-bold leading-snug text-foreground">
              انضم مجاناً
              <br />
              <span className="text-primary">وابدأ تحليلاتك</span>
            </h1>
            <p className="text-muted-foreground text-base leading-relaxed max-w-xs">
              حساب واحد يمنحك وصولاً كاملاً إلى أدوات التحليل الطبي الذكي
            </p>
          </div>

          <ul className="space-y-3">
            {STEPS_BENEFITS.map((text, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.35 + i * 0.08 }}
                className="flex items-center gap-3"
              >
                <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
                <span className="text-sm text-foreground/80">{text}</span>
              </motion.li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 text-xs text-muted-foreground/60">
          © 2025 تبيان الطبي — جميع الحقوق محفوظة
        </p>
      </motion.aside>

      {/* Right panel: Form */}
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
            <div className="text-center mb-7">
              <h2 className="text-2xl font-bold text-foreground mb-1.5">إنشاء حساب جديد</h2>
              <p className="text-sm text-muted-foreground">مجاناً — لا يتطلب بطاقة ائتمانية</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>

              {/* Full name */}
              <Field
                id="fullName" label="الاسم الكامل" placeholder="محمد العمري"
                icon={<UserIcon className="w-4 h-4" />}
                value={fullName} onChange={v => { setFullName(v); clearErr("fullName") }}
                error={fieldErr.fullName} type="text" autoComplete="name"
              />

              {/* Email */}
              <Field
                id="email" label="البريد الإلكتروني" placeholder="you@example.com"
                icon={<Mail className="w-4 h-4" />}
                value={email} onChange={v => { setEmail(v); clearErr("email") }}
                error={fieldErr.email} type="email" autoComplete="email" dir="ltr"
              />

              {/* Password */}
              <div className="space-y-1.5">
                <label htmlFor="password" className="text-sm font-medium text-foreground">كلمة المرور</label>
                <div className="relative">
                  <Lock className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  <input
                    id="password" type={showPass ? "text" : "password"}
                    autoComplete="new-password" placeholder="••••••••"
                    value={password}
                    onChange={e => { setPassword(e.target.value); clearErr("password") }}
                    className={inputCls(!!fieldErr.password)}
                  />
                  <button type="button" onClick={() => setShowPass(v => !v)}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    aria-label={showPass ? "إخفاء" : "إظهار"}>
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {/* Strength bar */}
                {password && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-1">
                    <div className="flex gap-1">
                      {[1, 2, 3, 4].map(n => (
                        <div key={n} className={`h-1 flex-1 rounded-full transition-colors duration-300 ${n <= passwordStrength ? strengthColor : "bg-muted"}`} />
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">قوة كلمة المرور: <span className="font-medium text-foreground">{strengthLabel}</span></p>
                  </motion.div>
                )}
                <FieldError msg={fieldErr.password} />
              </div>

              {/* Confirm password */}
              <div className="space-y-1.5">
                <label htmlFor="confirmPass" className="text-sm font-medium text-foreground">تأكيد كلمة المرور</label>
                <div className="relative">
                  <Lock className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  <input
                    id="confirmPass" type={showConfirm ? "text" : "password"}
                    autoComplete="new-password" placeholder="••••••••"
                    value={confirmPass}
                    onChange={e => { setConfirmPass(e.target.value); clearErr("confirmPass") }}
                    className={inputCls(!!fieldErr.confirmPass)}
                  />
                  <button type="button" onClick={() => setShowConfirm(v => !v)}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    aria-label={showConfirm ? "إخفاء" : "إظهار"}>
                    {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <FieldError msg={fieldErr.confirmPass} />
              </div>

              {/* Submit */}
              <motion.button
                whileHover={{ scale: loading ? 1 : 1.015 }}
                whileTap={{   scale: loading ? 1 : 0.985 }}
                type="submit" disabled={loading}
                className="w-full py-3.5 mt-1 rounded-2xl text-sm font-semibold text-primary-foreground gradient-primary shadow-glow-primary hover:opacity-90 transition-opacity disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    جارٍ إنشاء الحساب...
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    إنشاء الحساب
                  </>
                )}
              </motion.button>

              <p className="text-center text-xs text-muted-foreground">
                بالتسجيل توافق على{" "}
                <Link href="/privacy" className="text-foreground underline underline-offset-2 hover:text-primary">سياسة الخصوصية</Link>
              </p>
            </form>

            <div className="relative my-5">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border/50" /></div>
              <div className="relative flex justify-center"><span className="px-3 text-xs text-muted-foreground bg-card">أو</span></div>
            </div>

            <p className="text-center text-sm text-muted-foreground">
              لديك حساب بالفعل؟{" "}
              <Link href="/login" className="text-emerald-600 dark:text-emerald-400 font-medium hover:underline underline-offset-2">تسجيل الدخول</Link>
            </p>
          </div>

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

// ── Shared helpers ────────────────────────────────────────────────────────────

function inputCls(hasError: boolean) {
  return `w-full pr-10 pl-10 py-3 rounded-2xl text-sm bg-input border transition-colors outline-none
    focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground
    ${hasError ? "border-destructive focus:border-destructive focus:ring-destructive/20" : "border-border/60"}`
}

function FieldError({ msg }: { msg?: string }) {
  return (
    <AnimatePresence>
      {msg && (
        <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
          className="text-xs text-destructive">{msg}</motion.p>
      )}
    </AnimatePresence>
  )
}

function Field({ id, label, placeholder, icon, value, onChange, error, type = "text", autoComplete, dir }: {
  id: string; label: string; placeholder: string; icon: React.ReactNode
  value: string; onChange: (v: string) => void; error?: string
  type?: string; autoComplete?: string; dir?: string
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium text-foreground">{label}</label>
      <div className="relative">
        <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
          {icon}
        </span>
        <input
          id={id} type={type} placeholder={placeholder}
          autoComplete={autoComplete} dir={dir}
          value={value} onChange={e => onChange(e.target.value)}
          className={`w-full pr-10 pl-4 py-3 rounded-2xl text-sm bg-input border transition-colors outline-none
            focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground
            ${error ? "border-destructive focus:border-destructive focus:ring-destructive/20" : "border-border/60"}`}
        />
      </div>
      <FieldError msg={error} />
    </div>
  )
}
