import Link from 'next/link'
import GradeBadge from '@/components/skill/GradeBadge'
import ScoreBar from '@/components/skill/ScoreBar'

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
  json_ld: any | null
  // Future: dimension scores when available
  metrics?: {
    accuracy?: number
    reliability?: number
    security?: number
    performance?: number
  }
  findings?: Array<{
    dimension: string
    severity: string
    message: string
  }>
  scanned_at?: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

async function getSkill(skillId: string): Promise<SkillDetail | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/skills/${skillId}`, {
      cache: 'no-store',
    })
    
    if (!response.ok) {
      return null
    }
    
    return response.json()
  } catch (error) {
    console.error('Failed to fetch skill:', error)
    return null
  }
}

export default async function SkillDetailPage({
  params,
}: {
  params: { skill_id: string }
}) {
  const skill = await getSkill(params.skill_id)

  if (!skill) {
    return (
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-[#F53F3F]">Skill Not Found</h1>
        <p className="mt-2 text-[#4E5969]">
          The requested skill ID does not exist.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl border border-[#E5E6EB] p-8 shadow-sm">
        <div className="flex items-start justify-between mb-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-[#1D2129]">
                {skill.summary.canonical_name}
              </h1>
              <GradeBadge grade={skill.summary.grade} />
            </div>
            <p className="text-sm text-[#86909C] font-mono">
              {skill.summary.skill_id}
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <span className={`px-3 py-1 text-xs font-medium rounded-full ${
              skill.summary.status === 'NEUTRAL_TESTED' ? 'bg-[#00B42A]/10 text-[#00B42A]' :
              'bg-[#86909C]/10 text-[#86909C]'
            }`}>
              {skill.summary.status}
            </span>
            <span className="px-3 py-1 text-xs font-medium rounded-full bg-[#165DFF]/10 text-[#165DFF]">
              Evidence: {skill.summary.evidence_grade}
            </span>
          </div>
        </div>

        {skill.summary.score_total !== null && skill.summary.score_total !== undefined && (
          <div className="mb-8 p-6 bg-[#F5F7FA] rounded-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-[#4E5969]">综合评分</h3>
              <span className="text-5xl font-bold text-[#165DFF]">
                {skill.summary.score_total.toFixed(1)}
              </span>
            </div>
            <ScoreBar score={skill.summary.score_total} />
            {skill.scanned_at && (
              <p className="text-xs text-[#86909C] mt-3">
                评测时间: {new Date(skill.scanned_at).toLocaleString('zh-CN')}
              </p>
            )}
          </div>
        )}

        {/* Dimension Scores (if available) */}
        {skill.metrics && Object.keys(skill.metrics).length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">维度评分</h3>
            <div className="space-y-4">
              {skill.metrics.accuracy !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">准确性 Accuracy</span>
                    <span className="text-lg font-bold text-[#165DFF]">{skill.metrics.accuracy.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#165DFF] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.accuracy}%` }}
                    />
                  </div>
                </div>
              )}

              {skill.metrics.reliability !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">可靠性 Reliability</span>
                    <span className="text-lg font-bold text-[#00B42A]">{skill.metrics.reliability.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#00B42A] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.reliability}%` }}
                    />
                  </div>
                </div>
              )}

              {skill.metrics.security !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">安全性 Security</span>
                    <span className="text-lg font-bold text-[#FF7D00]">{skill.metrics.security.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#FF7D00] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.security}%` }}
                    />
                  </div>
                </div>
              )}

              {skill.metrics.performance !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[#1D2129]">性能 Performance</span>
                    <span className="text-lg font-bold text-[#722ED1]">{skill.metrics.performance.toFixed(1)}</span>
                  </div>
                  <div className="bg-[#E5E6EB] rounded-full h-3">
                    <div
                      className="bg-[#722ED1] h-3 rounded-full transition-all duration-300"
                      style={{ width: `${skill.metrics.performance}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Findings (if available) */}
        {skill.findings && skill.findings.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-[#1D2129] mb-4">发现问题</h3>
            <div className="space-y-3">
              {skill.findings.map((finding, idx) => (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border ${
                    finding.severity === 'high' || finding.severity === 'critical'
                      ? 'bg-[#F53F3F]/5 border-[#F53F3F]/20'
                      : finding.severity === 'medium'
                      ? 'bg-[#FF7D00]/5 border-[#FF7D00]/20'
                      : 'bg-[#86909C]/5 border-[#86909C]/20'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg">
                      {finding.severity === 'high' || finding.severity === 'critical' ? '🔴' :
                       finding.severity === 'medium' ? '🟡' : '⚪'}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                          finding.severity === 'high' || finding.severity === 'critical'
                            ? 'bg-[#F53F3F] text-white'
                            : finding.severity === 'medium'
                            ? 'bg-[#FF7D00] text-white'
                            : 'bg-[#86909C] text-white'
                        }`}>
                          {finding.severity.toUpperCase()}
                        </span>
                        <span className="text-xs text-[#86909C]">{finding.dimension}</span>
                      </div>
                      <p className="text-sm text-[#1D2129]">{finding.message}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evaluate Button (for GitHub repos) */}
        {skill.summary.origin_url.includes('github.com') && (
          <div className="mb-8 p-6 bg-gradient-to-r from-[#165DFF]/5 to-[#722ED1]/5 rounded-2xl border border-[#165DFF]/20">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-[#1D2129] mb-1">获取详细评分</h3>
                <p className="text-sm text-[#4E5969]">
                  评估此 Skill 的 GitHub 仓库，获取维度分数、代码质量分析和安全发现
                </p>
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
              target="_blank" 
              rel="noopener noreferrer"
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

        {skill.warnings && skill.warnings.length > 0 && (
          <div className="mt-6 p-4 bg-[#FF7D00]/10 rounded-xl">
            <h3 className="text-sm font-medium text-[#FF7D00] mb-2">Warnings</h3>
            <ul className="space-y-1">
              {skill.warnings.map((warning, idx) => (
                <li key={idx} className="text-sm text-[#FF7D00]">
                  • {warning}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

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
