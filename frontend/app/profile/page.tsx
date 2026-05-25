"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { motion } from "framer-motion"
import { User, Mail, Calendar, Lock, ChevronRight, Loader2, ShieldCheck } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth-context"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"

export default function ProfilePage() {
  const { user, updatePassword, signOut } = useAuth()
  const router = useRouter()

  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [newPassword, setNewPassword]           = useState("")
  const [confirmPassword, setConfirmPassword]   = useState("")
  const [saving, setSaving]                     = useState(false)

  const displayName = user?.user_metadata?.full_name ?? user?.email?.split("@")[0] ?? "المستخدم"
  const initials    = displayName.slice(0, 2).toUpperCase()
  const joinedAt    = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("ar-SA", { year: "numeric", month: "long", day: "numeric" })
    : "—"

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword.length < 8) { toast.error("كلمة المرور يجب أن تكون 8 أحرف على الأقل"); return }
    if (newPassword !== confirmPassword) { toast.error("كلمات المرور غير متطابقة"); return }
    setSaving(true)
    const { error } = await updatePassword(newPassword)
    setSaving(false)
    if (error) {
      toast.error(error.message)
    } else {
      toast.success("تم تغيير كلمة المرور بنجاح")
      setShowPasswordForm(false)
      setNewPassword("")
      setConfirmPassword("")
    }
  }

  return (
    <div className="min-h-screen" dir="rtl">
      <Header darkMode={false} toggleDark={() => {}} />

      <main className="container mx-auto px-4 py-16 max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-6"
        >
          {/* Page header */}
          <div className="flex items-center gap-3 mb-8">
            <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
              <ChevronRight className="w-5 h-5" />
            </Link>
            <h1 className="text-2xl font-bold text-foreground">الملف الشخصي</h1>
          </div>

          {/* Avatar card */}
          <div className="glass-strong rounded-3xl p-6 border border-border shadow-soft">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center text-xl font-bold text-primary-foreground shadow-glow-primary flex-shrink-0">
                {initials}
              </div>
              <div className="min-w-0">
                <h2 className="text-lg font-semibold text-foreground truncate">{displayName}</h2>
                <p className="text-sm text-muted-foreground truncate" dir="ltr">{user?.email}</p>
                <span className="inline-flex items-center gap-1 mt-1 text-xs text-success bg-success/10 px-2 py-0.5 rounded-full">
                  <ShieldCheck className="w-3 h-3" />
                  حساب موثّق
                </span>
              </div>
            </div>
          </div>

          {/* Info card */}
          <div className="glass-strong rounded-3xl border border-border shadow-soft overflow-hidden">
            <div className="px-6 py-4 border-b border-border/50 bg-muted/10">
              <h3 className="text-sm font-semibold text-foreground">معلومات الحساب</h3>
            </div>
            <div className="divide-y divide-border/40">
              <InfoRow icon={<User className="w-4 h-4" />} label="الاسم" value={displayName} />
              <InfoRow icon={<Mail className="w-4 h-4" />} label="البريد الإلكتروني" value={user?.email ?? "—"} ltr />
              <InfoRow icon={<Calendar className="w-4 h-4" />} label="تاريخ الانضمام" value={joinedAt} />
            </div>
          </div>

          {/* Change password */}
          <div className="glass-strong rounded-3xl border border-border shadow-soft overflow-hidden">
            <button
              onClick={() => setShowPasswordForm(v => !v)}
              className="w-full flex items-center justify-between px-6 py-4 hover:bg-muted/20 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Lock className="w-4 h-4 text-primary" />
                </div>
                <span className="text-sm font-medium text-foreground">تغيير كلمة المرور</span>
              </div>
              <ChevronRight className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${showPasswordForm ? "-rotate-90" : ""}`} />
            </button>

            {showPasswordForm && (
              <motion.form
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                onSubmit={handleChangePassword}
                className="px-6 pb-6 space-y-3 border-t border-border/50"
              >
                <div className="pt-4 space-y-3">
                  <input
                    type="password"
                    placeholder="كلمة المرور الجديدة"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    minLength={8}
                    required
                    className="w-full px-4 py-2.5 rounded-xl bg-muted/40 border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
                  />
                  <input
                    type="password"
                    placeholder="تأكيد كلمة المرور"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    minLength={8}
                    required
                    className="w-full px-4 py-2.5 rounded-xl bg-muted/40 border border-border text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all"
                  />
                  <button
                    type="submit"
                    disabled={saving}
                    className="w-full py-2.5 rounded-xl gradient-primary text-primary-foreground text-sm font-semibold disabled:opacity-50 flex items-center justify-center gap-2 shadow-glow-primary transition-opacity"
                  >
                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                    {saving ? "جاري الحفظ..." : "حفظ كلمة المرور"}
                  </button>
                </div>
              </motion.form>
            )}
          </div>
        </motion.div>
      </main>

      <Footer />
    </div>
  )
}

function InfoRow({ icon, label, value, ltr }: { icon: React.ReactNode; label: string; value: string; ltr?: boolean }) {
  return (
    <div className="flex items-center gap-4 px-6 py-3.5">
      <div className="w-8 h-8 rounded-xl bg-muted/40 flex items-center justify-center text-muted-foreground flex-shrink-0">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`text-sm font-medium text-foreground truncate mt-0.5 ${ltr ? "text-left" : ""}`} dir={ltr ? "ltr" : "rtl"}>
          {value}
        </p>
      </div>
    </div>
  )
}
