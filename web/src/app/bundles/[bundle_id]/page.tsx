'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'

interface Bundle {
  bundle_id: string
  name: string
  description: string
  category: string
  skill_ids: string[]
  tags: string[]
}

interface SkillSummary {
  skill_id: string
  canonical_name: string
  status: string
  description: string | null
  grade?: string | null
  score_total?: number | null
  origin_url: string
}

const CATEGORY_ICONS: Record<string, string> = {
  documentation: '📄',
  security: '🔒',
  development: '💻',
  productivity: '⚡',
  automation: '🤖',
  'data-science': '📊',
  communication: '💬',
  utilities: '🔧',
}

export default function BundleDetailPage({
  params,
}: {
  params: { bundle_id: string }
}) {
  const [bundle, setBundle] = useState<Bundle | null>(null)
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [skillsLoading, setSkillsLoading] = useState(false)

  useEffect(() => {
    loadBundle()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.bundle_id])

  const loadBundle = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/v1/bundles/${params.bundle_id}`)
      
      if (response.status === 404) {
        setError('Bundle 不存在')
        setLoading(false)
        return
      }
      
      if (!response.ok) {
        throw new Error('加载失败，请稍后重试')
      }
      
      const data: Bundle = await response.json()
      setBundle(data)
      
      // Load skills
      loadSkills(data.skill_ids)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const loadSkills = async (skillIds: string[]) => {
    setSkillsLoading(true)
    const loadedSkills: SkillSummary[] = []
    
    for (const skillId of skillIds) {
      try {
        const response = await fetch(`/api/v1/skills/${skillId}`)
        if (response.ok) {
          const data = await response.json()
          // Extract summary from full detail response
          loadedSkills.push({
            skill_id: data.summary?.skill_id || skillId,
            canonical_name: data.summary?.canonical_name || 'Unknown Skill',
            status: data.summary?.status || 'unknown',
            description: data.summary?.description || null,
            grade: data.summary?.grade || null,
            score_total: data.summary?.score_total || null,
            origin_url: data.summary?.origin_url || '',
          })
        }
      } catch (err) {
        // console.error(`Failed to load skill ${skillId}:`, err)
        // Add placeholder for failed skill
        loadedSkills.push({
          skill_id: skillId,
          canonical_name: '技能信息暂不可用',
          status: 'unknown',
          description: null,
          grade: null,
          score_total: null,
          origin_url: '',
        })
      }
    }
    
    setSkills(loadedSkills)
    setSkillsLoading(false)
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-12 shadow-sm text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#165DFF] border-t-transparent"></div>
        <p className="mt-4 text-[#4E5969]">加载中...</p>
      </div>
    )
  }

  if (error || !bundle) {
    return (
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-[#F53F3F]">Bundle Not Found</h1>
        <p className="mt-2 text-[#4E5969]">
          {error || 'The requested bundle does not exist.'}
        </p>
        <Link
          href="/bundles"
          className="inline-block mt-4 text-[#165DFF] hover:text-[#4080FF] font-medium"
        >
          ← 返回 Bundle 列表
        </Link>
      </div>
    )
  }

  const icon = CATEGORY_ICONS[bundle.category] || '📦'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-start gap-6 mb-6">
          <div className={`text-6xl p-4 rounded-2xl bg-[#165DFF]/10`}>
            {icon}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-[#1D2129]">
                {bundle.name}
              </h1>
              <span className="px-3 py-1 text-xs font-medium rounded-full bg-[#165DFF]/10 text-[#165DFF]">
                {bundle.category}
              </span>
            </div>
            <p className="text-lg text-[#4E5969] mb-4">
              {bundle.description}
            </p>
            <div className="flex flex-wrap gap-2">
              {bundle.tags.map((tag, idx) => (
                <span
                  key={idx}
                  className="px-3 py-1 text-xs font-medium rounded-full bg-[#86909C]/10 text-[#86909C]"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-[#E5E6EB]">
          <Link
            href="/bundles"
            className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
          >
            ← 返回 Bundle 列表
          </Link>
          <span className="text-sm text-[#86909C]">
            包含 {bundle.skill_ids.length} 个技能
          </span>
        </div>
      </div>

      {/* Skills List */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-xl font-bold text-[#1D2129] mb-6">
          包含的技能
        </h2>

        {skillsLoading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-[#165DFF] border-t-transparent"></div>
            <p className="mt-2 text-sm text-[#4E5969]">加载技能信息...</p>
          </div>
        )}

        {!skillsLoading && skills.length === 0 && (
          <p className="text-[#86909C] text-center py-8">暂无技能信息</p>
        )}

        {!skillsLoading && skills.length > 0 && (
          <div className="space-y-4">
            {skills.map((skill, idx) => (
              <div
                key={skill.skill_id}
                className="p-6 border border-[#E5E6EB] rounded-xl hover:border-[#165DFF] hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-sm font-medium text-[#86909C]">
                        #{idx + 1}
                      </span>
                      <h3 className="text-lg font-semibold text-[#1D2129]">
                        {skill.canonical_name}
                      </h3>
                      {skill.grade && <GradeBadge grade={skill.grade} />}
                    </div>
                    {skill.description && (
                      <p className="text-sm text-[#4E5969] mb-3">
                        {skill.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        skill.status === 'NEUTRAL_TESTED' 
                          ? 'bg-[#00B42A]/10 text-[#00B42A]' 
                          : 'bg-[#86909C]/10 text-[#86909C]'
                      }`}>
                        {skill.status}
                      </span>
                      {skill.score_total !== null && skill.score_total !== undefined && (
                        <span className="text-sm text-[#165DFF] font-medium">
                          评分: {skill.score_total.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>
                  {skill.origin_url ? (
                    <Link
                      href={`/skills/${skill.skill_id}`}
                      className="px-4 py-2 bg-[#165DFF] text-white text-sm rounded-full hover:bg-[#4080FF] transition-colors font-medium whitespace-nowrap"
                    >
                      查看详情 →
                    </Link>
                  ) : (
                    <span className="px-4 py-2 bg-[#86909C]/10 text-[#86909C] text-sm rounded-full font-medium whitespace-nowrap">
                      暂不可用
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Usage Tips */}
      <div className="bg-gradient-to-r from-[#165DFF]/5 to-[#722ED1]/5 rounded-2xl border border-[#165DFF]/20 p-8">
        <h3 className="text-lg font-semibold text-[#1D2129] mb-4">
          💡 使用建议
        </h3>
        <div className="space-y-2 text-sm text-[#4E5969]">
          <p>
            • 点击每个技能的&ldquo;查看详情&rdquo;按钮，了解技能的具体功能、评分和安全性
          </p>
          <p>
            • 建议按顺序使用 Bundle 中的技能，以实现完整的工作流
          </p>
          <p>
            • 如果某个技能评分较低，请谨慎使用，或查看详细评测报告了解风险
          </p>
          <p>
            • 您可以根据实际需求选择性使用 Bundle 中的部分技能
          </p>
        </div>
      </div>
    </div>
  )
}
