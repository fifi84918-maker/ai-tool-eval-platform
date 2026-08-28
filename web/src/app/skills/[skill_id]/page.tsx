'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import ScoreBar from '@/components/skill/ScoreBar'

interface SkillDetail {
  summary: {
    skill_id: string
    canonical_name: string
    status: string
    evidence_grade: string
    source_kind: string
    origin_url: string
    description: string | null
    score_total?: number | null
    grade?: string | null
  }
  author: string | null
  license_spdx: string | null
  warnings: string[]
  declared_permissions: string[]
  json_ld: any | null
  // V1A Task 29.4.3: PRD 19.3 extended fields
  evidence_grade_detail?: string
  applicable_scenarios?: string[]
  not_applicable_scenarios?: string[]
  compatibility_status?: string
  compatibility_notes?: string
  static_findings?: Array<{
    dimension: string
    level: string
    message: string
  }>
  failure_cases?: string[]
  test_env?: {
    model?: string
    host?: string
    os?: string
  }
  source_platforms?: string[]
  // Future: dimension scores when available
  metrics?: {
    accuracy?: number
    reliability?: number
    security?: number
    performance?: number
  }
  findings?: Array<{
    dimension: string
    severity: string
    message: string
  }>
  scanned_at?: string
}

interface BundleSummary {
  bundle_id: string
  name: string
  description: string
  category: string
}

interface BundleListResponse {
  items: BundleSummary[]
  total: number
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export default function SkillDetailPage({
  params,
}: {
  params: { skill_id: string }
}) {
  const [skill, setSkill] = useState<SkillDetail | null>(null)
  const [bundles, setBundles] = useState<BundleSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [bundlesLoading, setBundlesLoading] = useState(false)

  useEffect(() => {
    loadSkill()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.skill_id])

  const loadSkill = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/v1/skills/${params.skill_id}`)
      
      if (!response.ok) {
        setSkill(null)
        setLoading(false)
        return
      }
      
      const data = await response.json()
      setSkill(data)
      
      // Load bundles containing this skill
      loadBundles(params.skill_id)
    } catch (error) {
      console.error('Failed to fetch skill:', error)
      setSkill(null)
    } finally {
      setLoading(false)
    }
  }

  const loadBundles = async (skillId: string) => {
    setBundlesLoading(true)
    try {
      const response = await fetch(`/api/v1/bundles/by-skill/${skillId}`)
      
      if (response.ok) {
        const data: BundleListResponse = await response.json()
        setBundles(data.items || [])
      }
    } catch (error) {
      console.error('Failed to fetch bundles:', error)
    } finally {
      setBundlesLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-12 shadow-sm text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#165DFF] border-t-transparent"></div>
        <p className="mt-4 text-[#4E5969]">加载中...</p>
      </div>
    )
  }

  if (!skill) {
    return (
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-[#F53F3F]">Skill Not Found</h1>
        <p className="mt-2 text-[#4E5969]">
          The requested skill ID does not exist.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-[#1D2129]">
                {skill.summary.canonical_name}
              </h1>
              <GradeBadge grade={skill.summary.grade} />
            </div>
            <p className="text-sm text-[#86909C] font-mono">
              {skill.summary.skill_id}
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <span className={`px-3 py-1 text-xs font-medium rounded-full ${
              skill.summary.status === 'NEUTRAL_TESTED' ? 'bg-[#00B42A]/10 text-[#00B42A]' :
              'bg-[#86909C]/10 text-[#86909C]'
            }`}>
              {skill.summary.status}
            </span>
            <span className="px-3 py-1 text-xs font-medium rounded-full bg-[#165DFF]/10 text-[#165DFF]">
              Evidence: {skill.summary.evidence_grade}
            </span>
          </div>
        </div>

        {skill.summary.score_total !== null && skill.summary.score_total !== undefined && (
          <div className="mb-8 p-6 bg-[#F5F7FA] rounded-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-[#4E5969]">综合评分</h3>
              <span className="text-5xl font-bold text-[#165DFF]">
                {skill.summary.score_total.toFixed(1)}
              </span>
            </div>
            <ScoreBar score={skill.summary.score_total} />
            {skill.scanned_at && (
              <p className="text-xs text-[#86909C] mt-3">
                评测时间: {new Date(skill.scanned_at).toLocaleString('zh-CN')}
              </p>
            )}
          </div>
        )}

        {/* Dimension Scores (if available) */}
        {skill.metrics && Object.keys(skill.metrics).length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[#1D2129]">维度评分</h3>
              <Link
                href="/scoring"
                className="text-sm text-[#165DFF] hover:text-[#4080FF] font-medium"
              >
                了解评分体系 →
              </Link>
            </div>
            <div className="space-y-4">
              {skill.metrics.accuracy !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">准确性 Accuracy</span>
                    <span className="text-lg font-bold text-[#165DFF]">{skill.metrics.accuracy.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#165DFF] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.accuracy}%` }}
                    />
                  </div>
                </div>
              )}

              {skill.metrics.reliability !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">可靠性 Reliability</span>
                    <span className="text-lg font-bold text-[#00B42A]">{skill.metrics.reliability.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#00B42A] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.reliability}%` }}
                    />
                  </div>
                </div>
              )}

              {skill.metrics.security !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">安全性 Security</span>
                    <span className="text-lg font-bold text-[#FF7D00]">{skill.metrics.security.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#FF7D00] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.security}%` }}
                    />
                  </div>
                </div>
              )}

              {skill.metrics.performance !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">性能 Performance</span>
                    <span className="text-lg font-bold text-[#722ED1]">{skill.metrics.performance.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#722ED1] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.performance}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Findings (if available) */}
        {skill.findings && skill.findings.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">发现问题</h3>
            <div className="space-y-3">
              {skill.findings.map((finding, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border ${
                    finding.severity === 'high' || finding.severity === 'critical'
                      ? 'bg-[#F53F3F]/5 border-[#F53F3F]/20'
                      : finding.severity === 'medium'
                      ? 'bg-[#FF7D00]/5 border-[#FF7D00]/20'
                      : 'bg-[#86909C]/5 border-[#86909C]/20'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg">
                      {finding.severity === 'high' || finding.severity === 'critical' ? '🔴' :
                       finding.severity === 'medium' ? '🟡' : '⚪'}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                          finding.severity === 'high' || finding.severity === 'critical'
                            ? 'bg-[#F53F3F] text-white'
                            : finding.severity === 'medium'
                            ? 'bg-[#FF7D00] text-white'
                            : 'bg-[#86909C] text-white'
                        }`}>
                          {finding.severity.toUpperCase()}
                        </span>
                        <span className="text-xs text-[#86909C]">{finding.dimension}</span>
                      </div>
                      <p className="text-sm text-[#1D2129]">{finding.message}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evaluate Button (for GitHub repos) */}
        {skill.summary.origin_url.includes('github.com') && (
          <div className="mb-8 p-6 bg-gradient-to-r from-[#165DFF]/5 to-[#722ED1]/5 rounded-2xl border border-[#165DFF]/20">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-[#1D2129] mb-1">获取详细评分</h3>
                <p className="text-sm text-[#4E5969]">
                  评估此 Skill 的 GitHub 仓库，获取维度分数、代码质量分析和安全发现
                </p>
              </div>
              <Link
                href={`/eval?url=${encodeURIComponent(skill.summary.origin_url)}`}
                className="px-6 py-3 bg-[#165DFF] text-white rounded-full hover:bg-[#4080FF] transition-colors font-medium whitespace-nowrap"
              >
                立即评估 →
              </Link>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-6 mt-6">
          <div>
            <h3 className="text-sm font-medium text-[#4E5969]">Source</h3>
            <p className="mt-1 text-[#1D2129]">{skill.summary.source_kind}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-[#4E5969]">Author</h3>
            <p className="mt-1 text-[#1D2129]">{skill.author || 'Unknown'}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-[#4E5969]">License</h3>
            <p className="mt-1 text-[#1D2129]">{skill.license_spdx || 'Unknown'}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-[#4E5969]">Origin</h3>
            <a 
              href={skill.summary.origin_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="mt-1 text-[#165DFF] hover:text-[#4080FF] block"
            >
              View Source →
            </a>
          </div>
        </div>

        {skill.summary.description && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-[#4E5969]">Description</h3>
            <p className="mt-1 text-[#1D2129]">{skill.summary.description}</p>
          </div>
        )}

        {skill.warnings && skill.warnings.length > 0 && (
          <div className="mt-6 p-4 bg-[#FF7D00]/10 rounded-xl">
            <h3 className="text-sm font-medium text-[#FF7D00] mb-2">Warnings</h3>
            <ul className="space-y-1">
              {skill.warnings.map((warning, idx) => (
                <li key={idx} className="text-sm text-[#FF7D00]">
                  • {warning}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* V1A Task 29.4.3: PRD 19.3 Extended Fields */}
        
        {/* A. Evidence Grade + Test Environment */}
        {skill.evidence_grade_detail && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">证据等级</h3>
            <div className="flex items-center gap-4 flex-wrap">
              <span className={`px-4 py-2 text-sm font-medium rounded-full ${
                skill.evidence_grade_detail === 'A' ? 'bg-[#22c55e] text-white' :
                skill.evidence_grade_detail === 'B' ? 'bg-[#3b82f6] text-white' :
                skill.evidence_grade_detail === 'C' ? 'bg-[#eab308] text-white' :
                skill.evidence_grade_detail === 'D' ? 'bg-[#6b7280] text-white' :
                skill.evidence_grade_detail === 'U' ? 'bg-[#ef4444] text-white' :
                'bg-[#86909C] text-white'
              }`}>
                Grade {skill.evidence_grade_detail}
              </span>
              {skill.test_env && (
                <div className="text-sm text-[#4E5969]">
                  {skill.test_env.model && <span className="mr-3">Model: {skill.test_env.model}</span>}
                  {skill.test_env.host && <span className="mr-3">Host: {skill.test_env.host}</span>}
                  {skill.test_env.os && <span>OS: {skill.test_env.os}</span>}
                </div>
              )}
            </div>
          </div>
        )}

        {/* B. Applicable / Not Applicable Scenarios */}
        {((skill.applicable_scenarios && skill.applicable_scenarios.length > 0) || 
          (skill.not_applicable_scenarios && skill.not_applicable_scenarios.length > 0)) && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">适用场景</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {skill.applicable_scenarios && skill.applicable_scenarios.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-[#00B42A] mb-3">✓ 适用于</h4>
                  <ul className="space-y-2">
                    {skill.applicable_scenarios.map((scenario, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-[#1D2129]">
                        <span className="text-[#00B42A] mt-0.5">✓</span>
                        <span>{scenario}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {skill.not_applicable_scenarios && skill.not_applicable_scenarios.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-[#F53F3F] mb-3">✗ 不适用于</h4>
                  <ul className="space-y-2">
                    {skill.not_applicable_scenarios.map((scenario, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-[#1D2129]">
                        <span className="text-[#F53F3F] mt-0.5">✗</span>
                        <span>{scenario}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* C. Platform Compatibility */}
        {skill.compatibility_status && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">平台兼容性</h3>
            <div>
              <span className={`inline-block px-4 py-2 text-sm font-medium rounded-full ${
                skill.compatibility_status === 'Native' ? 'bg-[#00B42A] text-white' :
                skill.compatibility_status === 'Compatible' ? 'bg-[#3b82f6] text-white' :
                skill.compatibility_status === 'Adaptable' ? 'bg-[#eab308] text-white' :
                skill.compatibility_status === 'Partial' ? 'bg-[#FF7D00] text-white' :
                skill.compatibility_status === 'Blocked' ? 'bg-[#F53F3F] text-white' :
                'bg-[#86909C] text-white'
              }`}>
                {skill.compatibility_status}
              </span>
              {skill.compatibility_notes && (
                <p className="mt-3 text-sm text-[#4E5969]">{skill.compatibility_notes}</p>
              )}
            </div>
          </div>
        )}

        {/* D. Static Check Findings */}
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-[#1D2129] mb-4">静态检测结果</h3>
          {skill.static_findings && skill.static_findings.length > 0 ? (
            <div className="space-y-3">
              {skill.static_findings.map((finding, idx) => (
                <div key={idx} className="flex items-start gap-4 p-4 bg-[#F5F7FA] rounded-xl">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-sm font-medium text-[#1D2129]">{finding.dimension}</span>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                        finding.level === 'pass' ? 'bg-[#00B42A] text-white' :
                        finding.level === 'warning' ? 'bg-[#FF7D00] text-white' :
                        finding.level === 'block' ? 'bg-[#F53F3F] text-white' :
                        'bg-[#86909C] text-white'
                      }`}>
                        {finding.level.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm text-[#4E5969]">{finding.message}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#86909C]">暂无静态检测结果</p>
          )}
        </div>

        {/* E. Failure Cases */}
        {skill.failure_cases && skill.failure_cases.length > 0 && (
          <div className="mt-8">
            <details className="group">
              <summary className="cursor-pointer list-none">
                <div className="flex items-center justify-between p-4 bg-[#F5F7FA] rounded-xl hover:bg-[#E5E6EB] transition-colors">
                  <h3 className="text-lg font-semibold text-[#1D2129]">已知失败案例 ({skill.failure_cases.length})</h3>
                  <svg className="w-5 h-5 text-[#4E5969] group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </summary>
              <div className="mt-3 space-y-2">
                {skill.failure_cases.map((failureCase, idx) => (
                  <div key={idx} className="flex items-start gap-2 p-3 bg-[#F53F3F]/5 border border-[#F53F3F]/20 rounded-lg">
                    <span className="text-[#F53F3F] mt-0.5">•</span>
                    <p className="text-sm text-[#1D2129] flex-1">{failureCase}</p>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}

        {/* F. Source Platforms (at bottom of main card) */}
        {skill.source_platforms && skill.source_platforms.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[#E5E6EB]">
            <h4 className="text-sm font-medium text-[#4E5969] mb-3">来源平台</h4>
            <div className="flex flex-wrap gap-2">
              {skill.source_platforms.map((platform, idx) => (
                <span key={idx} className="px-3 py-1 text-xs font-medium bg-[#86909C]/10 text-[#86909C] rounded-full">
                  {platform}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bundle Recommendations Section */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-lg font-semibold text-[#1D2129] mb-4">
          📦 包含在以下套装中
        </h2>

        {bundlesLoading && (
          <div className="text-center py-6">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#165DFF] border-t-transparent"></div>
            <p className="mt-2 text-sm text-[#4E5969]">加载套装信息...</p>
          </div>
        )}

        {!bundlesLoading && bundles.length === 0 && (
          <p className="text-sm text-[#86909C] py-2">
            暂无套装包含此技能
          </p>
        )}

        {!bundlesLoading && bundles.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {bundles.slice(0, 3).map((bundle) => (
              <Link
                key={bundle.bundle_id}
                href={`/bundles/${bundle.bundle_id}`}
                className="block p-5 border border-[#E5E6EB] rounded-xl hover:border-[#165DFF] hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-base font-semibold text-[#1D2129] flex-1">
                    {bundle.name}
                  </h3>
                  <span className="text-xl ml-2">📦</span>
                </div>
                <p className="text-sm text-[#4E5969] mb-3 line-clamp-1">
                  {bundle.description}
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2 py-1 rounded bg-[#165DFF]/10 text-[#165DFF] font-medium">
                    {bundle.category}
                  </span>
                  <span className="text-sm text-[#165DFF] font-medium">
                    查看详情 →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}

        {!bundlesLoading && bundles.length > 3 && (
          <div className="mt-4 text-center">
            <Link
              href="/bundles"
              className="text-sm text-[#165DFF] hover:text-[#4080FF] font-medium"
            >
              查看全部套装 →
            </Link>
          </div>
        )}
      </div>

      {skill.json_ld && (
        <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
          <h2 className="text-lg font-semibold text-[#1D2129] mb-4">JSON-LD Structured Data</h2>
          <pre className="bg-[#F5F7FA] p-4 rounded-xl overflow-x-auto text-sm text-[#1D2129]">
            {JSON.stringify(skill.json_ld, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
