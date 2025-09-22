import type { Metadata } from 'next'
import '../styles/globals.css'

export const metadata: Metadata = {
  title: '{{app_name}}',
  description: 'Generated application using VibesPro',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
