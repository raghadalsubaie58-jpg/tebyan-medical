import { type EmailOtpType } from "@supabase/supabase-js"
import { type NextRequest, NextResponse } from "next/server"
import { createServerClient } from "@supabase/ssr"
import { cookies } from "next/headers"

/**
 * Handles Supabase email link callbacks:
 *   - signup confirmation  → /login?verified=1
 *   - password recovery    → /reset-password
 *   - magic link           → /
 *   - error               → /login?error=invalid_link
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const token_hash = searchParams.get("token_hash")
  const type       = searchParams.get("type") as EmailOtpType | null
  const next       = searchParams.get("next") ?? "/"

  if (token_hash && type) {
    const cookieStore = await cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll: () => cookieStore.getAll(),
          setAll: (list) => list.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          ),
        },
      }
    )

    const { error } = await supabase.auth.verifyOtp({ type, token_hash })

    if (!error) {
      // Password recovery: session is now set, let user choose new password
      if (type === "recovery") {
        return NextResponse.redirect(`${origin}/reset-password`)
      }
      // Email signup confirmation
      if (type === "signup" || type === "email") {
        return NextResponse.redirect(`${origin}/login?verified=1`)
      }
      // Magic link or other types
      return NextResponse.redirect(`${origin}${next}`)
    }
  }

  return NextResponse.redirect(`${origin}/login?error=invalid_link`)
}
