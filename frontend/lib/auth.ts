import type { NextAuthOptions } from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"
import GoogleProvider from "next-auth/providers/google"

export const authOptions: NextAuthOptions = {
  providers: [
    // Google OAuth — يحتاج GOOGLE_CLIENT_ID و GOOGLE_CLIENT_SECRET في .env.local
    ...(process.env.GOOGLE_CLIENT_ID
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID!,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
          }),
        ]
      : []),

    // بريد + كلمة مرور
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email:    { label: "البريد الإلكتروني", type: "email" },
        password: { label: "كلمة المرور",       type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null

        // يمكن ربط هذا بـ Supabase Auth لاحقاً
        // الآن: أي بريد + كلمة مرور تعمل (للتطوير)
        return {
          id:    credentials.email,
          email: credentials.email,
          name:  credentials.email.split("@")[0],
        }
      },
    }),
  ],

  session: { strategy: "jwt" },

  pages: { signIn: "/" },

  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id    = user.id
        token.email = user.email
        token.name  = user.name
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.email = token.email as string
        session.user.name  = token.name  as string
      }
      return session
    },
  },

  secret: process.env.NEXTAUTH_SECRET ?? "tebyan-dev-secret-change-in-production",
}
