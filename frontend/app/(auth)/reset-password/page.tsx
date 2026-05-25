"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { Eye, EyeOff, Lock, Sparkles, ShieldCheck, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth-context"
import { createClient } from "@/lib/supabase"

export default function ResetPasswordPage() {
  const router            = useRouter()
  const { updatePassword } = useAuth()

  const [password,    setPassword]    = useState("")
  const [confirmPass, setConfirmPass] = useState("")
  const [showPass,    setShowPass]    = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading,     setLoading]     = useState(false)
  const [ready,       setReady]       = useState(false)   // recovery session confirmed
  const [done,        setDone]        = useState(false)
  const [fieldErr,    setFieldErr]    = useState<{ password?: string; confirmPass?: string }>({})

  // Supabase sets the recovery session via cookie (auth/confirm route handles verifyOtp).
  // We just need to verify the user is in a recovery session.
  useEffect(() => {
    const supabase = createClient()
    // Check if we have a valid session (set by /auth/confirm after verifyOtp)
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setReady(true)
      } else {
        // No session — maybe user landed here directly without the email link
        toast.error("رابط إعادة التعيين غير صالح أو منتهي الصلاحية")
        setTimeout(() => router.push("/forgot-password"), 2500)
      }
    })

    // Also listen for PASSWORD_RECOVERY event in case of hash-based flow
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") setReady(true)
    })
    return () => subscription.unsubscribe()
  }, [router])

  const passwordStrength = (() => {
    if (!password) return 0
    let s = 0
    if (password.length >= 8)           s++
    if (/[A-Z]/.test(password))         s++
    if (/[0-9]/.test(password))         s++
    if (/[^A-Za-z0-9]/.test(password)) s++
    return s
  })()

  const strengthLabel = ["", "ضعيفة", "متوسطة", "قوية", "قوية جداً"][passwordStrength]
  const strengthColor = ["", "bg-destructive", "bg-warning", "bg-success", "bg-success"][passwordStrength]

  const validate = () => {
    const err: typeof fieldErr = {}
    if (!password)             err.password    = "كلمة المرور مطلوبة"
    else if (password.length < 8) err.password = "8 أحرف على الأقل"
    if (!confirmPass)          err.confirmPass = "يرجى تأكيد كلمة المرور"
    else if (password !== confirmPass) err.confirmPass = "كلمتا المرور غير متطابقتين"
    setFieldErr(err)
    return !Object.keys(err).length
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    const { error } = await updatePassword(password)
    setLoading(false)

    if (error) {
      toast.error("تعذّر تحديث كلمة المرور — يرجى المحاولة مرة أخرى")
      return
    }

    setDone(true)
    setTimeout(() => router.push("/login?reset=1"), 2800)
  }

  // ── Success state ──────────────────────────────────────────────────────────
  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="glass-strong rounded-3xl p-10 shadow-2xl max-w-sm w-full text-center"
        >
          <div className="w-16 h-16 rounded-full gradient-primary shadow-glow-primary flex items-center justify-center mx-auto mb-5">
            <CheckCircle2 className="w-8 h-8 text-primary-foreground" />
          </div>
          <h2 className="text-xl font-bold text-foreground mb-3">تم تحديث كلمة المرور</h2>
          <p className="text-sm text-muted-foreground mb-2">
            يتم توجيهك لتسجيل الدخول...
          </p>
          <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto mt-4" />
        </motion.div>
      </div>
    )
  }

  // ── Loading/invalid session ────────────────────────────────────────────────
  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground">التحقق من الجلسة...</p>
        </div>
      </div>
    )
  }

  // ── Reset form ─────────────────────────────────────────────────────────────
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
          <div className="text-center mb-7">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4">
              <ShieldCheck className="w-6 h-6 text-primary" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-1.5">تعيين كلمة مرور جديدة</h2>
            <p className="text-sm text-muted-foreground">اختر كلمة مرور قوية لحماية حسابك</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>

            {/* New password */}
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium text-foreground">كلمة المرور الجديدة</label>
              <div className="relative">
                <Lock className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <input
                  id="password"
                  type={showPass ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => { setPassword(e.target.value); setFieldErr(p => ({ ...p, password: undefined })) }}
                  className={`w-full pr-10 pl-10 py-3 rounded-2xl text-sm bg-input border transition-colors outline-none
                    focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground
                    ${fieldErr.password ? "border-destructive focus:border-destructive focus:ring-destructive/20" : "border-border/60"}`}
                />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors">
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {/* Strength */}
              {password && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-1">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map(n => (
                      <div key={n} className={`h-1 flex-1 rounded-full transition-colors duration-300 ${n <= passwordStrength ? strengthColor : "bg-muted"}`} />
                    ))}
                  </div>
                  {strengthLabel && <p className="text-xs text-muted-foreground">القوة: <span className="font-medium text-foreground">{strengthLabel}</span></p>}
                </motion.div>
              )}
              <AnimatePresence>
                {fieldErr.password && (
                  <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="text-xs text-destructive">{fieldErr.password}</motion.p>
                )}
              </AnimatePresence>
            </div>

            {/* Confirm password */}
            <div className="space-y-1.5">
              <label htmlFor="confirmPass" className="text-sm font-medium text-foreground">تأكيد كلمة المرور</label>
              <div className="relative">
                <Lock className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <input
                  id="confirmPass"
                  type={showConfirm ? "text" : "password"}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  value={confirmPass}
                  onChange={e => { setConfirmPass(e.target.value); setFieldErr(p => ({ ...p, confirmPass: undefined })) }}
                  className={`w-full pr-10 pl-10 py-3 rounded-2xl text-sm bg-input border transition-colors outline-none
                    focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground
                    ${fieldErr.confirmPass ? "border-destructive focus:border-destructive focus:ring-destructive/20" : "border-border/60"}`}
                />
                <button type="button" onClick={() => setShowConfirm(v => !v)}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors">
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <AnimatePresence>
                {fieldErr.confirmPass && (
                  <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="text-xs text-destructive">{fieldErr.confirmPass}</motion.p>
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
                  جارٍ الحفظ...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  حفظ كلمة المرور الجديدة
                </>
              )}
            </motion.button>
          </form>
        </div>
      </motion.div>
    </div>
  )
}
