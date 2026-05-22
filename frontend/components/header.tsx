"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import Image from "next/image"
import { useAuth } from "@/lib/auth-context"
import { createClient } from "@/lib/supabase"

const navItems = [
  { label: "الرئيسية", href: "#home" },
  { label: "التحليل",  href: "#analysis" },
  { label: "النتائج",  href: "#results" },
  { label: "المساعدة", href: "#help" },
  { label: "حول المنصة", href: "#about" },
]

function LoginModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab]           = useState<"login" | "register">("login")
  const [name, setName]         = useState("")
  const [email, setEmail]       = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState("")
  const [success, setSuccess]   = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    setSuccess("")

    const supabase = createClient()

    if (tab === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      setLoading(false)
      if (error) setError("البريد أو كلمة المرور غير صحيحة")
      else onClose()
    } else {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: name || email.split("@")[0] },
        },
      })
      setLoading(false)
      if (error) setError(error.message)
      else setSuccess("تم إنشاء الحساب! تحقّقي من بريدك الإلكتروني لتفعيل الحساب.")
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.4)", backdropFilter: "blur(8px)" }}
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.92, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-3xl overflow-hidden"
        style={{
          background: "rgba(255,255,255,0.95)",
          backdropFilter: "blur(24px)",
          boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
        }}
      >
        <div className="px-7 pt-7 pb-4">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-[#111111]">
              {tab === "login" ? "تسجيل الدخول" : "إنشاء حساب"}
            </h2>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="flex rounded-2xl p-1 mb-6" style={{ background: "rgba(0,0,0,0.04)" }}>
            {(["login", "register"] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); setError(""); setSuccess("") }}
                className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  tab === t ? "bg-white text-[#111111] shadow-sm" : "text-gray-500"
                }`}
              >
                {t === "login" ? "دخول" : "تسجيل"}
              </button>
            ))}
          </div>

          {success ? (
            <div className="py-6 text-center space-y-3">
              <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto" style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #a8e8d8 100%)" }}>
                <svg className="w-7 h-7 text-green-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm text-[#111111] font-medium">{success}</p>
              <button onClick={onClose} className="text-xs text-gray-400 underline">إغلاق</button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {tab === "register" && (
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="الاسم (اختياري)"
                  className="w-full px-4 py-3 rounded-2xl text-sm text-[#111111] placeholder:text-gray-400 focus:outline-none"
                  style={{ background: "rgba(0,0,0,0.04)", border: "1px solid rgba(0,0,0,0.06)" }}
                />
              )}
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="البريد الإلكتروني"
                required
                className="w-full px-4 py-3 rounded-2xl text-sm text-[#111111] placeholder:text-gray-400 focus:outline-none"
                style={{ background: "rgba(0,0,0,0.04)", border: "1px solid rgba(0,0,0,0.06)" }}
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="كلمة المرور"
                required
                minLength={6}
                className="w-full px-4 py-3 rounded-2xl text-sm text-[#111111] placeholder:text-gray-400 focus:outline-none"
                style={{ background: "rgba(0,0,0,0.04)", border: "1px solid rgba(0,0,0,0.06)" }}
              />
              {error && <p className="text-red-500 text-xs text-center">{error}</p>}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-2xl text-sm font-semibold text-[#111111] transition-all disabled:opacity-60"
                style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #a8e8d8 100%)" }}
              >
                {loading ? "جاري..." : tab === "login" ? "دخول" : "إنشاء حساب"}
              </motion.button>
            </form>
          )}
        </div>

        <div className="px-7 py-4 text-center" style={{ background: "rgba(0,0,0,0.02)" }}>
          <p className="text-xs text-gray-400">
            بالدخول توافق على{" "}
            <span className="text-[#111111] underline cursor-pointer">سياسة الخصوصية</span>
          </p>
        </div>
      </motion.div>
    </motion.div>
  )
}

interface HeaderProps {
  extraActions?: React.ReactNode
}

export function Header({ extraActions }: HeaderProps) {
  const { user } = useAuth()
  const [scrolled, setScrolled]             = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [showLogin, setShowLogin]           = useState(false)
  const [showUserMenu, setShowUserMenu]     = useState(false)

  const displayName = user?.user_metadata?.full_name ?? user?.email?.split("@")[0] ?? "م"

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const handleSignOut = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    setShowUserMenu(false)
  }

  return (
    <>
      <motion.header
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          scrolled ? "glass-strong shadow-soft py-3" : "py-5"
        }`}
      >
        <div className="container mx-auto px-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Image src="/logo.png" alt="تبيان" width={52} height={52} className="object-contain drop-shadow-md" />
            </motion.div>
            <span className="text-2xl font-bold text-foreground">تبيان</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item, index) => (
              <motion.div
                key={item.href}
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
              >
                <Link
                  href={item.href}
                  className="relative px-5 py-2.5 text-muted-foreground hover:text-foreground transition-colors duration-300 rounded-xl group"
                >
                  <span className="relative z-10">{item.label}</span>
                  <motion.div className="absolute inset-0 rounded-xl bg-primary/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" layoutId="nav-hover" />
                </Link>
              </motion.div>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-2">
            {extraActions}
            {user ? (
              <div className="relative">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 px-3 py-2 rounded-2xl transition-colors"
                  style={{ background: "rgba(184,243,228,0.3)" }}
                >
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold text-[#111111]"
                    style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #FFD7EC 100%)" }}
                  >
                    {displayName[0]?.toUpperCase() ?? "م"}
                  </div>
                  <span className="text-sm font-medium text-foreground">{displayName}</span>
                </motion.button>

                <AnimatePresence>
                  {showUserMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: 8, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 8, scale: 0.96 }}
                      transition={{ duration: 0.15 }}
                      className="absolute left-0 top-12 w-48 rounded-2xl overflow-hidden shadow-lg z-50"
                      style={{ background: "rgba(255,255,255,0.96)", backdropFilter: "blur(20px)", border: "1px solid rgba(0,0,0,0.06)" }}
                    >
                      <div className="px-4 py-3 border-b border-gray-50">
                        <p className="text-xs font-medium text-[#111111]">{displayName}</p>
                        <p className="text-xs text-gray-400 truncate">{user.email}</p>
                      </div>
                      <button
                        onClick={handleSignOut}
                        className="w-full text-right px-4 py-3 text-sm text-red-500 hover:bg-red-50 transition-colors"
                      >
                        تسجيل الخروج
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowLogin(true)}
                className="px-5 py-2.5 rounded-2xl text-sm font-medium text-[#111111] transition-all"
                style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #a8e8d8 100%)" }}
              >
                تسجيل الدخول
              </motion.button>
            )}
          </div>

          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden w-10 h-10 rounded-xl glass flex items-center justify-center"
            aria-label="القائمة"
          >
            <div className="flex flex-col gap-1.5">
              <motion.span animate={{ rotate: mobileMenuOpen ? 45 : 0, y: mobileMenuOpen ? 6 : 0 }} className="w-5 h-0.5 bg-foreground rounded-full origin-center" />
              <motion.span animate={{ opacity: mobileMenuOpen ? 0 : 1 }} className="w-5 h-0.5 bg-foreground rounded-full" />
              <motion.span animate={{ rotate: mobileMenuOpen ? -45 : 0, y: mobileMenuOpen ? -6 : 0 }} className="w-5 h-0.5 bg-foreground rounded-full origin-center" />
            </div>
          </motion.button>
        </div>

        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="md:hidden glass-strong mt-2 mx-4 rounded-2xl overflow-hidden"
            >
              <nav className="flex flex-col p-4">
                {navItems.map((item, index) => (
                  <motion.div key={item.href} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05 }}>
                    <Link href={item.href} onClick={() => setMobileMenuOpen(false)} className="block px-4 py-3 text-muted-foreground hover:text-foreground hover:bg-primary/10 rounded-xl transition-all duration-300">
                      {item.label}
                    </Link>
                  </motion.div>
                ))}
                <div className="mt-2 pt-2 border-t border-border">
                  {user ? (
                    <button onClick={handleSignOut} className="w-full text-right px-4 py-3 text-sm text-red-500 rounded-xl hover:bg-red-50 transition-colors">
                      تسجيل الخروج
                    </button>
                  ) : (
                    <button
                      onClick={() => { setShowLogin(true); setMobileMenuOpen(false) }}
                      className="w-full text-right px-4 py-3 text-sm font-medium text-[#111111] rounded-xl transition-colors"
                      style={{ background: "linear-gradient(135deg, #B8F3E4 0%, #a8e8d8 100%)" }}
                    >
                      تسجيل الدخول
                    </button>
                  )}
                </div>
              </nav>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>

      <AnimatePresence>
        {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
      </AnimatePresence>
    </>
  )
}
