'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import CompatBadge from '@/components/skill/CompatBadge'

// ---------------------------------------------------------------------------
// Types — existing bundle recommendation
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Types — V2 ranked skills (PRD §7)
// ---------------------------------------------------------------------------

interface ConflictOut {
  type: 'version' | 'overlap'
  items: string[]
  reason: string
}

interface RankedSkillOut {
  skill_id: string
  name: string
  canonical_name: string | null
  description: string
  platform: string
  compat_status: string
  composite: number | null
  evidence_level: string | null
  rank_score: number
  compat_weight: number
  excluded: boolean
  score_source: string
}

interface SkillRecommendResponse {
  total: number
  items: RankedSkillOut[]
  conflicts: ConflictOut[]
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function compositeColor(v: number | null) {
  if (v === null || v === undefined) return '#86909C'
  if (v >= 80) return '#22c55e'
  if (v >= 50) return '#f97316'
  return '#ef4444'
}

const getTierBadgeColor = (tier: string) => {
  switch (tier) {
    case 'starter':    return 'bg-success/10 text-success border-success/20'
    case 'standard':   return 'bg-primary/10 text-primary border-primary/20'
    case 'enterprise': return 'bg-purple/10 text-purple border-purple/20'
    default:           return 'bg-text-tertiary/10 text-text-tertiary border-border'
  }
}

const getTierLabel = (tier: string) => {
  switch (tier) {
    case 'starter':    return '入门版'
    case 'standard':   return '标准版'
    case 'enterprise': return '企业版'
    default:           return tier
  }
}

const getScoreGrade = (score: number | null | undefined): string => {
  if (score === null || score === undefined) return 'U'
  if (score >= 90) return 'A'
  if (score >= 75) return 'B'
  if (score >= 60) return 'C'
  return 'D'
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function RecommendPage() {
  // ── Bundle recommendation state ─────────────────────────────────────────
  const [projectName,          setProjectName]          = useState('')
  const [domains,              setDomains]              = useState<string[]>([])
  const [languages,            setLanguages]            = useState<string[]>([])
  const [securityRequirement,  setSecurityRequirement]  = useState<string>('standard')
  const [loading,              setLoading]              = useState(false)
  const [error,                setError]                = useState<string | null>(null)
  const [recommendations,      setRecommendations]      = useState<RecommendationResponse | null>(null)
  const [savedToast,           setSavedToast]           = useState(false)
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── V2 ranked skills state ───────────────────────────────────────────────
  const [activeTab,         setActiveTab]         = useState<'bundle' | 'skills'>('bundle')
  const [rankedLoading,     setRankedLoading]     = useState(false)
  const [rankedData,        setRankedData]        = useState<SkillRecommendResponse | null>(null)
  const [includeBlocked,    setIncludeBlocked]    = useState(false)
  const [compatFilter,      setCompatFilter]      = useState<string>('')
  const COMPAT_STATUSES = [
    '', 'COMPATIBLE', 'COMPATIBLE_WITH_ADAPTER', 'PENDING_VERIFICATION',
    'PARTIAL', 'UNKNOWN', 'INCOMPATIBLE', 'BLOCKED',
  ]

  useEffect(() => {
    return () => { if (toastTimer.current) clearTimeout(toastTimer.current) }
  }, [])

  // Load ranked skills when tab switches
  useEffect(() => {
    if (activeTab === 'skills') loadRankedSkills()
  }, [activeTab, includeBlocked, compatFilter]) // eslint-disable-line

  const loadRankedSkills = async () => {
    setRankedLoading(true)
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (includeBlocked) params.set('include_blocked', 'true')
      if (compatFilter)   params.set('compat_status', compatFilter)
      const r = await fetch(`${API_BASE_URL}/api/v1/recommend/skills?${params}`)
      if (r.ok) setRankedData(await r.json())
    } catch { /* graceful */ }
    setRankedLoading(false)
  }

  // Available options
  const DOMAIN_OPTIONS   = ['web', 'mobile', 'data-science', 'devops', 'security', 'documentation']
  const LANGUAGE_OPTIONS = ['javascript', 'python', 'java', 'go', 'rust', 'typescript']
  const SECURITY_OPTIONS = [
    { value: 'lax',      label: '低（个人项目）' },
    { value: 'standard', label: '标准（团队项目）' },
    { value: 'strict',   label: '高（企业级）' },
  ]

  const handleDomainToggle   = (d: string) => setDomains(p => p.includes(d) ? p.filter(x => x !== d) : [...p, d])
  const handleLanguageToggle = (l: string) => setLanguages(p => p.includes(l) ? p.filter(x => x !== l) : [...p, l])

  const handleSubmit = async () => {
    if (!projectName || domains.length === 0 || languages.length === 0) return
    setLoading(true); setError(null)
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName, domains, languages, security_requirement: securityRequirement }),
      })
      if (r.status === 401) throw new Error('认证失败：请检查 API 访问权限')
      if (r.status === 422) { const e = await r.json().catch(() => null); throw new Error(`参数错误: ${e?.detail || '输入参数验证失败'}`) }
      if (r.status >= 500)  throw new Error('服务器内部错误：请稍后重试')
      if (!r.ok)            throw new Error(`请求失败 (${r.status}): ${r.statusText}`)
      const data: RecommendationResponse = await r.json()
      setRecommendations(data)
      setSavedToast(true)
      if (toastTimer.current) clearTimeout(toastTimer.current)
      toastTimer.current = setTimeout(() => setSavedToast(false), 4000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-text-primary mb-2">技能推荐</h1>
        <p className="text-text-secondary">根据项目画像推荐套装，或浏览按兼容权重排序的技能列表</p>
      </div>

      {/* ── Tab switcher ──────────────────────────────────────────────────── */}
      <div className="flex gap-2 border-b border-border">
        <button
          className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'bundle'
              ? 'border-primary text-primary'
              : 'border-transparent text-text-secondary hover:text-text-primary'
          }`}
          onClick={() => setActiveTab('bundle')}
        >
          📦 Bundle 推荐
        </button>
        <button
          className={`px-6 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
            activeTab === 'skills'
              ? 'border-primary text-primary'
              : 'border-transparent text-text-secondary hover:text-text-primary'
          }`}
          onClick={() => setActiveTab('skills')}
        >
          ⭐ 技能排行
        </button>
      </div>

      {/* ======================================================================
          TAB: Bundle Recommendation (existing)
      ====================================================================== */}
      {activeTab === 'bundle' && (
        <>
          {/* Input Section */}
          <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
            <h2 className="text-xl font-semibold text-text-primary mb-6">项目画像</h2>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">项目名称</label>
                <input
                  type="text" value={projectName} onChange={e => setProjectName(e.target.value)}
                  placeholder="例如：电商平台后端服务" disabled={loading}
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-bg-card disabled:cursor-not-allowed"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">应用领域 (多选)</label>
                <div className="flex flex-wrap gap-2">
                  {DOMAIN_OPTIONS.map(d => (
                    <button key={d} onClick={() => handleDomainToggle(d)} disabled={loading}
                      className={`px-4 py-2 text-sm font-medium rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                        domains.includes(d) ? 'bg-primary text-white' : 'bg-bg-card text-text-secondary hover:bg-border'
                      }`}
                    >{d}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">编程语言 (多选)</label>
                <div className="flex flex-wrap gap-2">
                  {LANGUAGE_OPTIONS.map(l => (
                    <button key={l} onClick={() => handleLanguageToggle(l)} disabled={loading}
                      className={`px-4 py-2 text-sm font-medium rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                        languages.includes(l) ? 'bg-primary text-white' : 'bg-bg-card text-text-secondary hover:bg-border'
                      }`}
                    >{l}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">安全要求</label>
                <div className="flex gap-3">
                  {SECURITY_OPTIONS.map(opt => (
                    <button key={opt.value} onClick={() => setSecurityRequirement(opt.value)} disabled={loading}
                      className={`flex-1 px-4 py-3 text-sm font-medium rounded-lg border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                        securityRequirement === opt.value
                          ? 'bg-primary text-white border-primary'
                          : 'bg-white text-text-secondary border-border hover:border-primary'
                      }`}
                    >{opt.label}</button>
                  ))}
                </div>
              </div>
              <button
                onClick={handleSubmit}
                disabled={!projectName || domains.length === 0 || languages.length === 0 || loading}
                className="w-full px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:bg-text-tertiary disabled:cursor-not-allowed font-medium transition-colors"
              >
                {loading ? '生成推荐中...' : '获取推荐结果'}
              </button>
            </div>
          </div>

          {loading && (
            <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent" />
              <p className="mt-4 text-text-secondary">正在分析项目画像并生成推荐...</p>
            </div>
          )}

          {error && !loading && (
            <div className="bg-danger/10 border border-danger/20 rounded-2xl p-6">
              <div className="flex items-start gap-4">
                <span className="text-2xl">⚠️</span>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-danger mb-2">请求失败</h3>
                  <p className="text-sm text-text-secondary mb-4">{error}</p>
                  <button onClick={() => { setError(null); handleSubmit() }}
                    className="px-4 py-2 bg-danger text-white rounded-lg hover:bg-danger/90 transition-colors text-sm font-medium">重试</button>
                </div>
              </div>
            </div>
          )}

          {recommendations && recommendations.items.length === 0 && !loading && (
            <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
              <span className="text-6xl mb-4 inline-block">📦</span>
              <h3 className="text-xl font-semibold text-text-primary mb-2">暂无推荐结果</h3>
              <p className="text-text-secondary">当前没有符合条件的技能组合。请尝试调整项目画像或先采集技能。</p>
            </div>
          )}

          {recommendations && recommendations.items.length > 0 && !loading && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-text-primary">推荐结果</h2>
                <div className="flex items-center gap-3">
                  {savedToast && (
                    <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-success/10 border border-success/20 text-success text-sm font-medium">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                      推荐已保存
                    </span>
                  )}
                  <span className="text-sm text-text-secondary">共 {recommendations.total} 个推荐方案</span>
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {recommendations.items.map((item) => (
                  <div key={item.bundle_id} className="bg-white rounded-2xl border-2 border-border hover:border-primary p-6 shadow-sm hover:shadow-lg transition-all">
                    <div className="flex items-start justify-between mb-4">
                      <span className={`px-3 py-1 text-sm font-semibold rounded-full border ${getTierBadgeColor(item.tier)}`}>
                        {getTierLabel(item.tier)}
                      </span>
                      <div className="text-right">
                        <div className="text-3xl font-bold text-primary">{item.score.toFixed(1)}</div>
                        <div className="text-xs text-text-tertiary">匹配度</div>
                      </div>
                    </div>
                    <h3 className="text-lg font-bold text-text-primary mb-2">{item.name}</h3>
                    <p className="text-sm text-text-secondary mb-4 line-clamp-2">{item.description}</p>
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-text-primary mb-2">推荐理由</h4>
                      {item.match_reasons && item.match_reasons.length > 0 ? (
                        <ul className="space-y-1">
                          {item.match_reasons.slice(0, 3).map((r, i) => (
                            <li key={i} className="text-sm text-text-secondary flex items-start gap-2">
                              <span className="text-primary mt-0.5">•</span><span>{r}</span>
                            </li>
                          ))}
                        </ul>
                      ) : <p className="text-sm text-text-tertiary">暂无推荐理由</p>}
                    </div>
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-text-primary mb-2">包含技能 ({item.skills?.length || 0})</h4>
                      {item.skills && item.skills.length > 0 ? (
                        <div className="space-y-2">
                          {item.skills.slice(0, 3).map(skill => (
                            <Link key={skill.skill_id} href={`/skills/${skill.skill_id}`}
                              className="block p-3 bg-bg-card rounded-lg hover:bg-border transition-colors">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-text-primary">{skill.name || '未命名技能'}</span>
                                <GradeBadge grade={skill.grade || getScoreGrade(skill.score_total)} />
                              </div>
                              <span className="text-xs text-text-tertiary">评分: {skill.score_total?.toFixed(1) || '—'}</span>
                            </Link>
                          ))}
                          {item.skills.length > 3 && (
                            <div className="text-xs text-text-tertiary text-center pt-1">+ {item.skills.length - 3} 个更多技能</div>
                          )}
                        </div>
                      ) : <p className="text-sm text-text-tertiary">暂无技能信息</p>}
                    </div>
                    <details className="group">
                      <summary className="cursor-pointer list-none">
                        <div className="flex items-center justify-between p-3 bg-bg-card rounded-lg hover:bg-border transition-colors">
                          <span className="text-sm font-medium text-text-primary">规则检查 ({item.rule_findings.length})</span>
                          <svg className="w-4 h-4 text-text-secondary group-open:rotate-180 transition-transform"
                            fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      </summary>
                      <div className="mt-2 space-y-2">
                        {item.rule_findings.map(f => (
                          <div key={f.rule_id} className={`p-3 rounded-lg text-sm ${
                            f.severity === 'info'    ? 'bg-primary/10 text-primary' :
                            f.severity === 'warning' ? 'bg-warning/10 text-warning' :
                            f.severity === 'error'   ? 'bg-danger/10 text-danger' :
                            'bg-bg-card text-text-secondary'
                          }`}>
                            <div className="text-xs opacity-90">{f.message}</div>
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ======================================================================
          TAB: Ranked Skills (V2 — PRD §7)
      ====================================================================== */}
      {activeTab === 'skills' && (
        <div className="space-y-6">

          {/* Filters */}
          <div className="bg-white rounded-2xl border border-border p-6 shadow-sm">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-text-primary">兼容状态筛选:</label>
                <select
                  value={compatFilter}
                  onChange={e => setCompatFilter(e.target.value)}
                  className="px-3 py-1.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {COMPAT_STATUSES.map(s => (
                    <option key={s} value={s}>{s || '全部'}</option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeBlocked}
                  onChange={e => setIncludeBlocked(e.target.checked)}
                  className="rounded border-border"
                />
                显示 BLOCKED / INCOMPATIBLE
              </label>
            </div>
          </div>

          {/* Conflicts banner */}
          {rankedData && rankedData.conflicts.length > 0 && (
            <div className="bg-[#f97316]/5 border border-[#f97316]/30 rounded-2xl p-6">
              <h3 className="text-base font-semibold text-[#f97316] mb-3">
                ⚡ 检测到 {rankedData.conflicts.length} 个冲突
              </h3>
              <div className="space-y-3">
                {rankedData.conflicts.map((c, i) => (
                  <div key={i} className="p-3 bg-white/60 rounded-xl">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                        c.type === 'version' ? 'bg-[#8b5cf6] text-white' : 'bg-[#f97316] text-white'
                      }`}>
                        {c.type === 'version' ? '版本冲突' : '功能重叠'}
                      </span>
                      <span className="text-xs text-[#4E5969] font-mono">{c.items.join(' · ')}</span>
                    </div>
                    <p className="text-xs text-[#6b7280]">{c.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Loading */}
          {rankedLoading && (
            <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent" />
              <p className="mt-4 text-text-secondary">加载排行中...</p>
            </div>
          )}

          {/* Empty */}
          {!rankedLoading && rankedData && rankedData.items.length === 0 && (
            <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
              <span className="text-5xl mb-4 inline-block">📭</span>
              <h3 className="text-xl font-semibold text-text-primary mb-2">暂无技能数据</h3>
              <p className="text-text-secondary">请先通过采集流水线导入技能</p>
            </div>
          )}

          {/* Ranked cards */}
          {!rankedLoading && rankedData && rankedData.items.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-text-primary">
                  技能排行 ({rankedData.total})
                </h2>
                <span className="text-xs text-text-tertiary">按兼容权重 × 综合评分排序</span>
              </div>

              {rankedData.items.map((skill, idx) => (
                <Link
                  key={skill.skill_id}
                  href={`/skills/${skill.skill_id}`}
                  className={`block bg-white rounded-2xl border p-6 shadow-sm hover:shadow-md transition-all ${
                    skill.excluded
                      ? 'border-[#ef4444]/20 opacity-60 cursor-not-allowed pointer-events-none'
                      : 'border-[#E5E6EB] hover:border-[#165DFF]'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    {/* Rank number */}
                    <div className="w-10 h-10 rounded-full bg-[#F5F7FA] flex items-center justify-center shrink-0">
                      <span className="text-sm font-bold text-[#4E5969]">{idx + 1}</span>
                    </div>

                    {/* Main content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <h3 className="text-base font-semibold text-[#1D2129] truncate">{skill.name}</h3>
                        <CompatBadge status={skill.compat_status} size="sm" />
                        {skill.excluded && (
                          <span className="px-2 py-0.5 text-xs bg-[#ef4444] text-white rounded-full font-bold">已排除</span>
                        )}
                      </div>
                      <p className="text-sm text-[#86909C] truncate">{skill.description || '—'}</p>
                    </div>

                    {/* Score block */}
                    <div className="shrink-0 text-right">
                      {/* rank_score */}
                      <div
                        className="text-2xl font-bold"
                        style={{ color: compositeColor(skill.rank_score) }}
                      >
                        {skill.rank_score.toFixed(1)}
                      </div>
                      <div className="text-xs text-[#86909C]">rank</div>

                      {/* compat_weight tag */}
                      <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-[#F5F7FA] text-[#4E5969] rounded-full font-mono">
                        w={skill.compat_weight.toFixed(2)}
                      </span>

                      {/* composite */}
                      <div className="mt-1 text-xs text-[#86909C]">
                        {skill.composite !== null
                          ? `composite ${skill.composite.toFixed(1)}`
                          : <span className="text-[#86909C] border-b border-dashed">evidence fallback</span>
                        }
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
