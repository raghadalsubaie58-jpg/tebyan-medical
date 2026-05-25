"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Eye, EyeOff, X, CheckCircle2, LogIn, UserPlus } from "lucide-react"
import Link from "next/link"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth-context"

interface AuthModalProps {
  open:           boolean
  onOpenChange:   (open: boolean) => void
  defaultTab?:    "login" | "register"
  onSuccess?:     () => void
}

export function AuthModal({ open, onOpenChange, defaultTab = "login", onSuccess }: AuthModalProps) {
  const { signIn, signUp } = useAuth()

  const [tab,      setTab]      = useState<"login" | "register">(defaultTab)
  const [name,     setName]     = useState("")
  const [email,    setEmail]    = useState("")
  const [password, setPassword] = useState("")
  const [showPass, setShowPass] = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [verified, setVerified] = useState(false)

  const reset = () => {
    setName(""); setEmail(""); setPassword("")
    setShowPass(false); setLoading(false); setVerified(false)
  }

  const close = () => {
    reset()
    onOpenChange(false)
  }

  const handleTab = (t: "login" | "register") => {
    setTab(t); reset()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) { toast.error("يرجى ملء جميع الحقول"); return }
    if (password.length < 6) { toast.error("كلمة المرور يجب أن تكون 6 أحرف على الأقل"); return }

    setLoading(true)

    if (tab === "login") {
      const { error } = await signIn(email, password)
      setLoading(false)
      if (error) {
        toast.error(
          error.message.includes("Invalid login") ? "البريد أو كلمة المرور غير صحيحة"
          : error.message.includes("Email not confirmed") ? "يرجى تأكيد بريدك الإلكتروني أولاً"
          : "حدث خطأ، يرجى المحاولة"
        )
        return
      }
      toast.success("أهلاً وسهلاً!")
      close()
      onSuccess?.()
    } else {
      const { error, needsVerification } = await signUp(email, password, name)
      setLoading(false)
      if (error) {
        toast.error(error.message.includes("already registered") ? "هذا البريد مسجّل مسبقاً" : error.message)
        return
      }
      if (needsVerification) {
        setVerified(true)
      } else {
        toast.success("تم إنشاء الحساب!")
        close()
        onSuccess?.()
      }
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          style={{ background: "oklch(0 0 0 / 0.55)", backdropFilter: "blur(12px)" }}
          onClick={close}
        >
          <motion.div
            initial={{ scale: 0.92, opacity: 0, y: 20 }}
            animate={{ scale: 1,    opacity: 1, y: 0 }}
            exit={{ scale: 0.92, opacity: 0, y: 10 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            onClick={e => e.stopPropagation()}
            className="w-full max-w-sm glass-strong rounded-3xl overflow-hidden shadow-2xl"
            style={{ border: "1px solid var(--border)" }}
          >
            {/* Header */}
            <div className="px-7 pt-7 pb-5">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-xl font-bold text-foreground">
                  {verified ? "تحقّق من بريدك" : tab === "login" ? "مرحباً بعودتك" : "إنشاء حساب"}
                </h2>
                <button
                  onClick={close}
                  className="w-8 h-8 rounded-full bg-muted/60 flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors"
                  aria-label="إغلاق"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {!verified && (
                <div className="flex rounded-2xl p-1 mb-5 bg-muted/50">
                  {(["login", "register"] as const).map(t => (
                    <button
                      key={t}
                      onClick={() => handleTab(t)}
                      className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-1.5 ${
                        tab === t
                          ? "bg-card text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {t === "login" ? <><LogIn className="w-3.5 h-3.5" />دخول</> : <><UserPlus className="w-3.5 h-3.5" />تسجيل</>}
                    </button>
                  ))}
                </div>
              )}

              {/* Email verified state */}
              {verified ? (
                <div className="py-4 text-center space-y-4">
                  <div className="w-14 h-14 rounded-full gradient-primary shadow-glow-primary flex items-center justify-center mx-auto">
                    <CheckCircle2 className="w-7 h-7 text-primary-foreground" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground mb-1">تم إرسال رابط التفعيل إلى</p>
                    <p className="text-xs text-muted-foreground break-all" dir="ltr">{email}</p>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    تحقّق من بريدك وانقر على الرابط لتفعيل حسابك
                  </p>
                  <button onClick={close} className="text-xs text-primary hover:underline underline-offset-2">إغلاق</button>
                </div>
              ) : (

                /* Form */
                <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
                  {tab === "register" && (
                    <input
                      type="text"
                      placeholder="الاسم الكامل"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      className="w-full px-4 py-3 rounded-2xl text-sm text-foreground placeholder:text-muted-foreground bg-input border border-border/60 focus:border-ring focus:ring-2 focus:ring-ring/20 outline-none transition-colors"
                    />
                  )}

                  <input
                    type="email"
                    placeholder="البريد الإلكتروني"
                    dir="ltr"
                    autoComplete="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 rounded-2xl text-sm text-foreground placeholder:text-muted-foreground bg-input border border-border/60 focus:border-ring focus:ring-2 focus:ring-ring/20 outline-none transition-colors"
                  />

                  <div className="relative">
                    <input
                      type={showPass ? "text" : "password"}
                      placeholder="كلمة المرور"
                      autoComplete={tab === "login" ? "current-password" : "new-password"}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      required
                      minLength={6}
                      className="w-full px-4 pl-10 py-3 rounded-2xl text-sm text-foreground placeholder:text-muted-foreground bg-input border border-border/60 focus:border-ring focus:ring-2 focus:ring-ring/20 outline-none transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass(v => !v)}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={showPass ? "إخفاء" : "إظهار"}
                    >
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  {tab === "login" && (
                    <div className="text-left">
                      <Link
                        href="/forgot-password"
                        onClick={close}
                        className="text-xs text-primary hover:underline underline-offset-2"
                      >
                        نسيت كلمة المرور؟
                      </Link>
                    </div>
                  )}

                  <motion.button
                    whileHover={{ scale: loading ? 1 : 1.02 }}
                    whileTap={{ scale: loading ? 1 : 0.98 }}
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 rounded-2xl text-sm font-semibold text-primary-foreground gradient-primary shadow-glow-primary hover:opacity-90 transition-opacity disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                        جارٍ...
                      </>
                    ) : tab === "login" ? "تسجيل الدخول" : "إنشاء الحساب"}
                  </motion.button>
                </form>
              )}
            </div>

            {/* Footer */}
            {!verified && (
              <div className="px-7 py-4 bg-muted/20 border-t border-border/40 text-center">
                <p className="text-xs text-muted-foreground">
                  {tab === "login" ? (
                    <>
                      ليس لديك حساب؟{" "}
                      <button onClick={() => handleTab("register")} className="text-primary font-medium hover:underline underline-offset-2">
                        إنشاء حساب مجاني
                      </button>
                    </>
                  ) : (
                    <>
                      لديك حساب؟{" "}
                      <button onClick={() => handleTab("login")} className="text-primary font-medium hover:underline underline-offset-2">
                        تسجيل الدخول
                      </button>
                    </>
                  )}
                </p>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
