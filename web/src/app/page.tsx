'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import ScoreBar from '@/components/skill/ScoreBar'

interface SkillSummary {
  skill_id: string
  canonical_name: string
  status: string
  evidence_grade: string
  description: string | null
  origin_url: string
  score_total?: number | null
  grade?: string | null
}

interface HistoryItem {
  id: number
  repo_url: string
  score_total: number
  grade: string
  scanned_at: string
}

export default function HomePage() {
  const [query, setQuery] = useState('')
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(false)

  // 页面加载时自动获取所有技能和历史记录
  useEffect(() => {
    loadSkills()
    loadHistory()
  }, [])

  const loadSkills = async (searchQuery: string = '') => {
    setLoading(true)
    try {
      const queryParam = searchQuery ? `?q=${encodeURIComponent(searchQuery)}&limit=20` : '?limit=20'
      const response = await fetch(`/api/skills${queryParam}`)
      const data = await response.json()
      setSkills(data)
    } catch (error) {
      console.error('加载失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    try {
      const response = await fetch('/api/v1/eval/history?limit=6')
      const data = await response.json()
      setHistory(data.results || [])
    } catch (error) {
      console.error('加载历史失败:', error)
    }
  }

  const handleSearch = () => {
    loadSkills(query)
  }

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl font-bold text-[#1D2129] mb-4">
            AI Skill 评测平台
          </h1>
          <p className="text-lg text-[#4E5969] mb-8">
            发现、评估并对比各平台的 AI Skills
          </p>
          
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="按名称或描述搜索..."
              className="flex-1 px-4 py-3 bg-white border border-[#E5E6EB] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#165DFF] focus:border-[#165DFF] text-[#1D2129]"
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="px-8 py-3 bg-[#165DFF] text-white rounded-full hover:bg-[#4080FF] disabled:opacity-50 font-medium transition-colors"
            >
              {loading ? '搜索中...' : '搜索'}
            </button>
          </div>
        </div>
      </div>

      {/* Skills Grid */}
      <div>
        <h2 className="text-2xl font-bold text-[#1D2129] mb-6">
          已评估工具 {skills.length > 0 && `(${skills.length})`}
        </h2>

        {skills.length === 0 && !loading && (
          <div className="text-center text-[#86909C] py-16 bg-white rounded-2xl border border-[#E5E6EB]">
            暂无结果。可输入技能名称搜索，或点击&ldquo;搜索&rdquo;查看全部。
          </div>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {skills.map((skill) => (
            <Link 
              key={skill.skill_id} 
              href={`/skills/${skill.skill_id}`}
              className="block bg-white rounded-2xl border border-[#E5E6EB] p-6 shadow-sm hover:shadow-md hover:border-[#165DFF] transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3 flex-1">
                  <div className="w-10 h-10 rounded-full bg-[#165DFF]/8 flex items-center justify-center">
                    <span className="text-[#165DFF] font-semibold text-sm">
                      {skill.canonical_name.substring(0, 2).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-[#1D2129] truncate">
                      {skill.canonical_name}
                    </h3>
                  </div>
                  <GradeBadge grade={skill.grade} />
                </div>
              </div>
              
              {skill.description && (
                <p className="text-sm text-[#4E5969] mb-4 line-clamp-2">
                  {skill.description}
                </p>
              )}
              
              <div className="space-y-2">
                <ScoreBar score={skill.score_total} />
                <div className="flex items-center gap-2 text-xs text-[#86909C]">
                  <span>{skill.status}</span>
                  <span>•</span>
                  <span>证据等级: {skill.evidence_grade}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* History Section */}
      {history.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-[#1D2129]">
              历史记录 ({history.length})
            </h2>
            <Link 
              href="/eval" 
              className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
            >
              查看全部 →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {history.map((item) => (
              <Link
                key={item.id}
                href={`/eval/compare?ids=${item.id}`}
                className="block bg-white rounded-xl border border-[#E5E6EB] p-4 hover:shadow-md hover:border-[#165DFF] transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex-1 min-w-0 mr-3">
                    <p className="text-sm font-medium text-[#1D2129] truncate">
                      {item.repo_url.replace('https://github.com/', '').replace('uploaded:', '上传: ')}
                    </p>
                  </div>
                  <GradeBadge grade={item.grade} />
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-[#165DFF]">
                      {item.score_total.toFixed(1)}
                    </p>
                  </div>
                  <div className="text-xs text-[#86909C]">
                    {new Date(item.scanned_at).toLocaleDateString('zh-CN')}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
