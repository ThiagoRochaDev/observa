import type { ReactNode } from 'react'
import { Geist, Geist_Mono } from 'next/font/google'
import { ApiKeyGate } from '@/components/ApiKeyGate'
import { Shell } from '@/components/Shell'
import './globals.css'

const geist = Geist({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-geist',
})

const geistMono = Geist_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-geist-mono',
})

export const metadata = {
  title: 'Observa',
  description: 'Connect clouds. Catalog products. See cost and health.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" className={`${geist.variable} ${geistMono.variable}`}>
      <body className={geist.className}>
        <ApiKeyGate>
          <Shell>{children}</Shell>
        </ApiKeyGate>
      </body>
    </html>
  )
}
