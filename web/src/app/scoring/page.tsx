'use client'

import Link from 'next/link'

export default function ScoringGuidePage() {
  const dimensions = [
    {
      name: 'Accuracy',
      nameCn: '准确性',
      weight: '30%',
      icon: '🎯',
      description: '代码质量和测试覆盖程度',
      factors: [
        'README 文档完整性',
        '测试用例覆盖率',
        '持续集成（CI）配置',
        '项目清单文件（manifest）',
        '示例代码和使用文档',
      ],
      calculation: '评估项目的文档完整性和测试覆盖程度。拥有完善的 README、充分的测试用例和持续集成配置的项目得分更高。',
    },
    {
      name: 'Reliability',
      nameCn: '可靠性',
      weight: '30%',
      icon: '🔧',
      description: '依赖管理和开发规范',
      factors: [
        '依赖清单和锁文件',
        'Git 忽略配置（.gitignore）',
        '构建工具配置（Makefile）',
        '代码类型提示覆盖率',
        '代码检查工具配置（lint）',
      ],
      calculation: '评估项目的依赖管理和代码规范程度。使用依赖锁文件、类型提示和代码检查工具的项目更可靠。',
    },
    {
      name: 'Security',
      nameCn: '安全性',
      weight: '20%',
      icon: '🔒',
      description: '代码安全和隐私保护',
      factors: [
        '无硬编码密钥和敏感信息',
        '无 .env 文件泄露',
        '代码中 TODO/FIXME 数量',
        '安全政策文档（SECURITY.md）',
        '依赖版本锁定',
      ],
      calculation: '检查项目是否存在密钥泄露、敏感信息暴露等安全风险。从 100 分开始扣分，避免硬编码密钥和提供安全政策文档可提升得分。',
    },
    {
      name: 'Performance',
      nameCn: '性能',
      weight: '20%',
      icon: '⚡',
      description: '部署优化和异步处理能力',
      factors: [
        '容器化配置（Dockerfile）',
        '编排配置（docker-compose）',
        '构建优化配置（next.config.js 等）',
        '依赖数量控制',
        '异步编程模式使用',
      ],
      calculation: '评估项目的部署便利性和代码执行效率。使用 Docker 容器化、减少依赖数量、采用异步编程的项目性能更优。',
    },
  ]

  const grades = [
    { level: 'A', color: 'bg-[#00B42A]', threshold: '≥90', label: '优秀' },
    { level: 'B', color: 'bg-[#165DFF]', threshold: '≥75', label: '良好' },
    { level: 'C', color: 'bg-[#FF7D00]', threshold: '≥60', label: '及格' },
    { level: 'D', color: 'bg-[#F53F3F]', threshold: '≥40', label: '需改进' },
    { level: 'U', color: 'bg-[#86909C]', threshold: '<40', label: '不合格' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-[#1D2129] mb-2">
              评分体系说明
            </h1>
            <p className="text-lg text-[#4E5969]">
              我们如何评估 AI Skill 的质量
            </p>
          </div>
          <Link
            href="/"
            className="text-[#165DFF] hover:text-[#4080FF] text-sm font-medium"
          >
            ← 返回首页
          </Link>
        </div>

        <div className="p-6 bg-[#F5F7FA] rounded-xl">
          <h3 className="text-base font-semibold text-[#1D2129] mb-3">
            总分计算公式
          </h3>
          <p className="text-[#4E5969] mb-4 font-mono text-sm">
            总分 = 准确性 × 30% + 可靠性 × 30% + 安全性 × 20% + 性能 × 20%
          </p>
          <p className="text-sm text-[#86909C]">
            每个维度满分 100 分，加权计算后得到总分（0-100 分），再映射到等级（A/B/C/D/U）。
          </p>
        </div>
      </div>

      {/* Dimensions */}
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-[#1D2129]">
          四大评分维度
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {dimensions.map((dim, idx) => (
            <div
              key={idx}
              className="bg-white rounded-2xl border border-[#E5E6EB] p-6 shadow-sm"
            >
              <div className="flex items-start gap-4 mb-4">
                <div className="text-4xl">{dim.icon}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-xl font-bold text-[#1D2129]">
                      {dim.nameCn} <span className="text-[#86909C] text-sm font-normal">/ {dim.name}</span>
                    </h3>
                    <span className="px-3 py-1 bg-[#165DFF]/10 text-[#165DFF] rounded-full text-sm font-medium">
                      权重 {dim.weight}
                    </span>
                  </div>
                  <p className="text-[#4E5969] mb-4">
                    {dim.description}
                  </p>
                </div>
              </div>

              <div className="mb-4">
                <h4 className="text-sm font-semibold text-[#1D2129] mb-2">
                  评分因素：
                </h4>
                <ul className="space-y-1">
                  {dim.factors.map((factor, i) => (
                    <li key={i} className="text-sm text-[#4E5969] flex items-start gap-2">
                      <span className="text-[#165DFF] mt-1">•</span>
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-4 border-t border-[#E5E6EB]">
                <p className="text-sm text-[#86909C]">
                  {dim.calculation}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Grades */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-2xl font-bold text-[#1D2129] mb-6">
          等级划分标准
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {grades.map((grade, idx) => (
            <div
              key={idx}
              className="text-center p-4 bg-[#F5F7FA] rounded-xl"
            >
              <div className={`inline-flex items-center justify-center w-16 h-16 ${grade.color} text-white rounded-full text-2xl font-bold mb-3`}>
                {grade.level}
              </div>
              <div className="text-sm font-semibold text-[#1D2129] mb-1">
                {grade.label}
              </div>
              <div className="text-xs text-[#86909C] font-mono">
                {grade.threshold} 分
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 p-4 bg-[#E8F3FF] rounded-xl">
          <p className="text-sm text-[#165DFF]">
            💡 <strong>提示：</strong>等级评定基于总分，综合考量四个维度的加权得分。A 级项目代表行业最佳实践，D 级及以下需要重点改进。
          </p>
        </div>
      </div>

      {/* Technical Details */}
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h2 className="text-2xl font-bold text-[#1D2129] mb-6">
          技术说明
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              评分引擎
            </h3>
            <p className="text-sm text-[#4E5969]">
              我们使用静态代码分析技术扫描项目，提取质量指标（metrics），通过加权计算得到各维度分数。
              评分引擎完全开源，遵循确定性算法，相同项目的评分结果保持一致。
            </p>
          </div>

          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              扫描范围
            </h3>
            <p className="text-sm text-[#4E5969]">
              扫描器会分析项目的文件结构、配置文件、代码模式、安全信号等。
              自动跳过 node_modules、.git 等无关目录，专注于源代码和配置文件的质量评估。
            </p>
          </div>

          <div>
            <h3 className="text-base font-semibold text-[#1D2129] mb-2">
              持续改进
            </h3>
            <p className="text-sm text-[#4E5969]">
              评分体系会根据社区反馈和行业最佳实践持续优化。如果您有改进建议，欢迎在 GitHub 提交 Issue 或 Pull Request。
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
