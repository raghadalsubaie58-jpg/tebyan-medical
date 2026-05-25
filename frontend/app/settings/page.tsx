"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { Settings, Bell, Moon, Globe, Trash2, ChevronRight, LogOut, AlertTriangle, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth-context"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"

export default function SettingsPage() {
  const { user, signOut } = useAuth()
  const router = useRouter()

  const [notifications, setNotifications] = useState(true)
  const [showDeleteConfirm, setShowDeleteConfirm]  = useState(false)
  const [deleteInput, setDeleteInput]              = useState("")
  const [signingOut, setSigningOut]                = useState(false)

  const handleSignOut = async () => {
    setSigningOut(true)
    await signOut()
    toast.success("تم تسجيل الخروج بنجاح")
    router.push("/")
  }

  const DELETE_CONFIRM_TEXT = "حذف حسابي"

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
            <h1 className="text-2xl font-bold text-foreground">الإعدادات</h1>
          </div>

          {/* Account */}
          <SettingsSection title="الحساب">
            <SettingsRow
              icon={<Settings className="w-4 h-4 text-primary" />}
              label="الملف الشخصي"
              description="تعديل الاسم وكلمة المرور"
              href="/profile"
            />
            <SettingsRow
              icon={<LogOut className="w-4 h-4 text-muted-foreground" />}
              label="تسجيل الخروج"
              description={`تسجيل الخروج من ${user?.email ?? "الحساب"}`}
              onClick={handleSignOut}
              loading={signingOut}
              danger={false}
            />
          </SettingsSection>

          {/* Preferences */}
          <SettingsSection title="التفضيلات">
            <div className="flex items-center justify-between px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Bell className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">الإشعارات</p>
                  <p className="text-xs text-muted-foreground mt-0.5">إشعارات نتائج التحليل</p>
                </div>
              </div>
              <button
                onClick={() => setNotifications(v => !v)}
                className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${notifications ? "gradient-primary" : "bg-muted"}`}
                role="switch"
                aria-checked={notifications}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${notifications ? "translate-x-[-1.375rem]" : "translate-x-[-0.25rem]"}`} />
              </button>
            </div>

            <div className="flex items-center gap-3 px-5 py-4 border-t border-border/40">
              <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
                <Globe className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">اللغة</p>
                <p className="text-xs text-muted-foreground mt-0.5">العربية — Arabic</p>
              </div>
            </div>
          </SettingsSection>

          {/* Danger zone */}
          <SettingsSection title="منطقة الخطر">
            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="w-full flex items-center gap-3 px-5 py-4 text-destructive hover:bg-destructive/5 transition-colors rounded-2xl"
              >
                <div className="w-8 h-8 rounded-xl bg-destructive/10 flex items-center justify-center flex-shrink-0">
                  <Trash2 className="w-4 h-4 text-destructive" />
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">حذف الحساب</p>
                  <p className="text-xs text-destructive/70 mt-0.5">حذف نهائي لجميع بياناتك</p>
                </div>
              </button>
            ) : (
              <AnimatePresence>
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="px-5 py-4 space-y-3"
                >
                  <div className="flex items-start gap-2 p-3 bg-destructive/10 rounded-xl">
                    <AlertTriangle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-destructive leading-relaxed">
                      هذا الإجراء لا يمكن التراجع عنه. سيتم حذف جميع بياناتك وتحاليلك بشكل نهائي.
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    اكتب <span className="font-mono font-bold text-foreground">{DELETE_CONFIRM_TEXT}</span> للتأكيد:
                  </p>
                  <input
                    type="text"
                    value={deleteInput}
                    onChange={e => setDeleteInput(e.target.value)}
                    placeholder={DELETE_CONFIRM_TEXT}
                    className="w-full px-4 py-2.5 rounded-xl bg-muted/40 border border-destructive/30 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-destructive/30 transition-all"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setShowDeleteConfirm(false); setDeleteInput("") }}
                      className="flex-1 py-2.5 rounded-xl bg-muted/40 text-sm font-medium text-foreground hover:bg-muted/60 transition-colors"
                    >
                      إلغاء
                    </button>
                    <button
                      disabled={deleteInput !== DELETE_CONFIRM_TEXT}
                      onClick={() => toast.info("لحذف الحساب يرجى التواصل مع الدعم")}
                      className="flex-1 py-2.5 rounded-xl bg-destructive text-destructive-foreground text-sm font-semibold disabled:opacity-40 transition-opacity"
                    >
                      حذف الحساب
                    </button>
                  </div>
                </motion.div>
              </AnimatePresence>
            )}
          </SettingsSection>

          {/* App info */}
          <div className="text-center text-xs text-muted-foreground pt-4 space-y-1">
            <p>تبيان الطبي — نسخة 1.0</p>
            <div className="flex items-center justify-center gap-3">
              <Link href="/privacy" className="hover:text-foreground transition-colors">سياسة الخصوصية</Link>
              <span>·</span>
              <a href="mailto:support@tibyan.health" className="hover:text-foreground transition-colors">الدعم الفني</a>
            </div>
          </div>
        </motion.div>
      </main>

      <Footer />
    </div>
  )
}

function SettingsSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass-strong rounded-3xl border border-border shadow-soft overflow-hidden">
      <div className="px-5 py-3 border-b border-border/50 bg-muted/10">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{title}</h3>
      </div>
      {children}
    </div>
  )
}

function SettingsRow({
  icon, label, description, href, onClick, loading, danger,
}: {
  icon: React.ReactNode
  label: string
  description?: string
  href?: string
  onClick?: () => void
  loading?: boolean
  danger?: boolean
}) {
  const cls = `w-full flex items-center justify-between px-5 py-4 transition-colors hover:bg-muted/20 ${danger ? "hover:bg-destructive/5" : ""}`
  const inner = (
    <>
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${danger ? "bg-destructive/10" : "bg-primary/10"}`}>
          {icon}
        </div>
        <div className="text-right">
          <p className={`text-sm font-medium ${danger ? "text-destructive" : "text-foreground"}`}>{label}</p>
          {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
        </div>
      </div>
      {loading ? (
        <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />
      ) : (
        <ChevronRight className="w-4 h-4 text-muted-foreground" />
      )}
    </>
  )

  if (href) return <Link href={href} className={cls}>{inner}</Link>
  return <button onClick={onClick} className={cls}>{inner}</button>
}
