'use client'

import { useState } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import ScoreBar from '@/components/skill/ScoreBar'

interface EvalResult {
  repo_url: string
  metrics: {
    accuracy: number
    reliability: number
    security: number
    performance: number
  }
  score_total: number
  grade: string
  breakdown: {
    accuracy: number
    reliability: number
    security: number
    performance: number
  }
  scanned_at: string
}

export default function EvaluateRepoPage() {
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EvalResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleEvaluate = async () => {
    if (!repoUrl.trim()) {
      setError('Please enter a repository URL')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch('/api/v1/eval', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_url: repoUrl }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Evaluation failed')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold text-[#1D2129]">Evaluate New Repository</h1>
          <Link
            href="/"
            className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
          >
            ← Back to Skills
          </Link>
        </div>

        <p className="text-[#4E5969] mb-6">
          Enter a GitHub repository URL to analyze its quality and get a score.
        </p>

        <div className="flex gap-3">
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleEvaluate()}
            placeholder="https://github.com/owner/repo"
            className="flex-1 px-4 py-3 bg-white border border-[#E5E6EB] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#165DFF] focus:border-[#165DFF] text-[#1D2129]"
            disabled={loading}
          />
          <button
            onClick={handleEvaluate}
            disabled={loading}
            className="px-8 py-3 bg-[#165DFF] text-white rounded-full hover:bg-[#4080FF] disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {loading ? 'Evaluating...' : 'Evaluate'}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-4 bg-white border-2 border-[#F53F3F] rounded-xl">
            <p className="text-[#F53F3F] text-sm">{error}</p>
          </div>
        )}
      </div>

      {result && (
        <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-2xl font-bold text-[#1D2129]">Evaluation Result</h2>
              <GradeBadge grade={result.grade} />
            </div>
            <a
              href={result.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#165DFF] hover:text-[#4080FF] text-sm break-all"
            >
              {result.repo_url}
            </a>
          </div>

          <div className="mb-8 p-6 bg-[#F5F7FA] rounded-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-[#4E5969]">Overall Score</h3>
              <span className="text-5xl font-bold text-[#165DFF]">
                {result.score_total.toFixed(1)}
              </span>
            </div>
            <ScoreBar score={result.score_total} />
          </div>

          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">Dimension Breakdown</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-4 bg-[#F5F7FA] rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-[#1D2129]">Accuracy</span>
                  <span className="text-xl font-bold text-[#165DFF]">
                    {result.breakdown.accuracy.toFixed(1)}
                  </span>
                </div>
                <div className="bg-[#E5E6EB] rounded-full h-2">
                  <div
                    className="bg-[#165DFF] h-2 rounded-full"
                    style={{ width: `${(result.breakdown.accuracy / result.score_total) * 100}%` }}
                  />
                </div>
              </div>

              <div className="p-4 bg-[#F5F7FA] rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-[#1D2129]">Reliability</span>
                  <span className="text-xl font-bold text-[#00B42A]">
                    {result.breakdown.reliability.toFixed(1)}
                  </span>
                </div>
                <div className="bg-[#E5E6EB] rounded-full h-2">
                  <div
                    className="bg-[#00B42A] h-2 rounded-full"
                    style={{ width: `${(result.breakdown.reliability / result.score_total) * 100}%` }}
                  />
                </div>
              </div>

              <div className="p-4 bg-[#F5F7FA] rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-[#1D2129]">Security</span>
                  <span className="text-xl font-bold text-[#FF7D00]">
                    {result.breakdown.security.toFixed(1)}
                  </span>
                </div>
                <div className="bg-[#E5E6EB] rounded-full h-2">
                  <div
                    className="bg-[#FF7D00] h-2 rounded-full"
                    style={{ width: `${(result.breakdown.security / result.score_total) * 100}%` }}
                  />
                </div>
              </div>

              <div className="p-4 bg-[#F5F7FA] rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-[#1D2129]">Performance</span>
                  <span className="text-xl font-bold text-[#165DFF]">
                    {result.breakdown.performance.toFixed(1)}
                  </span>
                </div>
                <div className="bg-[#E5E6EB] rounded-full h-2">
                  <div
                    className="bg-[#165DFF] h-2 rounded-full"
                    style={{ width: `${(result.breakdown.performance / result.score_total) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-[#E5E6EB]">
            <p className="text-xs text-[#86909C]">
              Scanned at: {new Date(result.scanned_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
