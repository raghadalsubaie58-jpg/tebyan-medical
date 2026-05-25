"use client"

import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { LogOut, User, Settings, ChevronDown } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { toast } from "sonner"

export function UserMenu() {
  const { user, signOut, loading } = useAuth()
  const [open, setOpen] = useState(false)
  const menuRef         = useRef<HTMLDivElement>(null)

  const displayName = user?.user_metadata?.full_name ?? user?.email?.split("@")[0] ?? "م"
  const initials    = displayName.slice(0, 2).toUpperCase()

  // Close when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  const handleSignOut = async () => {
    setOpen(false)
    await signOut()
    toast.success("تم تسجيل الخروج بنجاح")
  }

  // Skeleton while auth state is resolving
  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-muted/40 animate-pulse">
        <div className="w-7 h-7 rounded-full bg-muted" />
        <div className="w-16 h-3 rounded bg-muted" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="relative" ref={menuRef}>
      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-primary/10 hover:bg-primary/15 border border-primary/20 transition-colors"
        aria-expanded={open}
        aria-haspopup="true"
      >
        {/* Avatar */}
        <div className="w-7 h-7 rounded-full gradient-primary flex items-center justify-center text-xs font-bold text-primary-foreground shadow-glow-primary flex-shrink-0">
          {initials}
        </div>
        <span className="text-sm font-medium text-foreground max-w-[100px] truncate">{displayName}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className="absolute left-0 top-12 w-56 glass-strong rounded-2xl shadow-soft overflow-hidden z-50"
            style={{ border: "1px solid var(--border)" }}
          >
            {/* User info header */}
            <div className="px-4 py-3 border-b border-border/50 bg-muted/20">
              <p className="text-xs font-semibold text-foreground truncate">{displayName}</p>
              <p className="text-xs text-muted-foreground truncate mt-0.5" dir="ltr">{user.email}</p>
            </div>

            {/* Menu items */}
            <div className="p-1.5 space-y-0.5">
              <Link
                href="/profile"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-foreground hover:bg-primary/8 transition-colors group"
              >
                <User className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                الملف الشخصي
              </Link>
              <Link
                href="/settings"
                onClick={() => setOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-foreground hover:bg-primary/8 transition-colors group"
              >
                <Settings className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                الإعدادات
              </Link>
            </div>

            <div className="p-1.5 border-t border-border/50">
              <button
                onClick={handleSignOut}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-destructive hover:bg-destructive/8 transition-colors text-right"
              >
                <LogOut className="w-4 h-4" />
                تسجيل الخروج
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Compact version for mobile menu
export function MobileSignOut() {
  const { signOut } = useAuth()

  const handleSignOut = async () => {
    await signOut()
    toast.success("تم تسجيل الخروج")
  }

  return (
    <button
      onClick={handleSignOut}
      className="w-full text-right px-4 py-3 text-sm text-destructive rounded-xl hover:bg-destructive/8 transition-colors flex items-center gap-2"
    >
      <LogOut className="w-4 h-4" />
      تسجيل الخروج
    </button>
  )
}
