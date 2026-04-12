import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/layout/Sidebar'

export const metadata: Metadata = {
  title: 'Hackazona — Industrial AI Platform',
  description: 'Industrial asset management and AI-powered monitoring',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-gradient-to-br from-[#0f1419] via-[#14191f] to-[#1a1f2e] text-white antialiased font-sans">
        <Sidebar />
        <main className="ml-56 min-h-screen">{children}</main>
      </body>
    </html>
  )
}
