'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import ScoreBar from '@/components/skill/ScoreBar'

interface SkillSummary {
  skill_id: string
  canonical_name: string
  status: string
  description: string | null
  grade?: string | null
  score_total?: number | null
  origin_url: string
}

interface SkillListResponse {
  items: SkillSummary[]
  total: number
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

const STATE_COLORS: Record<string, string> = {
  'DISCOVERED': 'bg-text-tertiary/10 text-text-tertiary border-text-tertiary/20',
  'ACQUIRED': 'bg-primary/10 text-primary border-primary/20',
  'STATIC_REVIEWED': 'bg-success/10 text-success border-success/20',
  'QUARANTINED': 'bg-danger/10 text-danger border-danger/20',
  'RUNNABLE': 'bg-purple/10 text-purple border-purple/20',
  'NEUTRAL_TESTED': 'bg-success/10 text-success border-success/20',
}

const STATE_LABELS: Record<string, string> = {
  'DISCOVERED': '已发现',
  'ACQUIRED': '已获取',
  'STATIC_REVIEWED': '静态审查',
  'QUARANTINED': '隔离',
  'RUNNABLE': '可运行',
  'NEUTRAL_TESTED': '已测试',
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stateFilter, setStateFilter] = useState<string>('all')
  const [total, setTotal] = useState(0)

  useEffect(() => {
    loadSkills()
  }, [])

  const loadSkills = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/skills?limit=100`)
      
      if (response.status === 404) {
        setError('接口未就绪：GET /api/v1/skills 暂不可用')
        return
      }

      if (response.status === 401) {
        setError('认证失败：请检查 API 访问权限')
        return
      }

      if (response.status >= 500) {
        setError('服务器内部错误：请稍后重试')
        return
      }

      if (!response.ok) {
        throw new Error(`请求失败 (${response.status}): ${response.statusText}`)
      }

      const data: SkillListResponse = await response.json()
      setSkills(data.items)
      setTotal(data.total)
    } catch (err) {
      // console.error('加载技能列表失败:', err)
      setError(err instanceof Error ? err.message : '未知错误')
    } finally {
      setLoading(false)
    }
  }

  const filteredSkills = stateFilter === 'all'
    ? skills
    : skills.filter(skill => skill.status === stateFilter)

  const uniqueStates = Array.from(new Set(skills.map(s => s.status)))

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
        <p className="mt-4 text-text-secondary">加载技能列表中...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
          <h1 className="text-3xl font-bold text-text-primary mb-2">技能列表</h1>
          <p className="text-text-secondary">浏览和管理所有已采集的技能</p>
        </div>
        
        <div className="bg-warning/10 border border-warning/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-warning mb-2">接口未就绪</h3>
              <p className="text-sm text-text-secondary mb-4">{error}</p>
              <button
                onClick={loadSkills}
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors text-sm font-medium"
              >
                重试
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (skills.length === 0) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
          <h1 className="text-3xl font-bold text-text-primary mb-2">技能列表</h1>
          <p className="text-text-secondary">浏览和管理所有已采集的技能</p>
        </div>
        
        <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
          <span className="text-6xl mb-4 inline-block">🔍</span>
          <h3 className="text-xl font-semibold text-text-primary mb-2">暂无技能</h3>
          <p className="text-text-secondary mb-6">
            还没有采集任何技能。请先使用评估工具采集技能。
          </p>
          <Link
            href="/eval"
            className="inline-block px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors font-medium"
          >
            开始评估
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-text-primary mb-2">技能列表</h1>
            <p className="text-text-secondary">浏览和管理所有已采集的技能</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-primary">{total}</div>
            <div className="text-sm text-text-tertiary">总技能数</div>
          </div>
        </div>

        {/* State Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-text-secondary">筛选状态:</span>
          <button
            onClick={() => setStateFilter('all')}
            className={`px-3 py-1 text-sm font-medium rounded-full transition-colors ${
              stateFilter === 'all'
                ? 'bg-primary text-white'
                : 'bg-bg-card text-text-secondary hover:bg-border'
            }`}
          >
            全部 ({skills.length})
          </button>
          {uniqueStates.map((state) => (
            <button
              key={state}
              onClick={() => setStateFilter(state)}
              className={`px-3 py-1 text-sm font-medium rounded-full transition-colors ${
                stateFilter === state
                  ? 'bg-primary text-white'
                  : 'bg-bg-card text-text-secondary hover:bg-border'
              }`}
            >
              {STATE_LABELS[state] || state} ({skills.filter(s => s.status === state).length})
            </button>
          ))}
        </div>
      </div>

      {/* Skills Grid */}
      <div className="grid grid-cols-1 gap-4">
        {filteredSkills.map((skill) => (
          <Link
            key={skill.skill_id}
            href={`/skills/${skill.skill_id}`}
            className="block bg-white rounded-xl border border-border hover:border-primary hover:shadow-md transition-all p-6"
          >
            <div className="flex items-start gap-6">
              {/* Left: Main Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-text-primary truncate">
                    {skill.canonical_name}
                  </h3>
                  {skill.grade && <GradeBadge grade={skill.grade} />}
                </div>
                
                {skill.description && (
                  <p className="text-sm text-text-secondary line-clamp-2 mb-3">
                    {skill.description}
                  </p>
                )}

                <div className="flex items-center gap-4 flex-wrap">
                  {/* Status Badge */}
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded border ${
                      STATE_COLORS[skill.status] || 'bg-bg-card text-text-secondary border-border'
                    }`}
                  >
                    {STATE_LABELS[skill.status] || skill.status}
                  </span>

                  {/* Origin Link */}
                  {skill.origin_url && (
                    <a
                      href={skill.origin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-xs text-primary hover:text-primary-hover"
                    >
                      查看来源 →
                    </a>
                  )}
                </div>
              </div>

              {/* Right: Score */}
              <div className="flex-shrink-0 w-48">
                {skill.score_total !== null && skill.score_total !== undefined ? (
                  <div>
                    <div className="text-sm font-medium text-text-secondary mb-2">
                      综合评分
                    </div>
                    <ScoreBar score={skill.score_total} />
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <span className="text-sm text-text-tertiary">暂无评分</span>
                  </div>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Empty Filter Result */}
      {filteredSkills.length === 0 && stateFilter !== 'all' && (
        <div className="bg-white rounded-2xl border border-border p-12 shadow-sm text-center">
          <span className="text-4xl mb-4 inline-block">🔍</span>
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            该状态下暂无技能
          </h3>
          <p className="text-text-secondary mb-4">
            当前筛选条件下没有找到技能
          </p>
          <button
            onClick={() => setStateFilter('all')}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors text-sm font-medium"
          >
            查看全部
          </button>
        </div>
      )}
    </div>
  )
}
