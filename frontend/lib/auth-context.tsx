"use client"

import { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react"
import type { User, Session, AuthError } from "@supabase/supabase-js"
import { createClient } from "./supabase"

interface AuthContextValue {
  user:           User | null
  session:        Session | null
  loading:        boolean
  signIn:         (email: string, password: string) => Promise<{ error: AuthError | null }>
  signUp:         (email: string, password: string, fullName: string) => Promise<{ error: AuthError | null; needsVerification: boolean }>
  signOut:        () => Promise<void>
  resetPassword:  (email: string) => Promise<{ error: AuthError | null }>
  updatePassword: (password: string) => Promise<{ error: AuthError | null }>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser]       = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  const supabase = useMemo(() => createClient(), [])

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_, session) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [supabase])

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error }
  }, [supabase])

  const signUp = useCallback(async (email: string, password: string, fullName: string) => {
    const origin = typeof window !== "undefined" ? window.location.origin : ""
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName || email.split("@")[0], avatar_url: null },
        emailRedirectTo: `${origin}/auth/confirm`,
      },
    })
    return { error, needsVerification: !error && !data.session }
  }, [supabase])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
  }, [supabase])

  const resetPassword = useCallback(async (email: string) => {
    const origin = typeof window !== "undefined" ? window.location.origin : ""
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${origin}/auth/confirm?next=/reset-password&type=recovery`,
    })
    return { error }
  }, [supabase])

  const updatePassword = useCallback(async (password: string) => {
    const { error } = await supabase.auth.updateUser({ password })
    return { error }
  }, [supabase])

  return (
    <AuthContext.Provider value={{ user, session, loading, signIn, signUp, signOut, resetPassword, updatePassword }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>")
  return ctx
}
