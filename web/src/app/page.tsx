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
  const [sortBy, setSortBy] = useState('score')  // 'score' or 'recent'
  const [page, setPage] = useState(1)
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [total, setTotal] = useState(0)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(false)

  const limit = 20

  // 页面加载时自动获取所有技能和历史记录
  useEffect(() => {
    loadSkills()
    loadHistory()
  }, [])

  // 当排序或分页变化时重新加载
  useEffect(() => {
    loadSkills()
  }, [sortBy, page])

  const loadSkills = async (searchQuery: string = query) => {
    setLoading(true)
    try {
      const offset = (page - 1) * limit
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
        sort_by: sortBy,
      })
      if (searchQuery) {
        params.set('q', searchQuery)
      }
      
      const response = await fetch(`/api/v1/skills?${params.toString()}`)
      const data = await response.json()
      
      // Handle both old (array) and new ({items, total}) response format
      if (Array.isArray(data)) {
        setSkills(data)
        setTotal(data.length)
      } else {
        setSkills(data.items || [])
        setTotal(data.total || 0)
      }
    } catch (error) {
      console.error('加载失败:', error)
      setSkills([])
      setTotal(0)
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
    setPage(1)  // Reset to first page on new search
    loadSkills(query)
  }

  const handleSortChange = (newSort: string) => {
    setSortBy(newSort)
    setPage(1)  // Reset to first page on sort change
  }

  const totalPages = Math.ceil(total / limit)
  const startItem = total === 0 ? 0 : (page - 1) * limit + 1
  const endItem = Math.min(page * limit, total)

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

      {/* Filter and Sort Bar */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-4 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-[#4E5969]">
            <span>共 {total} 个技能</span>
          </div>
          
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#4E5969]">排序：</span>
            <select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
              className="px-3 py-2 bg-white border border-[#E5E6EB] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#165DFF] focus:border-[#165DFF] text-sm text-[#1D2129] cursor-pointer"
              disabled={loading}
            >
              <option value="score">综合评分 ↓</option>
              <option value="recent">最新评测</option>
            </select>
          </div>
        </div>
      </div>

      {/* Skills Grid */}
      <div>
        <h2 className="text-2xl font-bold text-[#1D2129] mb-6">
          已评估工具
        </h2>

        {skills.length === 0 && !loading && (
          <div className="text-center text-[#86909C] py-16 bg-white rounded-2xl border border-[#E5E6EB]">
            <p className="mb-4">暂无符合条件的技能</p>
            {query && (
              <button
                onClick={() => {
                  setQuery('')
                  setPage(1)
                  loadSkills('')
                }}
                className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
              >
                重置筛选条件
              </button>
            )}
          </div>
        )}
        
        {loading && skills.length === 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, idx) => (
              <div
                key={idx}
                className="bg-white rounded-2xl border border-[#E5E6EB] p-6 shadow-sm animate-pulse"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3 flex-1">
                    <div className="w-10 h-10 rounded-full bg-[#E5E6EB]"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-[#E5E6EB] rounded w-3/4"></div>
                    </div>
                  </div>
                </div>
                <div className="space-y-2 mt-4">
                  <div className="h-3 bg-[#E5E6EB] rounded"></div>
                  <div className="h-3 bg-[#E5E6EB] rounded w-5/6"></div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {!loading && skills.map((skill) => (
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

        {/* Pagination */}
        {total > limit && (
          <div className="mt-8 flex items-center justify-between bg-white rounded-2xl border border-[#E5E6EB] p-4 shadow-sm">
            <div className="text-sm text-[#4E5969]">
              第 {startItem}-{endItem} 条，共 {total} 个
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1 || loading}
                className="px-4 py-2 border border-[#E5E6EB] rounded-lg text-sm font-medium text-[#1D2129] hover:bg-[#F5F7FA] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                上一页
              </button>
              
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum: number
                  if (totalPages <= 5) {
                    pageNum = i + 1
                  } else if (page <= 3) {
                    pageNum = i + 1
                  } else if (page >= totalPages - 2) {
                    pageNum = totalPages - 4 + i
                  } else {
                    pageNum = page - 2 + i
                  }
                  
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      disabled={loading}
                      className={`min-w-[40px] h-10 rounded-lg text-sm font-medium transition-colors ${
                        pageNum === page
                          ? 'bg-[#165DFF] text-white'
                          : 'text-[#1D2129] hover:bg-[#F5F7FA]'
                      } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      {pageNum}
                    </button>
                  )
                })}
              </div>
              
              <button
                onClick={() => setPage(page + 1)}
                disabled={page === totalPages || loading}
                className="px-4 py-2 border border-[#E5E6EB] rounded-lg text-sm font-medium text-[#1D2129] hover:bg-[#F5F7FA] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                下一页
              </button>
            </div>
          </div>
        )}
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
