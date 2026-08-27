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
      <div className="bg-white p-6 rounded-lg shadow">
        <h1 className="text-2xl font-bold text-red-600">Skill Not Found</h1>
        <p className="mt-2 text-gray-600">
          The requested skill ID does not exist.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900">
                {skill.summary.canonical_name}
              </h1>
              <GradeBadge grade={skill.summary.grade} />
            </div>
            <p className="text-sm text-gray-500 mt-1 font-mono">
              {skill.summary.skill_id}
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <span className={`px-3 py-1 text-xs font-medium rounded-full ${
              skill.summary.status === 'NEUTRAL_TESTED' ? 'bg-green-100 text-green-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {skill.summary.status}
            </span>
            <span className={`px-3 py-1 text-xs font-medium rounded-full ${
              skill.summary.evidence_grade === 'D' ? 'bg-blue-100 text-blue-800' :
              'bg-purple-100 text-purple-800'
            }`}>
              Grade: {skill.summary.evidence_grade}
            </span>
          </div>
        </div>

        {skill.summary.score_total !== null && skill.summary.score_total !== undefined && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Quality Score</h3>
            <ScoreBar score={skill.summary.score_total} />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 mt-6">
          <div>
            <h3 className="text-sm font-medium text-gray-500">Source</h3>
            <p className="mt-1 text-gray-900">{skill.summary.source_kind}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Author</h3>
            <p className="mt-1 text-gray-900">{skill.author || 'Unknown'}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">License</h3>
            <p className="mt-1 text-gray-900">{skill.license_spdx || 'Unknown'}</p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-500">Origin</h3>
            <a 
              href={skill.summary.origin_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="mt-1 text-blue-600 hover:underline"
            >
              View Source →
            </a>
          </div>
        </div>

        {skill.summary.description && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-500">Description</h3>
            <p className="mt-1 text-gray-900">{skill.summary.description}</p>
          </div>
        )}

        {skill.warnings && skill.warnings.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-yellow-600">Warnings</h3>
            <ul className="mt-2 space-y-1">
              {skill.warnings.map((warning, idx) => (
                <li key={idx} className="text-sm text-yellow-700">
                  • {warning}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {skill.json_ld && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">JSON-LD Structured Data</h2>
          <pre className="bg-gray-50 p-4 rounded overflow-x-auto text-sm">
            {JSON.stringify(skill.json_ld, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
