'use client'

import { useState } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import ScoreBar from '@/components/skill/ScoreBar'

interface EvalResult {
  repo_url?: string
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

interface BatchResult {
  repo_url: string
  score_total?: number
  grade?: string
  error?: string
}

export default function EvaluateRepoPage() {
  const [repoUrl, setRepoUrl] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [batchUrls, setBatchUrls] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EvalResult | null>(null)
  const [batchResults, setBatchResults] = useState<BatchResult[]>([])
  const [error, setError] = useState<string | null>(null)

  const handleEvaluateUrl = async () => {
    if (!repoUrl.trim()) {
      setError('请输入仓库 URL')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setBatchResults([])

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
        throw new Error(errorData.detail || '评估失败')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '发生错误')
    } finally {
      setLoading(false)
    }
  }

  const handleEvaluateZip = async () => {
    if (!selectedFile) {
      setError('请选择 ZIP 文件')
      return
    }

    if (!selectedFile.name.endsWith('.zip')) {
      setError('只支持 ZIP 文件')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setBatchResults([])

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch('/api/v1/eval/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '评估失败')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '发生错误')
    } finally {
      setLoading(false)
    }
  }

  const handleBatchEvaluate = async () => {
    const urls = batchUrls
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0)

    if (urls.length === 0) {
      setError('请输入至少一个仓库 URL')
      return
    }

    if (urls.length > 10) {
      setError('批量评估最多支持 10 个仓库')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setBatchResults([])

    try {
      const response = await fetch('/api/v1/eval/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_urls: urls }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '批量评估失败')
      }

      const data = await response.json()
      setBatchResults(data.results || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '发生错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold text-[#1D2129]">评估新仓库</h1>
          <Link
            href="/"
            className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
          >
            ← 返回技能列表
          </Link>
        </div>

        {/* GitHub URL 评估 */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-[#1D2129] mb-4">评估 GitHub 仓库</h2>
          <p className="text-[#4E5969] mb-4">
            输入 GitHub 仓库 URL，分析其质量并获得评分。
          </p>

          <div className="flex gap-3">
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !loading && handleEvaluateUrl()}
              placeholder="https://github.com/owner/repo"
              className="flex-1 px-4 py-3 bg-white border border-[#E5E6EB] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#165DFF] focus:border-[#165DFF] text-[#1D2129]"
              disabled={loading}
            />
            <button
              onClick={handleEvaluateUrl}
              disabled={loading}
              className="px-8 py-3 bg-[#165DFF] text-white rounded-full hover:bg-[#4080FF] disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loading ? '评估中...' : '开始评估'}
            </button>
          </div>
        </div>

        {/* 分隔线 */}
        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#E5E6EB]"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-white text-[#86909C]">或</span>
          </div>
        </div>

        {/* ZIP 文件上传 */}
        <div>
          <h2 className="text-lg font-semibold text-[#1D2129] mb-4">上传 ZIP 文件</h2>
          <p className="text-[#4E5969] mb-4">
            上传项目的 ZIP 压缩包进行评估（最大 50MB）。
          </p>

          <div className="flex gap-3">
            <div className="flex-1">
              <input
                type="file"
                accept=".zip"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="block w-full text-sm text-[#4E5969]
                  file:mr-4 file:py-3 file:px-6
                  file:rounded-full file:border-0
                  file:text-sm file:font-medium
                  file:bg-[#165DFF]/10 file:text-[#165DFF]
                  hover:file:bg-[#165DFF]/20
                  file:cursor-pointer cursor-pointer"
                disabled={loading}
              />
              {selectedFile && (
                <p className="mt-2 text-sm text-[#4E5969]">
                  已选择: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              )}
            </div>
            <button
              onClick={handleEvaluateZip}
              disabled={loading || !selectedFile}
              className="px-8 py-3 bg-[#165DFF] text-white rounded-full hover:bg-[#4080FF] disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loading ? '评估中...' : '开始评估'}
            </button>
          </div>
        </div>

        {/* 分隔线 */}
        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#E5E6EB]"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-white text-[#86909C]">或</span>
          </div>
        </div>

        {/* 批量评估 */}
        <div>
          <h2 className="text-lg font-semibold text-[#1D2129] mb-4">批量评估</h2>
          <p className="text-[#4E5969] mb-4">
            输入多个 GitHub 仓库 URL，每行一个，最多 10 个。
          </p>

          <div className="space-y-3">
            <textarea
              value={batchUrls}
              onChange={(e) => setBatchUrls(e.target.value)}
              placeholder="https://github.com/owner/repo1&#10;https://github.com/owner/repo2&#10;https://github.com/owner/repo3"
              rows={5}
              className="w-full px-4 py-3 bg-white border border-[#E5E6EB] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#165DFF] focus:border-[#165DFF] text-[#1D2129] font-mono text-sm"
              disabled={loading}
            />
            <button
              onClick={handleBatchEvaluate}
              disabled={loading || !batchUrls.trim()}
              className="w-full py-3 bg-[#165DFF] text-white rounded-xl hover:bg-[#4080FF] disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              {loading ? '批量评估中...' : '开始批量评估'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-6 p-4 bg-white border-2 border-[#F53F3F] rounded-xl">
            <p className="text-[#F53F3F] text-sm">{error}</p>
          </div>
        )}
      </div>

      {result && (
        <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <h2 className="text-2xl font-bold text-[#1D2129]">评估结果</h2>
              <GradeBadge grade={result.grade} />
            </div>
            {result.repo_url && (
              <a
                href={result.repo_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#165DFF] hover:text-[#4080FF] text-sm break-all"
              >
                {result.repo_url}
              </a>
            )}
          </div>

          <div className="mb-8 p-6 bg-[#F5F7FA] rounded-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-[#4E5969]">总体评分</h3>
              <span className="text-5xl font-bold text-[#165DFF]">
                {result.score_total.toFixed(1)}
              </span>
            </div>
            <ScoreBar score={result.score_total} />
          </div>

          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">维度明细</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-4 bg-[#F5F7FA] rounded-xl">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-[#1D2129]">准确性 Accuracy</span>
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
                  <span className="text-sm font-medium text-[#1D2129]">可靠性 Reliability</span>
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
                  <span className="text-sm font-medium text-[#1D2129]">安全性 Security</span>
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
                  <span className="text-sm font-medium text-[#1D2129]">性能 Performance</span>
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
              扫描时间: {new Date(result.scanned_at).toLocaleString('zh-CN')}
            </p>
          </div>
        </div>
      )}

      {batchResults.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
          <h2 className="text-2xl font-bold text-[#1D2129] mb-6">
            批量评估结果 ({batchResults.length})
          </h2>

          <div className="space-y-4">
            {batchResults.map((item, index) => (
              <div
                key={index}
                className="p-4 border border-[#E5E6EB] rounded-xl hover:border-[#165DFF] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 mr-4">
                    <p className="text-sm font-medium text-[#1D2129] truncate mb-1">
                      {item.repo_url.replace('https://github.com/', '')}
                    </p>
                    {item.error ? (
                      <p className="text-sm text-[#F53F3F]">❌ {item.error}</p>
                    ) : (
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-[#165DFF]">
                          {item.score_total?.toFixed(1)}
                        </span>
                        {item.grade && <GradeBadge grade={item.grade} />}
                      </div>
                    )}
                  </div>
                  {!item.error && (
                    <Link
                      href={item.repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#165DFF] hover:text-[#4080FF] text-sm whitespace-nowrap"
                    >
                      查看仓库 →
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-[#F5F7FA] rounded-xl">
            <p className="text-sm text-[#4E5969]">
              💡 提示：批量评估结果不会自动保存到历史记录，请单独评估重要仓库。
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
