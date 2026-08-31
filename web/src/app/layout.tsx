import './globals.css'
import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'AI Skill Benchmark Platform',
  description: 'AI Skill evaluation and benchmarking platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white">
        <nav className="bg-white border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex items-center">
                <Link href="/" className="text-xl font-bold text-primary">
                  AI Skill Eval
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link 
                  href="/" 
                  className="text-text-primary hover:text-primary px-3 py-2 text-sm font-medium"
                >
                  Search
                </Link>
                <Link 
                  href="/skills" 
                  className="text-text-primary hover:text-primary px-3 py-2 text-sm font-medium"
                >
                  Skills
                </Link>
                <Link 
                  href="/recommend" 
                  className="text-text-primary hover:text-primary px-3 py-2 text-sm font-medium"
                >
                  Recommend
                </Link>
                <Link 
                  href="/eval" 
                  className="bg-primary hover:bg-primary-hover text-white px-4 py-2 rounded-full text-sm font-medium transition-colors"
                >
                  Evaluate New Repo
                </Link>
              </div>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
