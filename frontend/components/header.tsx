"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import Image from "next/image"
import { useAuth } from "@/lib/auth-context"
import { UserMenu, MobileSignOut } from "@/components/auth/user-menu"
import { AuthModal } from "@/components/auth/auth-modal"

const navItems = [
  { label: "الرئيسية",     href: "#home" },
  { label: "التحليل",      href: "#analysis" },
  { label: "النتائج",      href: "#results" },
  { label: "سجل التحاليل", href: "#history" },
  { label: "حول المنصة",   href: "#about" },
]

interface HeaderProps {
  darkMode?:   boolean
  toggleDark?: () => void
}

export function Header({ darkMode, toggleDark }: HeaderProps) {
  const { user, loading } = useAuth()
  const [scrolled,        setScrolled]        = useState(false)
  const [mobileMenuOpen,  setMobileMenuOpen]  = useState(false)
  const [showAuthModal,   setShowAuthModal]   = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", onScroll)
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

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
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Image src="/logo.svg" alt="تبيان" width={52} height={52} className="object-contain drop-shadow-md" />
            </motion.div>
            <span className="text-2xl font-bold text-foreground">تبيان</span>
          </Link>

          {/* Desktop nav */}
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

          {/* Desktop auth controls */}
          <div className="hidden md:flex items-center gap-2">
            {/* Dark mode toggle */}
            {toggleDark && (
              <button
                onClick={toggleDark}
                className="w-9 h-9 rounded-xl glass flex items-center justify-center hover:bg-muted/50 transition-colors"
                aria-label="تبديل الوضع"
              >
                {darkMode
                  ? <svg className="w-4 h-4 text-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" /></svg>
                  : <svg className="w-4 h-4 text-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" /></svg>
                }
              </button>
            )}

            {/* Auth: loading → skeleton | user → menu | guest → login button */}
            {loading ? (
              <div className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-muted/40 animate-pulse">
                <div className="w-7 h-7 rounded-full bg-muted" />
                <div className="w-16 h-3 rounded bg-muted" />
              </div>
            ) : user ? (
              <UserMenu />
            ) : (
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowAuthModal(true)}
                className="px-5 py-2.5 rounded-2xl text-sm font-medium text-primary-foreground gradient-primary shadow-glow-primary hover:opacity-90 transition-opacity"
              >
                تسجيل الدخول
              </motion.button>
            )}
          </div>

          {/* Mobile menu button */}
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden w-10 h-10 rounded-xl glass flex items-center justify-center"
            aria-label="القائمة"
          >
            <div className="flex flex-col gap-1.5">
              <motion.span animate={{ rotate: mobileMenuOpen ? 45 : 0, y: mobileMenuOpen ? 6 : 0 }}   className="w-5 h-0.5 bg-foreground rounded-full origin-center" />
              <motion.span animate={{ opacity: mobileMenuOpen ? 0 : 1 }}                               className="w-5 h-0.5 bg-foreground rounded-full" />
              <motion.span animate={{ rotate: mobileMenuOpen ? -45 : 0, y: mobileMenuOpen ? -6 : 0 }} className="w-5 h-0.5 bg-foreground rounded-full origin-center" />
            </div>
          </motion.button>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="md:hidden glass-strong mt-2 mx-4 rounded-2xl overflow-hidden"
              style={{ border: "1px solid var(--border)" }}
            >
              <nav className="flex flex-col p-4">
                {navItems.map((item, index) => (
                  <motion.div key={item.href} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05 }}>
                    <Link
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className="block px-4 py-3 text-muted-foreground hover:text-foreground hover:bg-primary/10 rounded-xl transition-all duration-300"
                    >
                      {item.label}
                    </Link>
                  </motion.div>
                ))}

                <div className="mt-2 pt-2 border-t border-border flex flex-col gap-1">
                  {toggleDark && (
                    <button
                      onClick={toggleDark}
                      className="w-full text-right px-4 py-3 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-xl transition-colors"
                    >
                      {darkMode ? "الوضع النهاري ☀️" : "الوضع الليلي 🌙"}
                    </button>
                  )}

                  {user ? (
                    <MobileSignOut />
                  ) : (
                    <button
                      onClick={() => { setShowAuthModal(true); setMobileMenuOpen(false) }}
                      className="w-full text-right px-4 py-3 text-sm font-medium text-primary-foreground rounded-xl gradient-primary transition-opacity hover:opacity-90"
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

      {/* Auth modal — quick login from anywhere on the main page */}
      <AuthModal
        open={showAuthModal}
        onOpenChange={setShowAuthModal}
        onSuccess={() => setShowAuthModal(false)}
      />
    </>
  )
}
