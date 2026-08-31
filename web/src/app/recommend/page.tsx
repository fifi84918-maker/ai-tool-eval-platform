'use client'

import { useState } from 'react'
import GradeBadge from '@/components/skill/GradeBadge'

// Types aligned with backend RecommendationResponse
interface SkillMetric {
  name: string
  value: number
  description: string
}

interface RecommendedSkill {
  name: string
  grade: string
  score_total: number
  metrics: SkillMetric[]
}

interface RuleFinding {
  rule_id: string
  title: string
  message: string
  level: 'pass' | 'warning' | 'block'
}

interface RecommendationItem {
  bundle_id: string
  tier: 'starter' | 'standard' | 'enterprise'
  score: number
  match_reasons: string[]
  rule_findings: RuleFinding[]
  skills: RecommendedSkill[]
}

interface RecommendationResponse {
  profile_id: string
  profile_name: string
  total: number
  items: RecommendationItem[]
}

// Mock data for V1A - matching backend structure
const MOCK_RECOMMENDATIONS: RecommendationResponse = {
  profile_id: 'mock-profile-001',
  profile_name: 'Web开发项目',
  total: 3,
  items: [
    {
      bundle_id: 'starter-web-dev',
      tier: 'starter',
      score: 85.5,
      match_reasons: [
        '适合小型 Web 项目和个人开发',
        '包含基础的文档和开发工具',
        '所有技能均为轻量级，启动快',
      ],
      rule_findings: [
        { rule_id: 'R001', title: '安全等级', message: '所有技能通过基础安全检查', level: 'pass' },
        { rule_id: 'R002', title: '性能', message: '平均性能评分 85+', level: 'pass' },
      ],
      skills: [
        {
          name: 'markdown-preview',
          grade: 'A',
          score_total: 92.0,
          metrics: [
            { name: 'accuracy', value: 95, description: '渲染准确性高' },
            { name: 'security', value: 89, description: '无已知漏洞' },
          ],
        },
        {
          name: 'code-formatter',
          grade: 'B',
          score_total: 88.0,
          metrics: [
            { name: 'reliability', value: 90, description: '格式化稳定' },
            { name: 'performance', value: 86, description: '处理速度快' },
          ],
        },
      ],
    },
    {
      bundle_id: 'standard-web-dev',
      tier: 'standard',
      score: 92.0,
      match_reasons: [
        '适合中型团队协作项目',
        '包含完整的开发、测试和部署工具链',
        '支持多语言和跨域需求',
        '安全性和可靠性均达到企业级标准',
      ],
      rule_findings: [
        { rule_id: 'R001', title: '安全等级', message: '所有技能通过企业级安全检查', level: 'pass' },
        { rule_id: 'R002', title: '性能', message: '平均性能评分 90+', level: 'pass' },
        { rule_id: 'R003', title: '兼容性', message: '跨平台兼容性良好', level: 'pass' },
      ],
      skills: [
        {
          name: 'api-client',
          grade: 'A',
          score_total: 94.5,
          metrics: [
            { name: 'reliability', value: 96, description: 'HTTP请求稳定' },
            { name: 'security', value: 93, description: 'SSL/TLS 支持' },
          ],
        },
        {
          name: 'test-runner',
          grade: 'A',
          score_total: 91.0,
          metrics: [
            { name: 'accuracy', value: 92, description: '测试覆盖全面' },
            { name: 'performance', value: 90, description: '执行速度快' },
          ],
        },
        {
          name: 'deployment-helper',
          grade: 'B',
          score_total: 87.5,
          metrics: [
            { name: 'reliability', value: 88, description: '部署成功率高' },
            { name: 'security', value: 87, description: '密钥管理安全' },
          ],
        },
      ],
    },
    {
      bundle_id: 'enterprise-web-dev',
      tier: 'enterprise',
      score: 96.5,
      match_reasons: [
        '企业级全栈开发解决方案',
        '包含高级安全扫描和合规检查工具',
        '支持大规模团队协作和 CI/CD 流水线',
        '提供监控、日志和性能分析',
        '所有技能均为 A/B 级，可靠性 95%+',
      ],
      rule_findings: [
        { rule_id: 'R001', title: '安全等级', message: '通过最高级别安全审计', level: 'pass' },
        { rule_id: 'R002', title: '性能', message: '所有技能性能评分 95+', level: 'pass' },
        { rule_id: 'R003', title: '合规性', message: '符合 GDPR/SOC2 标准', level: 'pass' },
        { rule_id: 'R004', title: '可扩展性', message: '支持微服务架构', level: 'pass' },
      ],
      skills: [
        {
          name: 'security-scanner',
          grade: 'A',
          score_total: 98.0,
          metrics: [
            { name: 'accuracy', value: 99, description: '漏洞检测准确' },
            { name: 'security', value: 97, description: '零误报' },
          ],
        },
        {
          name: 'monitoring-agent',
          grade: 'A',
          score_total: 96.0,
          metrics: [
            { name: 'reliability', value: 98, description: '7x24 稳定运行' },
            { name: 'performance', value: 94, description: '低资源占用' },
          ],
        },
        {
          name: 'ci-cd-pipeline',
          grade: 'A',
          score_total: 95.0,
          metrics: [
            { name: 'reliability', value: 97, description: '自动化流程可靠' },
            { name: 'performance', value: 93, description: '构建速度快' },
          ],
        },
        {
          name: 'log-aggregator',
          grade: 'B',
          score_total: 92.0,
          metrics: [
            { name: 'performance', value: 94, description: '日志处理高效' },
            { name: 'accuracy', value: 90, description: '数据完整性好' },
          ],
        },
      ],
    },
  ],
}

export default function RecommendPage() {
  const [profileName, setProfileName] = useState('')
  const [domains, setDomains] = useState<string[]>([])
  const [languages, setLanguages] = useState<string[]>([])
  const [securityRequirement, setSecurityRequirement] = useState<string>('standard')
  const [showResults, setShowResults] = useState(false)

  // Available options
  const DOMAIN_OPTIONS = ['web', 'mobile', 'data-science', 'devops', 'security', 'documentation']
  const LANGUAGE_OPTIONS = ['javascript', 'python', 'java', 'go', 'rust', 'typescript']
  const SECURITY_OPTIONS = [
    { value: 'low', label: '低（个人项目）' },
    { value: 'standard', label: '标准（团队项目）' },
    { value: 'high', label: '高（企业级）' },
  ]

  const handleDomainToggle = (domain: string) => {
    setDomains(prev =>
      prev.includes(domain) ? prev.filter(d => d !== domain) : [...prev, domain]
    )
  }

  const handleLanguageToggle = (lang: string) => {
    setLanguages(prev =>
      prev.includes(lang) ? prev.filter(l => l !== lang) : [...prev, lang]
    )
  }

  const handleSubmit = () => {
    // V1A: Just log to console, don't call real API
    const requestBody = {
      profile_name: profileName,
      domains,
      languages,
      security_requirement: securityRequirement,
    }
    console.log('🚀 推荐请求体:', JSON.stringify(requestBody, null, 2))
    
    // Show mock results
    setShowResults(true)
  }

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case 'starter':
        return 'bg-success/10 text-success border-success/20'
      case 'standard':
        return 'bg-primary/10 text-primary border-primary/20'
      case 'enterprise':
        return 'bg-purple/10 text-purple border-purple/20'
      default:
        return 'bg-text-tertiary/10 text-text-tertiary border-border'
    }
  }

  const getTierLabel = (tier: string) => {
    switch (tier) {
      case 'starter':
        return '入门版'
      case 'standard':
        return '标准版'
      case 'enterprise':
        return '企业版'
      default:
        return tier
    }
  }

  return (
    <div className="space-y-8">
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-text-primary mb-2">技能推荐</h1>
        <p className="text-text-secondary">根据项目画像为您推荐最合适的技能组合</p>
      </div>

      {/* Input Section */}
      <div className="bg-white rounded-2xl border border-border p-8 shadow-sm">
        <h2 className="text-xl font-semibold text-text-primary mb-6">项目画像</h2>
        
        <div className="space-y-6">
          {/* Project Name */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              项目名称
            </label>
            <input
              type="text"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              placeholder="例如：电商平台后端服务"
              className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>

          {/* Domains (Multi-select) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              应用领域 (多选)
            </label>
            <div className="flex flex-wrap gap-2">
              {DOMAIN_OPTIONS.map((domain) => (
                <button
                  key={domain}
                  onClick={() => handleDomainToggle(domain)}
                  className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                    domains.includes(domain)
                      ? 'bg-primary text-white'
                      : 'bg-bg-card text-text-secondary hover:bg-border'
                  }`}
                >
                  {domain}
                </button>
              ))}
            </div>
          </div>

          {/* Languages (Multi-select) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              编程语言 (多选)
            </label>
            <div className="flex flex-wrap gap-2">
              {LANGUAGE_OPTIONS.map((lang) => (
                <button
                  key={lang}
                  onClick={() => handleLanguageToggle(lang)}
                  className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                    languages.includes(lang)
                      ? 'bg-primary text-white'
                      : 'bg-bg-card text-text-secondary hover:bg-border'
                  }`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>

          {/* Security Requirement (Single select) */}
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              安全要求
            </label>
            <div className="flex gap-3">
              {SECURITY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setSecurityRequirement(option.value)}
                  className={`flex-1 px-4 py-3 text-sm font-medium rounded-lg border transition-colors ${
                    securityRequirement === option.value
                      ? 'bg-primary text-white border-primary'
                      : 'bg-white text-text-secondary border-border hover:border-primary'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={!profileName || domains.length === 0 || languages.length === 0}
            className="w-full px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:bg-text-tertiary disabled:cursor-not-allowed font-medium transition-colors"
          >
            获取推荐结果
          </button>
        </div>
      </div>

      {/* Results Section */}
      {showResults && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-text-primary">
              推荐结果
            </h2>
            <span className="text-sm text-text-secondary">
              共 {MOCK_RECOMMENDATIONS.total} 个推荐方案
            </span>
          </div>

          {/* Recommendation Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {MOCK_RECOMMENDATIONS.items.map((item) => (
              <div
                key={item.bundle_id}
                className="bg-white rounded-2xl border-2 border-border hover:border-primary p-6 shadow-sm hover:shadow-lg transition-all"
              >
                {/* Card Header */}
                <div className="flex items-start justify-between mb-4">
                  <span
                    className={`px-3 py-1 text-sm font-semibold rounded-full border ${getTierBadgeColor(
                      item.tier
                    )}`}
                  >
                    {getTierLabel(item.tier)}
                  </span>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-primary">
                      {item.score.toFixed(1)}
                    </div>
                    <div className="text-xs text-text-tertiary">匹配度</div>
                  </div>
                </div>

                {/* Match Reasons */}
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-text-primary mb-2">
                    推荐理由
                  </h4>
                  <ul className="space-y-1">
                    {item.match_reasons.map((reason, idx) => (
                      <li
                        key={idx}
                        className="text-sm text-text-secondary flex items-start gap-2"
                      >
                        <span className="text-primary mt-0.5">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Skills List */}
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-text-primary mb-2">
                    包含技能 ({item.skills.length})
                  </h4>
                  <div className="space-y-2">
                    {item.skills.map((skill) => (
                      <div
                        key={skill.name}
                        className="p-3 bg-bg-card rounded-lg"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-text-primary">
                            {skill.name}
                          </span>
                          <GradeBadge grade={skill.grade} />
                        </div>
                        <div className="flex items-center justify-between text-xs text-text-tertiary">
                          <span>评分: {skill.score_total.toFixed(1)}</span>
                          <span>{skill.metrics.length} 个指标</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Rule Findings (Collapsible) */}
                <details className="group">
                  <summary className="cursor-pointer list-none">
                    <div className="flex items-center justify-between p-3 bg-bg-card rounded-lg hover:bg-border transition-colors">
                      <span className="text-sm font-medium text-text-primary">
                        规则检查 ({item.rule_findings.length})
                      </span>
                      <svg
                        className="w-4 h-4 text-text-secondary group-open:rotate-180 transition-transform"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </div>
                  </summary>
                  <div className="mt-2 space-y-2">
                    {item.rule_findings.map((finding) => (
                      <div
                        key={finding.rule_id}
                        className={`p-3 rounded-lg text-sm ${
                          finding.level === 'pass'
                            ? 'bg-success/10 text-success'
                            : finding.level === 'warning'
                            ? 'bg-warning/10 text-warning'
                            : 'bg-danger/10 text-danger'
                        }`}
                      >
                        <div className="font-medium mb-1">
                          {finding.title}
                        </div>
                        <div className="text-xs opacity-90">
                          {finding.message}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
