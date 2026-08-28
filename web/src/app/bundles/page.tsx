'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

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

// Category to emoji mapping
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

const CATEGORY_COLORS: Record<string, { bg: string; hover: string; badge: string }> = {
  documentation: { bg: 'bg-[#165DFF]/10', hover: 'hover:bg-[#165DFF]/20', badge: 'bg-[#165DFF]/10 text-[#165DFF]' },
  security: { bg: 'bg-[#F53F3F]/10', hover: 'hover:bg-[#F53F3F]/20', badge: 'bg-[#F53F3F]/10 text-[#F53F3F]' },
  development: { bg: 'bg-[#00B42A]/10', hover: 'hover:bg-[#00B42A]/20', badge: 'bg-[#00B42A]/10 text-[#00B42A]' },
  productivity: { bg: 'bg-[#722ED1]/10', hover: 'hover:bg-[#722ED1]/20', badge: 'bg-[#722ED1]/10 text-[#722ED1]' },
  automation: { bg: 'bg-[#14C9C9]/10', hover: 'hover:bg-[#14C9C9]/20', badge: 'bg-[#14C9C9]/10 text-[#14C9C9]' },
  'data-science': { bg: 'bg-[#FF7D00]/10', hover: 'hover:bg-[#FF7D00]/20', badge: 'bg-[#FF7D00]/10 text-[#FF7D00]' },
  communication: { bg: 'bg-[#9FDB1D]/10', hover: 'hover:bg-[#9FDB1D]/20', badge: 'bg-[#9FDB1D]/10 text-[#9FDB1D]' },
  utilities: { bg: 'bg-[#86909C]/10', hover: 'hover:bg-[#86909C]/20', badge: 'bg-[#86909C]/10 text-[#86909C]' },
}

export default function BundlesPage() {
  const [bundles, setBundles] = useState<BundleSummary[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadBundles()
  }, [])

  const loadBundles = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/v1/bundles')
      
      if (!response.ok) {
        throw new Error('加载失败，请稍后重试')
      }
      
      const data: BundleListResponse = await response.json()
      setBundles(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  // Client-side filtering
  const filteredBundles = bundles.filter(bundle => {
    const query = searchQuery.toLowerCase()
    return (
      bundle.name.toLowerCase().includes(query) ||
      bundle.description.toLowerCase().includes(query)
    )
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-[#1D2129] mb-2">
              Bundle 推荐
            </h1>
            <p className="text-lg text-[#4E5969]">
              按场景发现 skill 组合，一站式解决复杂需求
            </p>
          </div>
          <Link
            href="/"
            className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
          >
            ← 返回首页
          </Link>
        </div>

        {/* Search Bar */}
        <div className="mt-6">
          <input
            type="text"
            placeholder="搜索 Bundle 名称或描述..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 border border-[#E5E6EB] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#165DFF] focus:border-transparent"
          />
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-[#165DFF] border-t-transparent"></div>
          <p className="mt-4 text-[#4E5969]">加载中...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-[#F53F3F]/10 border border-[#F53F3F]/20 rounded-2xl p-6">
          <p className="text-[#F53F3F] font-medium">❌ {error}</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredBundles.length === 0 && (
        <div className="bg-white rounded-2xl border border-[#E5E6EB] p-12 shadow-sm text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h3 className="text-xl font-semibold text-[#1D2129] mb-2">
            {searchQuery ? '未找到匹配的 Bundle' : '暂无 Bundle'}
          </h3>
          <p className="text-[#4E5969]">
            {searchQuery ? '尝试调整搜索关键词' : 'Bundle 数据正在完善中'}
          </p>
        </div>
      )}

      {/* Bundles Grid */}
      {!loading && !error && filteredBundles.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredBundles.map((bundle) => {
            const icon = CATEGORY_ICONS[bundle.category] || '📦'
            const colors = CATEGORY_COLORS[bundle.category] || CATEGORY_COLORS.utilities
            
            return (
              <Link
                key={bundle.bundle_id}
                href={`/bundles/${bundle.bundle_id}`}
                className={`block bg-white rounded-2xl border border-[#E5E6EB] p-6 shadow-sm hover:shadow-lg transition-all ${colors.hover}`}
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className={`text-4xl p-3 rounded-xl ${colors.bg}`}>
                    {icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-bold text-[#1D2129] mb-1">
                      {bundle.name}
                    </h3>
                    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${colors.badge}`}>
                      {bundle.category}
                    </span>
                  </div>
                </div>

                <p className="text-sm text-[#4E5969] mb-4 line-clamp-2">
                  {bundle.description}
                </p>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-[#86909C]">
                    查看包含的技能
                  </span>
                  <span className="text-[#165DFF] text-sm font-medium">
                    查看详情 →
                  </span>
                </div>
              </Link>
            )
          })}
        </div>
      )}

      {/* Info Section */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-xl font-bold text-[#1D2129] mb-4">
          关于 Bundle
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              什么是 Bundle？
            </h3>
            <p className="text-sm text-[#4E5969]">
              Bundle 是一组针对特定场景精心组合的 AI Skills。每个 Bundle 聚焦一个具体的工作流或业务场景，包含完成该场景所需的全部技能，让您无需逐个寻找，一次性获得完整解决方案。
            </p>
          </div>

          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              如何选择适合的 Bundle？
            </h3>
            <p className="text-sm text-[#4E5969]">
              根据您的实际需求场景选择 Bundle。点击 Bundle 卡片查看详情，了解包含的具体技能和适用场景。每个技能都经过评分和测试，您可以进一步查看单个技能的详细信息和评测报告。
            </p>
          </div>

          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              Bundle 推荐原则
            </h3>
            <p className="text-sm text-[#4E5969]">
              我们的 Bundle 基于真实业务场景设计，优先选择高质量、经过验证的技能。每个 Bundle 中的技能相互补充，覆盖场景的不同环节，帮助您构建完整的自动化工作流。
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="text-center py-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-[#165DFF] text-white rounded-full hover:bg-[#4080FF] transition-colors font-medium"
        >
          返回首页
        </Link>
      </div>
    </div>
  )
}
