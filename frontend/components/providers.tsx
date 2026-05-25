"use client"

import { AuthProvider } from "@/lib/auth-context"
import { Toaster } from "@/components/ui/sonner"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      {children}
      <Toaster
        position="top-center"
        richColors
        closeButton
        duration={4000}
        toastOptions={{
          style: { fontFamily: "var(--font-ibm-plex-arabic), var(--font-cairo), sans-serif" },
        }}
      />
    </AuthProvider>
  )
}
