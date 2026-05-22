"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"

interface FamilyProfileProps {
  activeProfile: string
  onChange:      (profile: string) => void
}

const PROFILES = ["أنا", "الزوج/الزوجة", "الأب", "الأم", "الابن", "البنت"]

export function FamilyProfile({ activeProfile, onChange }: FamilyProfileProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass text-sm font-medium text-foreground hover:bg-muted/60 transition-colors"
      >
        <span className="w-6 h-6 rounded-full gradient-primary flex items-center justify-center text-xs text-primary-foreground font-bold">
          {activeProfile[0]}
        </span>
        <span>{activeProfile}</span>
        <svg className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full mt-2 left-0 w-44 glass-strong rounded-2xl shadow-soft border border-border/40 overflow-hidden z-50"
          >
            <div className="p-1.5">
              <p className="text-xs text-muted-foreground px-2 py-1.5 font-medium">وضع العائلة</p>
              {PROFILES.map(p => (
                <button
                  key={p}
                  onClick={() => { onChange(p); setOpen(false) }}
                  className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-sm transition-colors text-right ${
                    activeProfile === p
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-foreground hover:bg-muted/50"
                  }`}
                >
                  <span className="w-6 h-6 rounded-full gradient-primary flex items-center justify-center text-xs text-primary-foreground font-bold shrink-0">
                    {p[0]}
                  </span>
                  {p}
                  {activeProfile === p && (
                    <svg className="w-3.5 h-3.5 mr-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
