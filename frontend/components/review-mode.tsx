"use client"

import React, {
  createContext, useContext, useState, useRef, useEffect, useCallback,
} from "react"
import { motion, AnimatePresence } from "framer-motion"

// ══════════════════════════════════════════════════════════════
//  DATA
// ══════════════════════════════════════════════════════════════

type Category = "fix" | "improvement" | "responsive"

interface Change {
  id:        number
  component: string
  area:      string
  title:     string
  problem:   string
  before:    string[]
  after:     string[]
  uxImpact:  string
  category:  Category
}

const CAT: Record<Category, { badge: string; ring: string; label: string }> = {
  fix:         { badge: "bg-destructive",                  ring: "ring-destructive/60",  label: "إصلاح"    },
  improvement: { badge: "bg-primary",                      ring: "ring-primary/60",      label: "تحسين"    },
  responsive:  { badge: "bg-[oklch(0.62_0.18_280)]",       ring: "ring-[oklch(0.62_0.18_280)]/60", label: "استجابة" },
}

export const CHANGES: Change[] = [
  {
    id: 1,
    component: "ChatBot",
    area: "منطقة الرسائل",
    title: "توسيع مساحة المحادثة",
    problem: "منطقة الرسائل h-56 (224px) تعرض 5-6 رسائل فقط وتجبر على التمرير المستمر",
    before: ["📦 ارتفاع: h-56  =  224px", "يظهر 5-6 رسائل", "تمرير مستمر ومرهق"],
    after:  ["📦 ارتفاع: h-72  =  288px", "يظهر 8-9 رسائل", "محادثة أطول بلا تمرير"],
    uxImpact: "المستخدم يقرأ المحادثة كاملة دون تمرير مستمر — تجربة أكثر سلاسة",
    category: "improvement",
  },
  {
    id: 2,
    component: "ChatBot",
    area: "عرض اللوحة والزر",
    title: "توسيع لوحة المحادثة",
    problem: "عرض اللوحة 320px كان يضغط النصوص العربية الطويلة على سطرين دون داعٍ",
    before: ["عرض: w-[320px]", "النص العربي مضغوط", "max-w ضيق على الشاشات الصغيرة"],
    after:  ["عرض: w-[340px]", "تنفس أفضل للنصوص", "max-w أوسع على الجوال"],
    uxImpact: "قراءة أراح للغة العربية ذات الأحرف الطويلة والمتصلة",
    category: "improvement",
  },
  {
    id: 3,
    component: "ChatBot",
    area: "حقل الإدخال",
    title: "إضافة Focus Ring للإدخال",
    problem: "النقر على حقل الكتابة لم يُظهر أي مؤشر بصري — إشكالية Accessibility وضعف UX",
    before: ["لا يوجد حد عند التركيز", "المستخدم لا يعرف: هل الحقل نشط؟", "مشكلة في معايير a11y"],
    after:  ["ring-1 ring-primary/40 يظهر عند التركيز", "مؤشر بصري واضح وأنيق", "متوافق مع WCAG"],
    uxImpact: "المستخدم يعرف دائماً أين يكتب — مهم خصوصاً في الوضع النهاري الفاتح",
    category: "fix",
  },
  {
    id: 4,
    component: "Upload Section",
    area: "حالة الخطأ",
    title: "زر إعادة المحاولة عند فشل الرفع",
    problem: "عند فشل رفع الملف كان يظهر نص الخطأ فقط — المستخدم مجبور على تحديث الصفحة",
    before: ["❌ نص الخطأ فقط", "لا خيار للمتابعة", "تجربة محبطة ومقطوعة"],
    after:  ["❌ نص الخطأ واضح", "🔄 زر 'إعادة المحاولة'", "الملف يُعاد رفعه بنقرة واحدة"],
    uxImpact: "تحويل لحظة الإحباط إلى تجربة قابلة للتعافي — الحفاظ على جلسة المستخدم",
    category: "fix",
  },
  {
    id: 5,
    component: "Risk Dashboard",
    area: "حالة الخطأ",
    title: "زر إعادة المحاولة في تقرير المخاطر",
    problem: "فشل تحميل تقرير المخاطر لم يمنح المستخدم خياراً للمحاولة مجدداً",
    before: ["❌ رسالة خطأ في مربع أحمر", "لا إمكانية إعادة التحميل", "المستخدم عالق"],
    after:  ["❌ رسالة الخطأ", "🔄 زر 'إعادة المحاولة' بنفس المربع", "إعادة اتصال فورية بالخادم"],
    uxImpact: "تجربة مقاومة للأخطاء — المستخدم لا يشعر بعجز أو حاجة لتحديث الصفحة",
    category: "fix",
  },
  {
    id: 6,
    component: "Voice Recorder",
    area: "ألوان الأزرار",
    title: "استبدال الألوان الثابتة بمتغيرات CSS",
    problem: "red-500 و blue-500 ثابتة تتعارض مع نظام الألوان في الوضع الداكن والفاتح",
    before: ["bg-red-500  (ثابت، لا يتكيف)", "text-blue-500  (ثابت، يبدو غريباً)", "Dark Mode: يبدو منفصلاً"],
    after:  ["bg-destructive  (CSS token)", "text-primary  (CSS token)", "Dark/Light: تناسق كامل"],
    uxImpact: "تناسق بصري تام في كلا الوضعين — لا ألوان طافية تبدو خارج النظام",
    category: "improvement",
  },
  {
    id: 7,
    component: "Compare Analyses",
    area: "جدول المقارنة",
    title: "تحسين الـ Grid للجوال",
    problem: "الجدول يستخدم 160px×2 ثابتة — على جوال 360px يتجاوز العرض ويحدث تمرير أفقي",
    before: ["grid-cols-[1fr_160px_160px]", "الأعمدة: 320px ثابتة", "↔ تمرير أفقي على الجوال"],
    after:  ["sm: [1fr_160px_160px]", "mobile: [1fr_100px_100px]", "لا تمرير أفقي على 360px+"],
    uxImpact: "المستخدم على الجوال يرى المقارنة كاملة بلا تمرير أفقي محبط",
    category: "responsive",
  },
  {
    id: 8,
    component: "Results Page",
    area: "زر تصدير PDF",
    title: "تفعيل زر الطباعة / PDF",
    problem: "زر 'تصدير PDF' كان موجوداً بصرياً لكن onClick لم يكن مربوطاً — ينقر المستخدم ولا شيء يحدث",
    before: ["زر PDF بتصميم جميل", "onClick = undefined (معطل)", "ميزة وعد بها ولم تُنجز"],
    after:  ["onClick={handlePrint}", "window.print() بعد 300ms delay", "نافذة طباعة المتصفح تفتح فوراً"],
    uxImpact: "ميزة كانت ميتة أصبحت تعمل — المستخدم يحفظ تقريره كـ PDF بنقرة واحدة",
    category: "fix",
  },
]

// ══════════════════════════════════════════════════════════════
//  CONTEXT
// ══════════════════════════════════════════════════════════════

interface ReviewCtx {
  active:    boolean
  currentId: number | null
  toggle:    () => void
  select:    (id: number | null) => void
}

const ReviewContext = createContext<ReviewCtx>({
  active: false, currentId: null, toggle: () => {}, select: () => {},
})

export function useReviewMode() { return useContext(ReviewContext) }

// ══════════════════════════════════════════════════════════════
//  PROVIDER
// ══════════════════════════════════════════════════════════════

export function ReviewModeProvider({ children }: { children: React.ReactNode }) {
  const [active,    setActiveState] = useState(false)
  const [currentId, setCurrentId]   = useState<number | null>(null)

  const toggle = useCallback(() => {
    setActiveState(v => !v)
    setCurrentId(null)
  }, [])

  const select = useCallback((id: number | null) => setCurrentId(id), [])

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "R") {
        e.preventDefault()
        setActiveState(v => !v)
        setCurrentId(null)
      }
      if (!active) return
      if (e.key === "Escape") { setActiveState(false); setCurrentId(null) }
      if (e.key === "ArrowLeft") {
        setCurrentId(prev => {
          const idx = prev ? CHANGES.findIndex(c => c.id === prev) : -1
          return idx < CHANGES.length - 1 ? CHANGES[idx + 1].id : prev
        })
      }
      if (e.key === "ArrowRight") {
        setCurrentId(prev => {
          const idx = prev ? CHANGES.findIndex(c => c.id === prev) : CHANGES.length
          return idx > 0 ? CHANGES[idx - 1].id : prev
        })
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [active])

  return (
    <ReviewContext.Provider value={{ active, currentId, toggle, select }}>
      {children}
      <ReviewFloatingButton />
      <ReviewPanel />
    </ReviewContext.Provider>
  )
}

// ══════════════════════════════════════════════════════════════
//  FLOATING TOGGLE BUTTON
// ══════════════════════════════════════════════════════════════

function ReviewFloatingButton() {
  const { active, toggle } = useReviewMode()
  return (
    <motion.button
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 2 }}
      onClick={toggle}
      className={[
        "fixed top-20 left-4 z-[200] flex items-center gap-2 px-3.5 py-2 rounded-full",
        "text-xs font-bold shadow-lg border transition-all duration-300 select-none",
        active
          ? "bg-foreground text-background border-foreground/20"
          : "bg-card text-muted-foreground border-border hover:text-foreground hover:border-primary/40",
      ].join(" ")}
      title="Ctrl+Shift+R"
    >
      <span className="text-sm">{active ? "✕" : "🔍"}</span>
      <span>{active ? "إيقاف المراجعة" : "وضع المراجعة"}</span>
      {!active && (
        <span className="w-5 h-5 rounded-full bg-primary/15 text-primary text-[10px] font-black flex items-center justify-center">
          {CHANGES.length}
        </span>
      )}
      {active && (
        <motion.span
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="w-2 h-2 rounded-full bg-primary"
        />
      )}
    </motion.button>
  )
}

// ══════════════════════════════════════════════════════════════
//  SIDE PANEL
// ══════════════════════════════════════════════════════════════

function ReviewPanel() {
  const { active, currentId, select } = useReviewMode()

  const idx = currentId ? CHANGES.findIndex(c => c.id === currentId) : -1

  const navigate = (dir: 1 | -1) => {
    const next = idx === -1 ? 0 : Math.max(0, Math.min(CHANGES.length - 1, idx + dir))
    select(CHANGES[next].id)
  }

  return (
    <AnimatePresence>
      {active && (
        <>
          {/* Backdrop (mobile only) */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[150] bg-black/20 sm:hidden"
            onClick={() => select(null)}
          />

          {/* Panel */}
          <motion.aside
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed top-0 left-0 h-full z-[190] w-80 flex flex-col bg-card border-r border-border shadow-2xl"
          >
            {/* Header */}
            <div className="px-5 pt-5 pb-4 border-b border-border shrink-0">
              <div className="flex items-center gap-3 mb-1">
                <span className="text-lg">🔍</span>
                <div>
                  <h2 className="text-sm font-bold text-foreground">وضع المراجعة المرئية</h2>
                  <p className="text-[10px] text-muted-foreground">Design Audit Mode</p>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-3">
                <div className="flex justify-between text-[10px] text-muted-foreground mb-1.5">
                  <span>{CHANGES.length} تحسين تم تطبيقه</span>
                  {currentId && <span>{idx + 1} / {CHANGES.length}</span>}
                </div>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-primary"
                    animate={{ width: currentId ? `${((idx + 1) / CHANGES.length) * 100}%` : "0%" }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>

              {/* Legend */}
              <div className="flex gap-3 mt-3">
                {(Object.entries(CAT) as [Category, typeof CAT[Category]][]).map(([key, cfg]) => (
                  <div key={key} className="flex items-center gap-1.5">
                    <div className={`w-2 h-2 rounded-full ${cfg.badge}`} />
                    <span className="text-[10px] text-muted-foreground">{cfg.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Changes list */}
            <div className="flex-1 overflow-y-auto py-3 px-3 space-y-2" style={{ scrollbarWidth: "thin" }}>
              {CHANGES.map((change, i) => {
                const cfg = CAT[change.category]
                const isActive = currentId === change.id
                return (
                  <motion.div
                    key={change.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                  >
                    <button
                      onClick={() => select(isActive ? null : change.id)}
                      className={[
                        "w-full text-right rounded-2xl border transition-all duration-200",
                        isActive
                          ? "bg-muted border-primary/30 shadow-sm"
                          : "bg-transparent border-border hover:bg-muted/50",
                      ].join(" ")}
                    >
                      <div className="flex items-start gap-2.5 p-3">
                        <div className={`w-6 h-6 rounded-full ${cfg.badge} text-white text-[11px] font-black flex items-center justify-center shrink-0 mt-0.5`}>
                          {change.id}
                        </div>
                        <div className="flex-1 min-w-0 text-right">
                          <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                            <span className="text-[9px] font-bold text-muted-foreground">{change.component}</span>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full text-white ${cfg.badge}`}>
                              {cfg.label}
                            </span>
                          </div>
                          <p className="text-[12px] font-semibold text-foreground leading-snug">{change.title}</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">{change.area}</p>
                        </div>
                      </div>

                      {/* Expanded details */}
                      <AnimatePresence initial={false}>
                        {isActive && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.22 }}
                            className="overflow-hidden"
                            onClick={e => e.stopPropagation()}
                          >
                            <div className="px-3 pb-3 space-y-2.5 border-t border-border/60 pt-3">
                              {/* Problem */}
                              <div className="rounded-xl bg-destructive/8 border border-destructive/15 p-2.5">
                                <p className="text-[9px] font-black text-destructive uppercase tracking-wider mb-1">المشكلة السابقة</p>
                                <p className="text-[10px] text-foreground/80 leading-relaxed">{change.problem}</p>
                              </div>

                              {/* Before / After */}
                              <div className="grid grid-cols-2 gap-2">
                                <div className="rounded-xl bg-muted border border-border p-2">
                                  <p className="text-[9px] font-black text-muted-foreground uppercase mb-1.5">قبل ❌</p>
                                  {change.before.map((line, j) => (
                                    <p key={j} className="text-[10px] text-foreground/60 leading-relaxed font-mono">{line}</p>
                                  ))}
                                </div>
                                <div className="rounded-xl bg-success/5 border border-success/20 p-2">
                                  <p className="text-[9px] font-black text-success uppercase mb-1.5">بعد ✅</p>
                                  {change.after.map((line, j) => (
                                    <p key={j} className="text-[10px] text-foreground/80 leading-relaxed font-mono">{line}</p>
                                  ))}
                                </div>
                              </div>

                              {/* UX Impact */}
                              <div className="rounded-xl bg-primary/5 border border-primary/20 p-2.5">
                                <p className="text-[9px] font-black text-primary uppercase tracking-wider mb-1">تأثير UX ✨</p>
                                <p className="text-[10px] text-foreground/80 leading-relaxed">{change.uxImpact}</p>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </button>
                  </motion.div>
                )
              })}
            </div>

            {/* Navigation footer */}
            <div className="px-4 py-3.5 border-t border-border shrink-0">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate(-1)}
                  disabled={idx <= 0 && currentId !== null}
                  className="flex-1 py-2 rounded-xl bg-muted text-xs font-bold text-foreground disabled:opacity-30 hover:bg-muted/70 transition-colors"
                >
                  → السابق
                </button>
                <button
                  onClick={() => currentId === null ? select(CHANGES[0].id) : navigate(1)}
                  disabled={idx >= CHANGES.length - 1}
                  className="flex-1 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-bold disabled:opacity-30 hover:bg-primary/90 transition-colors"
                >
                  {currentId === null ? "ابدأ الجولة ◀" : "التالي ←"}
                </button>
              </div>
              <p className="text-center text-[9px] text-muted-foreground mt-2">Ctrl+Shift+R  ·  ← → للتنقل  ·  Esc للإغلاق</p>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}

// ══════════════════════════════════════════════════════════════
//  HIGHLIGHT WRAPPER
// ══════════════════════════════════════════════════════════════

interface ReviewHighlightProps {
  changeId:  number
  children:  React.ReactNode
  className?: string
  style?:     React.CSSProperties
}

export function ReviewHighlight({ changeId, children, className = "", style }: ReviewHighlightProps) {
  const { active, currentId, select } = useReviewMode()
  const ref = useRef<HTMLDivElement>(null)

  const change    = CHANGES.find(c => c.id === changeId)
  const isActive  = active && currentId === changeId
  const isVisible = active

  // Scroll into view when activated
  useEffect(() => {
    if (isActive && ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [isActive])

  if (!change || !isVisible) return <div className={className} style={style}>{children}</div>

  const cfg = CAT[change.category]

  return (
    <div ref={ref} className={`relative ${className}`} style={{ ...style, scrollMarginTop: "120px" }}>
      {/* Animated ring */}
      <div
        className={[
          "absolute inset-0 rounded-[inherit] ring-2 pointer-events-none z-20 transition-all duration-300",
          cfg.ring,
          isActive ? "ring-offset-2" : "opacity-50",
        ].join(" ")}
        style={{ borderRadius: "inherit" }}
      />

      {/* Animated glow when active */}
      {isActive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute inset-0 rounded-[inherit] pointer-events-none z-20"
          style={{
            background: change.category === "fix"
              ? "oklch(0.62 0.21 25 / 0.06)"
              : change.category === "responsive"
              ? "oklch(0.62 0.18 280 / 0.06)"
              : "oklch(0.72 0.11 168 / 0.06)",
          }}
        />
      )}

      {/* Number badge — positioned INSIDE so it works inside overflow-hidden containers */}
      <motion.button
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.9 }}
        onClick={e => { e.stopPropagation(); select(currentId === changeId ? null : changeId) }}
        animate={{ scale: isActive ? 1.2 : 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
        className={[
          "absolute top-1.5 right-1.5 z-30 w-6 h-6 rounded-full text-white text-[11px] font-black",
          "flex items-center justify-center shadow-lg cursor-pointer",
          cfg.badge,
        ].join(" ")}
      >
        {changeId}
      </motion.button>

      {/* Tooltip label when active — below the badge, inside the element */}
      <AnimatePresence>
        {isActive && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.9 }}
            transition={{ duration: 0.15 }}
            className="absolute top-9 right-1.5 z-40 px-3 py-1.5 rounded-xl text-[11px] font-bold text-white shadow-xl pointer-events-none max-w-[180px]"
            style={{ background: "oklch(0.12 0.01 210 / 0.95)" }}
          >
            ✦ {change.title}
          </motion.div>
        )}
      </AnimatePresence>

      {children}
    </div>
  )
}
