'use client'

import { useState } from 'react'
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

export default function HomePage() {
  const [query, setQuery] = useState('')
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/skills?query=${encodeURIComponent(query)}&limit=20`)
      const data = await response.json()
      setSkills(data)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-4">Search Skills</h1>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Search by name or description..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {skills.length === 0 && !loading && (
          <div className="text-center text-gray-500 py-8">
            No results. Try searching for a skill name.
          </div>
        )}
        
        {skills.map((skill) => (
          <Link 
            key={skill.skill_id} 
            href={`/skills/${skill.skill_id}`}
            className="block bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-gray-900">
                    {skill.canonical_name}
                  </h2>
                  <GradeBadge grade={skill.grade} />
                </div>
                <p className="text-sm text-gray-500 mt-1 font-mono">
                  {skill.skill_id.substring(0, 16)}...
                </p>
                {skill.description && (
                  <p className="text-gray-700 mt-2">
                    {skill.description}
                  </p>
                )}
                <div className="mt-3">
                  <ScoreBar score={skill.score_total} />
                </div>
              </div>
              <div className="ml-4 flex flex-col gap-2">
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                  skill.status === 'NEUTRAL_TESTED' ? 'bg-green-100 text-green-800' :
                  skill.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {skill.status}
                </span>
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                  skill.evidence_grade === 'D' ? 'bg-blue-100 text-blue-800' :
                  'bg-purple-100 text-purple-800'
                }`}>
                  Grade: {skill.evidence_grade}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
