'use client'

import Link from 'next/link'

export default function CategoriesPage() {
  // 硬编码分类列表（当样本数据有 category_tags 后，可从 API 获取）
  const categories = [
    {
      name: '文档处理',
      slug: 'documentation',
      icon: '📄',
      description: '处理文档、生成报告、内容编辑等',
      color: 'bg-[#165DFF]/10',
      hoverColor: 'hover:bg-[#165DFF]/20',
      count: 0, // 当前样本无分类数据
    },
    {
      name: '代码开发',
      slug: 'development',
      icon: '💻',
      description: '代码审查、自动化开发、重构工具等',
      color: 'bg-[#00B42A]/10',
      hoverColor: 'hover:bg-[#00B42A]/20',
      count: 0,
    },
    {
      name: '数据分析',
      slug: 'analytics',
      icon: '📊',
      description: '数据处理、统计分析、可视化等',
      color: 'bg-[#FF7D00]/10',
      hoverColor: 'hover:bg-[#FF7D00]/20',
      count: 0,
    },
    {
      name: '生产力工具',
      slug: 'productivity',
      icon: '⚡',
      description: '邮件管理、日历同步、任务自动化等',
      color: 'bg-[#722ED1]/10',
      hoverColor: 'hover:bg-[#722ED1]/20',
      count: 0,
    },
    {
      name: '安全合规',
      slug: 'security',
      icon: '🔒',
      description: '安全检查、漏洞扫描、合规验证等',
      color: 'bg-[#F53F3F]/10',
      hoverColor: 'hover:bg-[#F53F3F]/20',
      count: 0,
    },
    {
      name: '测试部署',
      slug: 'testing',
      icon: '🚀',
      description: 'CI/CD、自动化测试、容器化部署等',
      color: 'bg-[#14C9C9]/10',
      hoverColor: 'hover:bg-[#14C9C9]/20',
      count: 0,
    },
    {
      name: '内容创作',
      slug: 'content',
      icon: '✍️',
      description: '文本生成、翻译、创意写作等',
      color: 'bg-[#F7BA1E]/10',
      hoverColor: 'hover:bg-[#F7BA1E]/20',
      count: 0,
    },
    {
      name: '通信协作',
      slug: 'communication',
      icon: '💬',
      description: '消息推送、团队协作、通知管理等',
      color: 'bg-[#9FDB1D]/10',
      hoverColor: 'hover:bg-[#9FDB1D]/20',
      count: 0,
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-[#1D2129] mb-2">
              按分类浏览
            </h1>
            <p className="text-lg text-[#4E5969]">
              探索不同类别的 AI Skills
            </p>
          </div>
          <Link
            href="/"
            className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
          >
            ← 返回首页
          </Link>
        </div>

        <div className="p-4 bg-[#E8F3FF] rounded-xl">
          <p className="text-sm text-[#165DFF]">
            💡 <strong>提示：</strong>当前为预览版本，分类数据正在完善中。点击分类查看对应技能。
          </p>
        </div>
      </div>

      {/* Categories Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {categories.map((category, idx) => (
          <Link
            key={idx}
            href={`/?category=${encodeURIComponent(category.slug)}`}
            className={`block bg-white rounded-2xl border border-[#E5E6EB] p-6 shadow-sm hover:shadow-lg transition-all ${category.hoverColor}`}
          >
            <div className="flex items-start gap-4 mb-4">
              <div className={`text-4xl p-3 rounded-xl ${category.color}`}>
                {category.icon}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-bold text-[#1D2129] mb-1">
                  {category.name}
                </h3>
                {category.count > 0 && (
                  <span className="text-sm text-[#86909C]">
                    {category.count} 个技能
                  </span>
                )}
              </div>
            </div>

            <p className="text-sm text-[#4E5969] mb-4">
              {category.description}
            </p>

            <div className="flex items-center text-[#165DFF] text-sm font-medium">
              查看技能 →
            </div>
          </Link>
        ))}
      </div>

      {/* Info Section */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-xl font-bold text-[#1D2129] mb-4">
          关于分类
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              分类标准
            </h3>
            <p className="text-sm text-[#4E5969]">
              我们根据 AI Skill 的主要用途和应用场景进行分类。一个 Skill 可能属于多个分类，我们会根据其核心功能归类到最相关的类别。
            </p>
          </div>

          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              如何选择
            </h3>
            <p className="text-sm text-[#4E5969]">
              点击感兴趣的分类卡片，系统会为您展示该类别下的所有技能。您可以进一步查看详情、评分和使用说明。
            </p>
          </div>

          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              数据说明
            </h3>
            <p className="text-sm text-[#4E5969]">
              当前平台处于早期阶段，分类数据正在持续完善。未来会支持更细粒度的分类和标签筛选功能。
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
