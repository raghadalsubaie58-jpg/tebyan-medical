import type { Metadata, Viewport } from 'next'
import { Cairo, IBM_Plex_Sans_Arabic } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { Providers } from '@/components/providers'
import './globals.css'

const cairo = Cairo({
  subsets: ['arabic', 'latin'],
  weight: ['400', '600', '700'],
  variable: '--font-cairo',
  display: 'swap',
})

const ibmPlexArabic = IBM_Plex_Sans_Arabic({
  subsets: ['arabic', 'latin'],
  weight: ['400', '600'],
  variable: '--font-ibm-plex-arabic',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'تبيان | منصة الذكاء الاصطناعي الطبي',
  description: 'منصة تبيان الذكية لتحليل التقارير الطبية باستخدام الذكاء الاصطناعي - تبسيط المصطلحات الطبية وتقديم التوصيات الصحية',
  keywords: ['تبيان', 'ذكاء اصطناعي', 'تحليل طبي', 'تقارير طبية', 'صحة'],
}

export const viewport: Viewport = {
  themeColor: '#B8F3E4',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ar" dir="rtl" className="bg-background" suppressHydrationWarning>
      <body className={`${cairo.variable} ${ibmPlexArabic.variable} font-sans antialiased`}>
        {/* Anti-flash: apply saved theme before React hydration */}
        <script dangerouslySetInnerHTML={{__html: `(function(){try{var p=new URLSearchParams(window.location.search);if(p.get('theme')==='dark'||localStorage.getItem('tabyan-theme')==='dark')document.documentElement.classList.add('dark');}catch(e){}})();`}} />
        <Providers>{children}</Providers>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
