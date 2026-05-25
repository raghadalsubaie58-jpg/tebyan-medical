"use client"

export default function ComparePage() {
  return (
    <div className="flex flex-col h-screen bg-background" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 glass-strong border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-muted-foreground/40" />
            <span className="text-muted-foreground text-sm font-medium">الحالي</span>
          </div>
          <span className="text-muted-foreground/40 text-xs">vs</span>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-primary" />
            <span className="text-primary text-sm font-medium">المقترح ✨</span>
          </div>
        </div>
        <span className="text-muted-foreground text-sm">مقارنة التحسينات</span>
      </div>

      {/* Split view */}
      <div className="flex flex-1 overflow-hidden">
        {/* Current */}
        <div className="flex-1 flex flex-col border-l border-border">
          <div className="text-center py-2 bg-muted/30 text-muted-foreground text-xs font-medium tracking-wider uppercase shrink-0">
            الحالي — localhost:3000
          </div>
          <iframe
            src="http://localhost:3000"
            className="flex-1 w-full border-none"
            title="current"
          />
        </div>

        {/* Divider */}
        <div className="w-px bg-border shrink-0" />

        {/* Improved */}
        <div className="flex-1 flex flex-col">
          <div className="text-center py-2 bg-primary/8 text-primary text-xs font-medium tracking-wider uppercase shrink-0">
            المقترح — localhost:3000/preview
          </div>
          <iframe
            src="http://localhost:3000/preview"
            className="flex-1 w-full border-none"
            title="improved"
          />
        </div>
      </div>
    </div>
  )
}
