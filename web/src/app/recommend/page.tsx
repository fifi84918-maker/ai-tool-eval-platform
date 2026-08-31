'use client'

import { useState } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'

// Types aligned with backend RecommendationResponse
interface RecommendedSkillOut {
  skill_id: string
  name: string
  grade: string | null
  score_total: number | null
  metrics?: Record<string, number>
}

interface RuleViolation {
  rule_id: string
  severity: string
  message: string
}

interface BundleRecommendationOut {
  bundle_id: string
  name: string
  tier: 'starter' | 'standard' | 'enterprise'
  description: string
  security_level: string
  highlights: string[]
  score: number
  match_reasons: string[]
  skills: RecommendedSkillOut[]
  rule_findings: RuleViolation[]
}

interface RecommendationResponse {
  profile_id: string | null
  profile_name: string | null
  total: number
  items: BundleRecommendationOut[]
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export default function RecommendPage() {
  const [projectName, setProjectName] = useState('')
  const [domains, setDomains] = useState<string[]>([])
  const [languages, setLanguages] = useState<string[]>([])
  const [securityRequirement, setSecurityRequirement] = useState<string>('standard')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null)

  // Available options
  const DOMAIN_OPTIONS = ['web', 'mobile', 'data-science', 'devops', 'security', 'documentation']
  const LANGUAGE_OPTIONS = ['javascript', 'python', 'java', 'go', 'rust', 'typescript']
  const SECURITY_OPTIONS = [
    { value: 'lax', label: '低（个人项目）' },
    { value: 'standard', label: '标准（团队项目）' },
    { value: 'strict', label: '高（企业级）' },
  ]

  const handleDomainToggle = (domain: string) => {
    setDomains(prev =>
      prev.includes(domain) ? prev.filter(d => d !== domain) : [...prev, domain]
    )
  }

  const handleLanguageToggle = (lang: string) => {
    setLanguages(prev =>
      prev.includes(lang) ? prev.filter(l => l !== lang) : [...prev, lang]
    )
  }

  const handleSubmit = async () => {
    if (!projectName || domains.length === 0 || languages.length === 0) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      const requestBody = {
        name: projectName,
        domains,
        languages,
        security_requirement: securityRequirement,
      }
      
      console.log('🚀 推荐请求体:', JSON.stringify(requestBody, null, 2))

      const response = await fetch(`${API_BASE_URL}/api/v1/recommend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error(`请求失败: ${response.status} ${response.statusText}`)
      }

      const data: RecommendationResponse = await response.json()
      setRecommendations(data)
    } catch (err) {
      console.error('推荐请求失败:', err)
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  const handleRetry = () => {
    setError(null)
    handleSubmit()
  }

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case 'starter':
        return 'bg-success/10 text-success border-success/20'
      case 'standard':
        return 'bg-primary/10 text-primary border-primary/20'
      case 'enterprise':
        return 'bg-purple/10 text-purple border-purple/20'
      default:
        return 'bg-text-tertiary/10 text-text-tertiary border-border'
    }
  }

  const getTierLabel = (tier: string) => {
    switch (tier) {
      case 'starter':
        return '入门版'
      case 'standard':
        return '标准版'
      case 'enterprise':
        return '企业版'
      default:
        return tier
    }
  }

  const getScoreGrade = (score: number | null | undefined): string => {
    if (score === null || score === undefined) return 'U'
    if (score >= 90) return 'A'
    if (score >= 75) return 'B'
    if (score >= 60) return 'C'
    return 'D'
  }

  return (
    <div className="space-y-8">
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-text-primary mb-2">技能推荐</h1>
        <p className="text-text-secondary">根据项目画像为您推荐最合适的技能组合</p>
      </div>

      {/* Input Section */}
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <h2 className="text-xl font-semibold text-text-primary mb-6">项目画像</h2>
        
        <div className="space-y-6">
          {/* Project Name */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              项目名称
            </label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="例如：电商平台后端服务"
              disabled={loading}
              className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-bg-card disabled:cursor-not-allowed"
            />
          </div>

          {/* Domains (Multi-select) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              应用领域 (多选)
            </label>
            <div className="flex flex-wrap gap-2">
              {DOMAIN_OPTIONS.map((domain) => (
                <button
                  key={domain}
                  onClick={() => handleDomainToggle(domain)}
                  disabled={loading}
                  className={`px-4 py-2 text-sm font-medium rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    domains.includes(domain)
                      ? 'bg-primary text-white'
                      : 'bg-bg-card text-text-secondary hover:bg-border'
                  }`}
                >
                  {domain}
                </button>
              ))}
            </div>
          </div>

          {/* Languages (Multi-select) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              编程语言 (多选)
            </label>
            <div className="flex flex-wrap gap-2">
              {LANGUAGE_OPTIONS.map((lang) => (
                <button
                  key={lang}
                  onClick={() => handleLanguageToggle(lang)}
                  disabled={loading}
                  className={`px-4 py-2 text-sm font-medium rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    languages.includes(lang)
                      ? 'bg-primary text-white'
                      : 'bg-bg-card text-text-secondary hover:bg-border'
                  }`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>

          {/* Security Requirement (Single select) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              安全要求
            </label>
            <div className="flex gap-3">
              {SECURITY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setSecurityRequirement(option.value)}
                  disabled={loading}
                  className={`flex-1 px-4 py-3 text-sm font-medium rounded-lg border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    securityRequirement === option.value
                      ? 'bg-primary text-white border-primary'
                      : 'bg-white text-text-secondary border-border hover:border-primary'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={!projectName || domains.length === 0 || languages.length === 0 || loading}
            className="w-full px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:bg-text-tertiary disabled:cursor-not-allowed font-medium transition-colors"
          >
            {loading ? '生成推荐中...' : '获取推荐结果'}
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
          <p className="mt-4 text-text-secondary">正在分析项目画像并生成推荐...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-danger/10 border border-danger/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-danger mb-2">请求失败</h3>
              <p className="text-sm text-text-secondary mb-4">{error}</p>
              <button
                onClick={handleRetry}
                className="px-4 py-2 bg-danger text-white rounded-lg hover:bg-danger/90 transition-colors text-sm font-medium"
              >
                重试
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {recommendations && recommendations.items.length === 0 && !loading && (
        <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
          <span className="text-6xl mb-4 inline-block">📦</span>
          <h3 className="text-xl font-semibold text-text-primary mb-2">暂无推荐结果</h3>
          <p className="text-text-secondary">
            当前没有符合条件的技能组合。请尝试调整项目画像或先采集技能。
          </p>
        </div>
      )}

      {/* Results Section */}
      {recommendations && recommendations.items.length > 0 && !loading && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-text-primary">
              推荐结果
            </h2>
            <span className="text-sm text-text-secondary">
              共 {recommendations.total} 个推荐方案
            </span>
          </div>

          {/* Recommendation Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {recommendations.items.map((item) => (
              <div
                key={item.bundle_id}
                className="bg-white rounded-2xl border-2 border-border hover:border-primary p-6 shadow-sm hover:shadow-lg transition-all"
              >
                {/* Card Header */}
                <div className="flex items-start justify-between mb-4">
                  <span
                    className={`px-3 py-1 text-sm font-semibold rounded-full border ${getTierBadgeColor(
                      item.tier
                    )}`}
                  >
                    {getTierLabel(item.tier)}
                  </span>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-primary">
                      {item.score.toFixed(1)}
                    </div>
                    <div className="text-xs text-text-tertiary">匹配度</div>
                  </div>
                </div>

                {/* Bundle Name */}
                <h3 className="text-lg font-bold text-text-primary mb-2">
                  {item.name}
                </h3>
                <p className="text-sm text-text-secondary mb-4 line-clamp-2">
                  {item.description}
                </p>

                {/* Match Reasons */}
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-text-primary mb-2">
                    推荐理由
                  </h4>
                  <ul className="space-y-1">
                    {item.match_reasons.slice(0, 3).map((reason, idx) => (
                      <li
                        key={idx}
                        className="text-sm text-text-secondary flex items-start gap-2"
                      >
                        <span className="text-primary mt-0.5">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Skills List */}
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-text-primary mb-2">
                    包含技能 ({item.skills.length})
                  </h4>
                  <div className="space-y-2">
                    {item.skills.slice(0, 3).map((skill) => (
                      <Link
                        key={skill.skill_id}
                        href={`/skills/${skill.skill_id}`}
                        className="block p-3 bg-bg-card rounded-lg hover:bg-border transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-text-primary">
                            {skill.name}
                          </span>
                          <GradeBadge grade={skill.grade || getScoreGrade(skill.score_total)} />
                        </div>
                        <div className="flex items-center justify-between text-xs text-text-tertiary">
                          <span>评分: {skill.score_total?.toFixed(1) || '—'}</span>
                        </div>
                      </Link>
                    ))}
                    {item.skills.length > 3 && (
                      <div className="text-xs text-text-tertiary text-center pt-1">
                        + {item.skills.length - 3} 个更多技能
                      </div>
                    )}
                  </div>
                </div>

                {/* Rule Findings (Collapsible) */}
                <details className="group">
                  <summary className="cursor-pointer list-none">
                    <div className="flex items-center justify-between p-3 bg-bg-card rounded-lg hover:bg-border transition-colors">
                      <span className="text-sm font-medium text-text-primary">
                        规则检查 ({item.rule_findings.length})
                      </span>
                      <svg
                        className="w-4 h-4 text-text-secondary group-open:rotate-180 transition-transform"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </div>
                  </summary>
                  <div className="mt-2 space-y-2">
                    {item.rule_findings.map((finding) => (
                      <div
                        key={finding.rule_id}
                        className={`p-3 rounded-lg text-sm ${
                          finding.severity === 'info'
                            ? 'bg-primary/10 text-primary'
                            : finding.severity === 'warning'
                            ? 'bg-warning/10 text-warning'
                            : finding.severity === 'error'
                            ? 'bg-danger/10 text-danger'
                            : 'bg-bg-card text-text-secondary'
                        }`}
                      >
                        <div className="text-xs opacity-90">
                          {finding.message}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
