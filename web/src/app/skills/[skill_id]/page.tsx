'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import ScoreBar from '@/components/skill/ScoreBar'
import CompatBadge from '@/components/skill/CompatBadge'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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
  evidence_grade_detail?: string
  applicable_scenarios?: string[]
  not_applicable_scenarios?: string[]
  compatibility_status?: string
  compatibility_notes?: string
  static_findings?: Array<{ dimension: string; level: string; message: string }>
  failure_cases?: string[]
  test_env?: { model?: string; host?: string; os?: string }
  source_platforms?: string[]
  metrics?: { accuracy?: number; reliability?: number; security?: number; performance?: number }
  findings?: Array<{ dimension: string; severity: string; message: string }>
  scanned_at?: string
  // V1E fields
  risk_flags?: Array<{ rule: string; severity: string; detail: string }>
  dynamic_score?: number | null
}

interface ScoreResult {
  skill_id: string
  dimensions: Record<string, number | null>
  composite: number | null
  evidence_level: string
  sample_size: number
  uplift: number | null
  env: { host: string; model: string; client_version: string; test_date: string }
  status: string
  valid_until: string | null
}

interface CompatResult {
  skill_id: string
  compat_status: string
  portable_core: Record<string, any>
  host_overlay: { missing_items: string[]; present_items: string[]; adaptation_cost: string }
  evidence: { has_load_evidence: boolean; source: string }
  recommendations: string[]
}

interface BundleSummary { bundle_id: string; name: string; description: string; category: string }
interface BundleListResponse { items: BundleSummary[]; total: number }

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Status badge helpers
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; text: string }> = {
    VERIFIED:         { bg: '#22c55e', text: '#fff' },
    STATIC_REVIEWED:  { bg: '#3b82f6', text: '#fff' },
    QUARANTINED:      { bg: '#ef4444', text: '#fff' },
    METADATA_ONLY:    { bg: '#6b7280', text: '#fff' },
    ACQUIRED:         { bg: '#eab308', text: '#fff' },
    DISCOVERED:       { bg: '#eab308', text: '#fff' },
  }
  const c = cfg[status] ?? { bg: '#86909C', text: '#fff' }
  return (
    <span
      className="px-3 py-1 text-xs font-semibold rounded-full"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {status}
    </span>
  )
}

function EvidenceBadge({ level }: { level: string }) {
  const cfg: Record<string, { bg: string; text: string }> = {
    A: { bg: '#f59e0b', text: '#fff' },
    B: { bg: '#3b82f6', text: '#fff' },
    C: { bg: '#6b7280', text: '#fff' },
    D: { bg: '#9ca3af', text: '#fff' },
    U: { bg: '#e5e7eb', text: '#9ca3af' },
  }
  const c = cfg[level] ?? cfg['U']
  return (
    <span
      className="px-3 py-1 text-xs font-semibold rounded-full"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      Evidence {level}
    </span>
  )
}

// Composite score colour helper
function compositeColor(v: number | null) {
  if (v === null || v === undefined) return '#86909C'
  if (v >= 80) return '#22c55e'
  if (v >= 50) return '#f97316'
  return '#ef4444'
}

// Dimension labels (PRD §6.1)
const DIM_LABELS: Record<string, string> = {
  task_effect:        '任务效果 Task Effect',
  stability:          '稳定性 Stability',
  trigger_quality:    '触发质量 Trigger Quality',
  permission_privacy: '权限隐私 Permission/Privacy',
  cost_efficiency:    '成本效益 Cost Efficiency',
  platform_compat:    '平台兼容 Platform Compat',
  maintainability:    '可维护性 Maintainability',
  doc_explainability: '文档说明 Doc Explainability',
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SkillDetailPage({ params }: { params: { skill_id: string } }) {
  const [skill,         setSkill]         = useState<SkillDetail | null>(null)
  const [scoreResult,   setScoreResult]   = useState<ScoreResult | null>(null)
  const [compatResult,  setCompatResult]  = useState<CompatResult | null>(null)
  const [bundles,       setBundles]       = useState<BundleSummary[]>([])
  const [loading,       setLoading]       = useState(true)
  const [scoreLoading,  setScoreLoading]  = useState(false)
  const [compatLoading, setCompatLoading] = useState(false)
  const [riskExpanded,  setRiskExpanded]  = useState(false)
  const [overlayExpanded, setOverlayExpanded] = useState(false)

  useEffect(() => { loadAll() }, [params.skill_id]) // eslint-disable-line

  const loadAll = async () => {
    setLoading(true)
    await loadSkill()
    // Fire scores + compat in parallel after main load
    loadScores()
    loadCompat()
    loadBundles(params.skill_id)
    setLoading(false)
  }

  const loadSkill = async () => {
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/skills/${params.skill_id}`)
      if (r.ok) setSkill(await r.json())
      else setSkill(null)
    } catch { setSkill(null) }
  }

  const loadScores = async () => {
    setScoreLoading(true)
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/skills/${params.skill_id}/scores`)
      if (r.ok) setScoreResult(await r.json())
    } catch { /* graceful degradation */ }
    setScoreLoading(false)
  }

  const loadCompat = async () => {
    setCompatLoading(true)
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/skills/${params.skill_id}/compat`)
      if (r.ok) setCompatResult(await r.json())
    } catch { /* graceful degradation */ }
    setCompatLoading(false)
  }

  const loadBundles = async (skillId: string) => {
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/bundles/by-skill/${skillId}`)
      if (r.ok) { const d: BundleListResponse = await r.json(); setBundles(d.items || []) }
    } catch { /* ignore */ }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-12 shadow-sm text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#165DFF] border-t-transparent" />
        <p className="mt-4 text-[#4E5969]">加载中...</p>
      </div>
    )
  }

  if (!skill) {
    return (
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-[#F53F3F]">Skill Not Found</h1>
        <p className="mt-2 text-[#4E5969]">The requested skill ID does not exist.</p>
      </div>
    )
  }

  // Derived values
  const riskFlags    = skill.risk_flags ?? []
  const hasBlockFlag = riskFlags.some(f => f.severity === 'block')

  return (
    <div className="space-y-6">

      {/* ── Main card ──────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">

        {/* Header row */}
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <h1 className="text-3xl font-bold text-[#1D2129]">
                {skill.summary.canonical_name}
              </h1>
              <GradeBadge grade={skill.summary.grade} />
              {/* V1E: Status badge */}
              <StatusBadge status={skill.summary.status} />
            </div>
            <p className="text-sm text-[#86909C] font-mono">{skill.summary.skill_id}</p>
          </div>
          {/* Evidence badge */}
          <div className="flex flex-col gap-2 ml-4 shrink-0">
            <EvidenceBadge level={skill.summary.evidence_grade} />
          </div>
        </div>

        {/* ── V1E: Risk Flags ─────────────────────────────────────────────── */}
        {riskFlags.length > 0 && (
          <div className={`mb-6 p-4 rounded-xl border ${
            hasBlockFlag
              ? 'bg-[#ef4444]/5 border-[#ef4444]/30'
              : 'bg-[#f97316]/5 border-[#f97316]/30'
          }`}>
            <button
              className="w-full flex items-center justify-between text-left"
              onClick={() => setRiskExpanded(v => !v)}
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">{hasBlockFlag ? '🚫' : '⚠️'}</span>
                <span className={`font-semibold text-sm ${
                  hasBlockFlag ? 'text-[#ef4444]' : 'text-[#f97316]'
                }`}>
                  {hasBlockFlag ? 'QUARANTINED' : '风险标记'} — {riskFlags.length} 个问题
                </span>
              </div>
              <svg
                className={`w-4 h-4 transition-transform ${riskExpanded ? 'rotate-180' : ''}`}
                style={{ color: hasBlockFlag ? '#ef4444' : '#f97316' }}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {riskExpanded && (
              <div className="mt-3 space-y-2">
                {riskFlags.map((f, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-white/60 rounded-lg">
                    <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                      f.severity === 'block' ? 'bg-[#ef4444] text-white' : 'bg-[#f97316] text-white'
                    }`}>
                      {f.severity.toUpperCase()}
                    </span>
                    <div>
                      <p className="text-xs font-mono text-[#4E5969]">{f.rule}</p>
                      <p className="text-sm text-[#1D2129]">{f.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── V1D: Dynamic score ──────────────────────────────────────────── */}
        {skill.dynamic_score !== null && skill.dynamic_score !== undefined ? (
          <div className="mb-4 flex items-center gap-2">
            <span className="text-sm text-[#4E5969]">动态评分:</span>
            <span
              className="px-3 py-1 text-sm font-bold rounded-full"
              style={{ backgroundColor: compositeColor(skill.dynamic_score) + '20', color: compositeColor(skill.dynamic_score) }}
            >
              {skill.dynamic_score.toFixed(1)}
            </span>
          </div>
        ) : (
          <div className="mb-4 flex items-center gap-2">
            <span className="text-sm text-[#4E5969]">动态评分:</span>
            <span className="px-3 py-1 text-sm rounded-full border border-dashed border-[#86909C] text-[#86909C]">
              未启用
            </span>
          </div>
        )}

        {/* Legacy score_total (kept for backward compat) */}
        {skill.summary.score_total !== null && skill.summary.score_total !== undefined && (
          <div className="mb-8 p-6 bg-[#F5F7FA] rounded-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-[#4E5969]">综合评分</h3>
              <span className="text-5xl font-bold text-[#165DFF]">
                {skill.summary.score_total.toFixed(1)}
              </span>
            </div>
            <ScoreBar score={skill.summary.score_total} />
          </div>
        )}

        {/* Info grid */}
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
              target="_blank" rel="noopener noreferrer"
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

        {/* Warnings */}
        {skill.warnings && skill.warnings.length > 0 && (
          <div className="mt-6 p-4 bg-[#FF7D00]/10 rounded-xl">
            <h3 className="text-sm font-medium text-[#FF7D00] mb-2">Warnings</h3>
            <ul className="space-y-1">
              {skill.warnings.map((w, i) => (
                <li key={i} className="text-sm text-[#FF7D00]">• {w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Evaluate CTA */}
        {skill.summary.origin_url.includes('github.com') && (
          <div className="mt-8 p-6 bg-gradient-to-r from-[#165DFF]/5 to-[#722ED1]/5 rounded-2xl border border-[#165DFF]/20">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-[#1D2129] mb-1">获取详细评分</h3>
                <p className="text-sm text-[#4E5969]">评估此 Skill 的 GitHub 仓库，获取维度分数、代码质量分析和安全发现</p>
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

        {/* Static findings */}
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-[#1D2129] mb-4">静态检测结果</h3>
          {skill.static_findings && skill.static_findings.length > 0 ? (
            <div className="space-y-3">
              {skill.static_findings.map((f, i) => (
                <div key={i} className="flex items-start gap-4 p-4 bg-[#F5F7FA] rounded-xl">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-sm font-medium text-[#1D2129]">{f.dimension}</span>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                        f.level === 'pass' ? 'bg-[#00B42A] text-white' :
                        f.level === 'warning' ? 'bg-[#FF7D00] text-white' :
                        f.level === 'block' ? 'bg-[#F53F3F] text-white' :
                        'bg-[#86909C] text-white'
                      }`}>{f.level.toUpperCase()}</span>
                    </div>
                    <p className="text-sm text-[#4E5969]">{f.message}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#86909C]">暂无静态检测结果</p>
          )}
        </div>

        {/* Source platforms */}
        {skill.source_platforms && skill.source_platforms.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[#E5E6EB]">
            <h4 className="text-sm font-medium text-[#4E5969] mb-3">来源平台</h4>
            <div className="flex flex-wrap gap-2">
              {skill.source_platforms.map((p, i) => (
                <span key={i} className="px-3 py-1 text-xs font-medium bg-[#86909C]/10 text-[#86909C] rounded-full">{p}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Scoring card (V1F — /scores) ───────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-[#1D2129]">⭐ 八维评分</h2>
          {scoreResult && <EvidenceBadge level={scoreResult.evidence_level ?? 'U'} />}
        </div>

        {scoreLoading && (
          <div className="text-center py-6">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#165DFF] border-t-transparent" />
            <p className="mt-2 text-sm text-[#4E5969]">加载评分中...</p>
          </div>
        )}

        {!scoreLoading && !scoreResult && (
          <p className="text-sm text-[#86909C]">暂无评分数据</p>
        )}

        {!scoreLoading && scoreResult && (
          <>
            {/* Composite */}
            <div className="flex items-center gap-6 mb-8 p-6 bg-[#F5F7FA] rounded-2xl">
              <div>
                <p className="text-xs text-[#86909C] mb-1">综合评分 Composite</p>
                {scoreResult.composite !== null ? (
                  <span
                    className="text-5xl font-bold"
                    style={{ color: compositeColor(scoreResult.composite) }}
                  >
                    {scoreResult.composite.toFixed(1)}
                  </span>
                ) : (
                  <span className="text-3xl font-bold text-[#86909C] border-b-2 border-dashed border-[#86909C]">
                    —
                  </span>
                )}
              </div>
              <div className="flex-1">
                {scoreResult.composite !== null && (
                  <ScoreBar score={scoreResult.composite} />
                )}
              </div>
            </div>

            {/* Dimension bars */}
            <div className="space-y-4">
              {Object.entries(scoreResult.dimensions).map(([dim, val]) => (
                <div key={dim}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-[#4E5969]">{DIM_LABELS[dim] ?? dim}</span>
                    {val !== null ? (
                      <span className="text-sm font-bold" style={{ color: compositeColor(val) }}>
                        {val.toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-xs text-[#86909C]">—</span>
                    )}
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-2">
                    {val !== null ? (
                      <div
                        className="h-2 rounded-full transition-all duration-500"
                        style={{ width: `${val}%`, backgroundColor: compositeColor(val) }}
                      />
                    ) : (
                      <div className="h-2 rounded-full bg-[#E5E6EB] border border-dashed border-[#86909C]" />
                    )}
                  </div>
                </div>
              ))}
            </div>

            <p className="mt-4 text-xs text-[#86909C]">
              样本数: {scoreResult.sample_size} ·
              评测模型: {scoreResult.env?.model ?? '—'} ·
              版本: {scoreResult.env?.client_version ?? '—'}
            </p>
          </>
        )}
      </div>

      {/* ── Compat card (V1G — /compat) ────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-[#1D2129]">🔌 兼容判定</h2>
          {compatResult && <CompatBadge status={compatResult.compat_status} />}
        </div>

        {compatLoading && (
          <div className="text-center py-6">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#165DFF] border-t-transparent" />
            <p className="mt-2 text-sm text-[#4E5969]">加载兼容判定中...</p>
          </div>
        )}

        {!compatLoading && !compatResult && (
          <p className="text-sm text-[#86909C]">暂无兼容判定数据</p>
        )}

        {!compatLoading && compatResult && (
          <>
            {/* Evidence */}
            <div className="flex items-center gap-4 mb-6 p-4 bg-[#F5F7FA] rounded-xl">
              <div>
                <p className="text-xs text-[#86909C]">加载证据</p>
                <span className={`text-sm font-semibold ${
                  compatResult.evidence.has_load_evidence ? 'text-[#22c55e]' : 'text-[#6b7280]'
                }`}>
                  {compatResult.evidence.has_load_evidence ? '✓ 有证据' : '✗ 无证据'}
                </span>
              </div>
              <div>
                <p className="text-xs text-[#86909C]">来源</p>
                <span className="text-sm text-[#1D2129]">{compatResult.evidence.source}</span>
              </div>
              <div>
                <p className="text-xs text-[#86909C]">适配成本</p>
                <span className={`text-sm font-semibold ${
                  compatResult.host_overlay.adaptation_cost === 'low'   ? 'text-[#22c55e]' :
                  compatResult.host_overlay.adaptation_cost === 'medium' ? 'text-[#f97316]' :
                  'text-[#ef4444]'
                }`}>
                  {compatResult.host_overlay.adaptation_cost.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Host Overlay missing items */}
            {compatResult.host_overlay.missing_items.length > 0 && (
              <div className="mb-4">
                <button
                  className="w-full flex items-center justify-between text-left p-3 bg-[#F5F7FA] rounded-xl hover:bg-[#E5E6EB] transition-colors"
                  onClick={() => setOverlayExpanded(v => !v)}
                >
                  <span className="text-sm font-medium text-[#4E5969]">
                    缺失 Host Overlay 项 ({compatResult.host_overlay.missing_items.length})
                  </span>
                  <svg
                    className={`w-4 h-4 text-[#86909C] transition-transform ${overlayExpanded ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {overlayExpanded && (
                  <div className="mt-2 flex flex-wrap gap-2 px-3">
                    {compatResult.host_overlay.missing_items.map((item, i) => (
                      <span key={i} className="px-2 py-0.5 text-xs bg-[#eab308]/10 text-[#b45309] rounded">
                        {item.replace(/_/g, '-')}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Recommendations */}
            {compatResult.recommendations.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-[#4E5969] mb-2">建议</h4>
                <ul className="space-y-1">
                  {compatResult.recommendations.map((r, i) => (
                    <li key={i} className="text-sm text-[#1D2129] flex items-start gap-2">
                      <span className="text-[#165DFF] mt-0.5">→</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Bundle recommendations ──────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-lg font-semibold text-[#1D2129] mb-4">📦 包含在以下套装中</h2>
        {bundles.length === 0 ? (
          <p className="text-sm text-[#86909C] py-2">暂无套装包含此技能</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {bundles.slice(0, 3).map((bundle) => (
              <Link
                key={bundle.bundle_id}
                href={`/bundles/${bundle.bundle_id}`}
                className="block p-5 border border-[#E5E6EB] rounded-xl hover:border-[#165DFF] hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-base font-semibold text-[#1D2129] flex-1">{bundle.name}</h3>
                  <span className="text-xl ml-2">📦</span>
                </div>
                <p className="text-sm text-[#4E5969] mb-3 line-clamp-1">{bundle.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2 py-1 rounded bg-[#165DFF]/10 text-[#165DFF] font-medium">{bundle.category}</span>
                  <span className="text-sm text-[#165DFF] font-medium">查看详情 →</span>
                </div>
              </Link>
            ))}
          </div>
        )}
        {bundles.length > 3 && (
          <div className="mt-4 text-center">
            <Link href="/bundles" className="text-sm text-[#165DFF] hover:text-[#4080FF] font-medium">查看全部套装 →</Link>
          </div>
        )}
      </div>

      {/* ── JSON-LD ──────────────────────────────────────────────────────────── */}
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
