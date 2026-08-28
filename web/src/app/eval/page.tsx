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
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">Evaluate New Repository</h1>
          <Link
            href="/"
            className="text-blue-600 hover:underline text-sm"
          >
            ← Back to Skills
          </Link>
        </div>

        <p className="text-gray-600 mb-6">
          Enter a GitHub repository URL to analyze its quality and get a score.
        </p>

        <div className="flex gap-2">
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleEvaluate()}
            placeholder="https://github.com/owner/repo"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            onClick={handleEvaluate}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Evaluating...' : 'Evaluate'}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}
      </div>

      {result && (
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-xl font-semibold">Evaluation Result</h2>
              <GradeBadge grade={result.grade} />
            </div>
            <a
              href={result.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-sm break-all"
            >
              {result.repo_url}
            </a>
          </div>

          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Overall Score</h3>
            <ScoreBar score={result.score_total} />
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Dimension Breakdown</h3>
            
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">Accuracy</span>
                <span className="text-sm font-medium text-gray-900">
                  {result.breakdown.accuracy.toFixed(1)}
                </span>
              </div>
              <div className="bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${(result.breakdown.accuracy / result.score_total) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">Reliability</span>
                <span className="text-sm font-medium text-gray-900">
                  {result.breakdown.reliability.toFixed(1)}
                </span>
              </div>
              <div className="bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${(result.breakdown.reliability / result.score_total) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">Security</span>
                <span className="text-sm font-medium text-gray-900">
                  {result.breakdown.security.toFixed(1)}
                </span>
              </div>
              <div className="bg-gray-200 rounded-full h-2">
                <div
                  className="bg-yellow-500 h-2 rounded-full"
                  style={{ width: `${(result.breakdown.security / result.score_total) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">Performance</span>
                <span className="text-sm font-medium text-gray-900">
                  {result.breakdown.performance.toFixed(1)}
                </span>
              </div>
              <div className="bg-gray-200 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full"
                  style={{ width: `${(result.breakdown.performance / result.score_total) * 100}%` }}
                />
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              Scanned at: {new Date(result.scanned_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
