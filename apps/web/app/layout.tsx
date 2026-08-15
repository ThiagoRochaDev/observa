import type { ReactNode } from 'react'
import { DM_Sans } from 'next/font/google'
import { Shell } from '@/components/Shell'
import './globals.css'

const dmSans = DM_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-dm-sans',
})

export const metadata = {
  title: 'Observa',
  description: 'Connect clouds. Catalog products. See cost and health.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={dmSans.variable}>
      <body className={dmSans.className}>
        <Shell>{children}</Shell>
      </body>
    </html>
  )
}
