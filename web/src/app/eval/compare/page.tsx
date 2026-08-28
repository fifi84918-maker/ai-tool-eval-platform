'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'

// Tell Next.js this is a dynamic page
export const dynamic = 'force-dynamic'
export const fetchCache = 'force-no-store'
export const revalidate = 0

interface EvaluationDetail {
  id: number
  repo_url: string
  score_total: number
  grade: string
  metrics: {
    accuracy: number
    reliability: number
    security: number
    performance: number
  }
  findings: Array<{
    dimension: string
    severity: string
    message: string
  }>
  meta: {
    file_count: number
    language: string | null
    has_readme: boolean
    has_tests: boolean
    has_ci: boolean
    has_dockerfile: boolean
  }
  scanned_at: string
}

function CompareContent() {
  const searchParams = useSearchParams()
  const ids = searchParams.get('ids')
  
  const [evaluations, setEvaluations] = useState<EvaluationDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (ids) {
      loadComparison(ids)
    } else {
      setLoading(false)
    }
  }, [ids])

  const loadComparison = async (evalIds: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`/api/v1/eval/compare?ids=${evalIds}`)
      if (!response.ok) {
        throw new Error('加载对比失败')
      }
      const data = await response.json()
      setEvaluations(data.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : '发生错误')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-[#4E5969]">加载中...</div>
      </div>
    )
  }

  if (error || evaluations.length === 0) {
    return (
      <div className="max-w-7xl mx-auto p-8">
        <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8">
          <p className="text-[#F53F3F] mb-4">{error || '未找到评估记录'}</p>
          <Link href="/eval" className="text-[#165DFF] hover:text-[#4080FF]">
            ← 返回评估页面
          </Link>
        </div>
      </div>
    )
  }

  const dimensions = [
    { key: 'accuracy', label: '准确性', color: '#165DFF' },
    { key: 'reliability', label: '可靠性', color: '#00B42A' },
    { key: 'security', label: '安全性', color: '#FF7D00' },
    { key: 'performance', label: '性能', color: '#165DFF' }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-[#1D2129]">对比评估</h1>
          <Link
            href="/"
            className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
          >
            ← 返回首页
          </Link>
        </div>
      </div>

      {/* Repo Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {evaluations.map((evaluation) => (
          <div key={evaluation.id} className="bg-white rounded-2xl border border-[#E5E6EB] p-6 shadow-sm">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1 min-w-0 mr-3">
                <h3 className="text-sm font-medium text-[#4E5969] mb-2">仓库</h3>
                <p className="text-base font-semibold text-[#1D2129] break-all">
                  {evaluation.repo_url.replace('https://github.com/', '').replace('uploaded:', '上传: ')}
                </p>
              </div>
              <GradeBadge grade={evaluation.grade} />
            </div>
            
            <div className="mb-4">
              <h3 className="text-sm font-medium text-[#4E5969] mb-2">总分</h3>
              <p className="text-3xl font-bold text-[#165DFF]">
                {evaluation.score_total.toFixed(1)}
              </p>
            </div>

            <div className="text-xs text-[#86909C]">
              扫描时间: {new Date(evaluation.scanned_at).toLocaleString('zh-CN')}
            </div>
          </div>
        ))}
      </div>

      {/* Dimension Comparison */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-2xl font-bold text-[#1D2129] mb-6">维度对比</h2>
        
        <div className="space-y-8">
          {dimensions.map((dim) => (
            <div key={dim.key}>
              <h3 className="text-lg font-semibold text-[#1D2129] mb-4">{dim.label}</h3>
              <div className="space-y-3">
                {evaluations.map((evaluation) => (
                  <div key={evaluation.id} className="flex items-center gap-4">
                    <div className="w-32 text-sm text-[#4E5969] truncate">
                      {evaluation.repo_url.split('/').pop()?.replace('uploaded:', '')}
                    </div>
                    <div className="flex-1 flex items-center gap-3">
                      <div className="flex-1 bg-[#E5E6EB] rounded-full h-6 relative overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${evaluation.metrics[dim.key as keyof typeof evaluation.metrics]}%`,
                            backgroundColor: dim.color
                          }}
                        />
                      </div>
                      <div className="w-16 text-right text-lg font-bold" style={{ color: dim.color }}>
                        {evaluation.metrics[dim.key as keyof typeof evaluation.metrics].toFixed(1)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Findings */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-2xl font-bold text-[#1D2129] mb-6">安全发现</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {evaluations.map((evaluation) => (
            <div key={evaluation.id} className="space-y-3">
              <h3 className="font-semibold text-[#1D2129] truncate">
                {evaluation.repo_url.split('/').pop()?.replace('uploaded:', '')}
              </h3>
              
              {evaluation.findings.length === 0 ? (
                <p className="text-sm text-[#86909C]">✅ 未发现安全问题</p>
              ) : (
                <div className="space-y-2">
                  {evaluation.findings
                    .sort((a, b) => {
                      const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 }
                      return severityOrder[a.severity as keyof typeof severityOrder] - 
                             severityOrder[b.severity as keyof typeof severityOrder]
                    })
                    .map((finding, idx) => {
                      const severityEmoji = {
                        critical: '🔴',
                        high: '🟠',
                        medium: '🟡',
                        low: '🟢'
                      }[finding.severity] || 'ℹ️'
                      
                      return (
                        <div key={idx} className="text-sm">
                          <span className="mr-1">{severityEmoji}</span>
                          <span className="text-[#4E5969]">{finding.message}</span>
                        </div>
                      )
                    })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function ComparePage() {
  return <CompareContent />
}
