'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

interface IngestResponse {
  discovered?: number
  acquired?: number
  reviewed?: number
  quarantined?: number
  runnable?: number
  errors?: Array<{ source?: string; skill_id?: string; error: string }>
  skills?: Array<{ skill_id: string; name: string; benchmark_score?: number | null; state: string }>
  // Fallback fields from /ingest/github endpoint
  created?: number
  updated?: number
  skipped?: number
  warnings?: string[]
}

interface RunRecord {
  id: number
  query: string
  startedAt: string
  discovered: number
  acquired: number
  reviewed: number
  quarantined: number
  runnable: number
  errorCount: number
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

const STATE_COLORS: Record<string, { bg: string; text: string }> = {
  discovered: { bg: 'bg-text-tertiary/10', text: 'text-text-tertiary' },
  acquired:   { bg: 'bg-primary/10',        text: 'text-primary' },
  reviewed:   { bg: 'bg-success/10',        text: 'text-success' },
  quarantined:{ bg: 'bg-danger/10',         text: 'text-danger' },
  runnable:   { bg: 'bg-purple/10',         text: 'text-purple' },
}

let _runSeq = 0

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function IngestPage() {
  const router = useRouter()
  const [query, setQuery]   = useState('')
  const [limit, setLimit]   = useState<number>(5)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState<string | null>(null)
  const [result, setResult] = useState<IngestResponse | null>(null)
  const [runHistory, setRunHistory] = useState<RunRecord[]>([])
  const [historyOpen, setHistoryOpen] = useState(false)

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    const startedAt = new Date().toISOString()

    try {
      // Try pipeline endpoint first; fall back to /ingest/github
      let response = await fetch(`${API_BASE_URL}/api/v1/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), limit }),
      })

      if (response.status === 404 || response.status === 405) {
        response = await fetch(`${API_BASE_URL}/api/v1/ingest/github`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query.trim(), limit }),
        })
      }

      if (response.status === 404) {
        throw new Error('采集接口未就绪：后端 ingest API 尚未实现')
      }
      if (response.status === 401) {
        throw new Error('认证失败：请检查 API 访问权限')
      }
      if (response.status === 422) {
        const body = await response.json().catch(() => null)
        throw new Error(`参数错误: ${body?.detail ?? '输入参数验证失败'}`)
      }
      if (response.status >= 500) {
        throw new Error('服务器内部错误：请稍后重试或联系管理员')
      }
      if (!response.ok) {
        throw new Error(`请求失败 (${response.status}): ${response.statusText}`)
      }

      const data: IngestResponse = await response.json()

      const normalized: IngestResponse = {
        discovered:  data.discovered  ?? data.created  ?? 0,
        acquired:    data.acquired    ?? data.updated   ?? 0,
        reviewed:    data.reviewed    ?? 0,
        quarantined: data.quarantined ?? 0,
        runnable:    data.runnable    ?? 0,
        errors:      data.errors      ?? (data.warnings?.map(w => ({ error: w })) ?? []),
        skills:      data.skills      ?? [],
      }

      setResult(normalized)

      // Append to session-local run history
      setRunHistory(prev => [
        {
          id:          ++_runSeq,
          query:       query.trim(),
          startedAt,
          discovered:  normalized.discovered  ?? 0,
          acquired:    normalized.acquired    ?? 0,
          reviewed:    normalized.reviewed    ?? 0,
          quarantined: normalized.quarantined ?? 0,
          runnable:    normalized.runnable    ?? 0,
          errorCount:  normalized.errors?.length ?? 0,
        },
        ...prev,
      ].slice(0, 10)) // keep at most 10 in-session records
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }, [query, limit])

  const handleRetry = () => {
    setError(null)
    handleSubmit(new Event('submit') as unknown as React.FormEvent)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-text-primary mb-2">技能采集</h1>
        <p className="text-text-secondary">输入关键词，从 GitHub 搜索并采集 Skill</p>
      </div>

      {/* Input Section */}
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Search Query */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              搜索关键词
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="例如：pdf processing, document extraction, SKILL.md..."
              disabled={loading}
              className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-bg-card disabled:cursor-not-allowed text-base"
            />
            <p className="mt-2 text-sm text-text-tertiary">
              将在 GitHub 上搜索包含该关键词的仓库
            </p>
          </div>

          {/* Limit Selector */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              采集数量
            </label>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              disabled={loading}
              className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-bg-card disabled:cursor-not-allowed text-base"
            >
              <option value={1}>1 个仓库</option>
              <option value={3}>3 个仓库</option>
              <option value={5}>5 个仓库（推荐）</option>
              <option value={10}>10 个仓库</option>
              <option value={20}>20 个仓库</option>
            </select>
            <p className="mt-2 text-sm text-text-tertiary">
              数量越多，采集时间越长
            </p>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="w-full px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:bg-text-tertiary disabled:cursor-not-allowed font-medium transition-colors text-base flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                <span>采集中，请稍候...</span>
              </>
            ) : (
              <span>开始采集</span>
            )}
          </button>
        </form>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-primary border-t-transparent mb-4" />
          <h3 className="text-lg font-semibold text-text-primary mb-2">正在采集技能...</h3>
          <p className="text-text-secondary">
            正在从 GitHub 搜索、获取、扫描和评分，这可能需要一些时间
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-danger/10 border border-danger/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <span className="text-3xl">⚠️</span>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-danger mb-2">采集失败</h3>
              <p className="text-sm text-text-secondary mb-4">{error}</p>
              <div className="flex gap-3">
                <button
                  onClick={handleRetry}
                  className="px-4 py-2 bg-danger text-white rounded-lg hover:bg-danger/90 transition-colors text-sm font-medium"
                >
                  重试
                </button>
                <Link
                  href="/skills"
                  className="px-4 py-2 bg-white border border-border text-text-primary rounded-lg hover:bg-bg-card transition-colors text-sm font-medium"
                >
                  查看现有技能
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Success Result */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-text-primary">采集结果</h2>
              <span className="text-sm text-text-tertiary">关键词：&ldquo;{query}&rdquo;</span>
            </div>

            {/* State Count Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
              {(
                [
                  { key: 'discovered',  label: '已发现',  sub: 'DISCOVERED' },
                  { key: 'acquired',    label: '已获取',  sub: 'ACQUIRED' },
                  { key: 'reviewed',    label: '审查通过', sub: 'STATIC_REVIEWED' },
                  { key: 'quarantined', label: '已隔离',  sub: 'QUARANTINED' },
                  { key: 'runnable',    label: '可运行',  sub: 'RUNNABLE' },
                ] as const
              ).map(({ key, label, sub }) => (
                <div key={key} className={`${STATE_COLORS[key].bg} rounded-xl p-6 text-center`}>
                  <div className={`text-4xl font-bold ${STATE_COLORS[key].text} mb-2`}>
                    {result[key] ?? 0}
                  </div>
                  <div className="text-sm font-medium text-text-secondary">{label}</div>
                  <div className="text-xs text-text-tertiary mt-1">{sub}</div>
                </div>
              ))}
            </div>

            {/* Error Messages */}
            {result.errors && result.errors.length > 0 && (
              <div className="mb-6 p-4 bg-warning/10 border border-warning/20 rounded-lg">
                <h3 className="text-sm font-semibold text-warning mb-2">
                  ⚠️ 部分采集失败 ({result.errors.length} 个错误)
                </h3>
                <div className="space-y-1">
                  {result.errors.slice(0, 3).map((err, idx) => (
                    <p key={idx} className="text-xs text-text-secondary">
                      • {err.source ? `[${err.source}] ` : ''}{err.error}
                    </p>
                  ))}
                  {result.errors.length > 3 && (
                    <p className="text-xs text-text-tertiary italic">
                      ...以及 {result.errors.length - 3} 个其他错误
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={() => router.push('/skills')}
                className="flex-1 px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors font-medium text-base"
              >
                查看技能列表 →
              </button>
              <button
                onClick={() => { setResult(null); setQuery('') }}
                className="px-6 py-3 bg-white border border-border text-text-primary rounded-lg hover:bg-bg-card transition-colors font-medium text-base"
              >
                再次采集
              </button>
            </div>
          </div>

          {/* Skills List Preview */}
          {result.skills && result.skills.length > 0 && (
            <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
              <h3 className="text-lg font-semibold text-text-primary mb-4">
                采集的技能 ({result.skills.length})
              </h3>
              <div className="space-y-3">
                {result.skills.map((skill) => (
                  <Link
                    key={skill.skill_id}
                    href={`/skills/${skill.skill_id}`}
                    className="block p-4 bg-bg-card rounded-lg hover:bg-border transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium text-text-primary">{skill.name || '未命名技能'}</h4>
                        <p className="text-sm text-text-tertiary">
                          {skill.state}
                          {skill.benchmark_score != null && (
                            <span className="ml-2">• 评分: {skill.benchmark_score.toFixed(1)}</span>
                          )}
                        </p>
                      </div>
                      <span className="text-primary text-sm font-medium">查看详情 →</span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty/initial State */}
      {!loading && !error && !result && (
        <div className="bg-gradient-to-br from-primary/5 to-purple/5 rounded-2xl border border-primary/10 p-12">
          <div className="max-w-2xl mx-auto text-center">
            <span className="text-6xl mb-4 inline-block">🔍</span>
            <h3 className="text-xl font-semibold text-text-primary mb-3">开始采集 GitHub 技能</h3>
            <p className="text-text-secondary mb-6">
              输入关键词和数量，系统将自动搜索、获取、扫描和评分 GitHub 上的技能仓库
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-left">
              {[
                { icon: '🔍', label: '搜索发现', tier: 'L1' },
                { icon: '📥', label: '获取内容', tier: 'L1' },
                { icon: '🔒', label: '安全扫描', tier: 'L3' },
                { icon: '⚡', label: '性能评分', tier: 'L4' },
              ].map(({ icon, label, tier }) => (
                <div key={label} className="p-4 bg-white rounded-lg border border-border">
                  <div className="text-2xl mb-2">{icon}</div>
                  <div className="text-xs font-medium text-text-primary">{label}</div>
                  <div className="text-xs text-text-tertiary">{tier}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Session Run History ─────────────────────────────────────────── */}
      {/*
        NOTE: The backend stores ingest_runs in SQLite (api/db/aux_store.py),
        but no GET /api/v1/ingest/runs endpoint is currently registered in
        api/routers/ingest.py.  Adding that route would require a backend
        change (out of scope for this task).  We therefore show a session-local
        log that is populated from successful in-page submissions.
        Persistent cross-session history will be available once the backend
        exposes GET /api/v1/ingest/runs.
      */}
      {runHistory.length > 0 && (
        <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
          <button
            onClick={() => setHistoryOpen(o => !o)}
            className="w-full flex items-center justify-between px-8 py-5 hover:bg-bg-card transition-colors text-left"
          >
            <div className="flex items-center gap-3">
              <span className="text-lg">🕐</span>
              <span className="text-base font-semibold text-text-primary">
                本次会话采集记录
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
                {runHistory.length}
              </span>
            </div>
            <svg
              className={`w-5 h-5 text-text-tertiary transition-transform ${historyOpen ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {historyOpen && (
            <div className="border-t border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-bg-card text-text-tertiary text-xs uppercase tracking-wide">
                    <th className="px-6 py-3 text-left font-medium">#</th>
                    <th className="px-6 py-3 text-left font-medium">关键词</th>
                    <th className="px-6 py-3 text-center font-medium">发现</th>
                    <th className="px-6 py-3 text-center font-medium">获取</th>
                    <th className="px-6 py-3 text-center font-medium">审查</th>
                    <th className="px-6 py-3 text-center font-medium text-danger">隔离</th>
                    <th className="px-6 py-3 text-center font-medium text-purple">可用</th>
                    <th className="px-6 py-3 text-left font-medium">时间</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {runHistory.map((run) => (
                    <tr key={run.id} className="hover:bg-bg-card/60 transition-colors">
                      <td className="px-6 py-3 text-text-tertiary">{run.id}</td>
                      <td className="px-6 py-3 text-text-primary max-w-[200px] truncate font-medium">
                        {run.query}
                        {run.errorCount > 0 && (
                          <span className="ml-2 text-xs text-warning">
                            ({run.errorCount} 错)
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3 text-center text-text-tertiary">{run.discovered}</td>
                      <td className="px-6 py-3 text-center text-primary">{run.acquired}</td>
                      <td className="px-6 py-3 text-center text-success">{run.reviewed}</td>
                      <td className="px-6 py-3 text-center text-danger">{run.quarantined}</td>
                      <td className="px-6 py-3 text-center text-purple">{run.runnable}</td>
                      <td className="px-6 py-3 text-text-tertiary whitespace-nowrap">
                        {fmtTime(run.startedAt)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="px-6 py-3 text-xs text-text-tertiary border-t border-border">
                仅显示本次会话内的采集记录（最多 10 条）。跨会话持久历史需后端开放 GET /api/v1/ingest/runs。
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
