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
              <h3 className="text-sm font-medium text-[#4E5969]">Quality Score</h3>
              <span className="text-5xl font-bold text-[#165DFF]">
                {skill.summary.score_total.toFixed(1)}
              </span>
            </div>
            <ScoreBar score={skill.summary.score_total} />
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
