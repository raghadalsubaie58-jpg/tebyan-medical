import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "تبيان الطبي — الحساب",
  description: "منصة الذكاء الاصطناعي لتحليل التقارير الطبية",
}

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen relative overflow-hidden bg-background">
      {/* Ambient gradient blobs */}
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 right-1/3 w-[500px] h-[500px] rounded-full bg-primary/8 blur-[100px]" />
        <div className="absolute top-1/2 -left-40 w-[400px] h-[400px] rounded-full bg-primary/6 blur-[80px]" />
        <div className="absolute -bottom-20 right-1/4 w-[350px] h-[350px] rounded-full bg-blue-500/5 blur-[80px]" />
        {/* Subtle dot grid */}
        <svg
          className="absolute inset-0 h-full w-full opacity-[0.025]"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <pattern id="auth-grid" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="1" fill="currentColor" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#auth-grid)" />
        </svg>
      </div>

      {children}
    </div>
  )
}
