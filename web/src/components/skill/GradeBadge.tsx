interface GradeBadgeProps {
  grade: string | null | undefined
}

export default function GradeBadge({ grade }: GradeBadgeProps) {
  if (!grade) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-300 text-gray-600">
        —
      </span>
    )
  }

  const colorMap: Record<string, string> = {
    A: 'bg-green-500 text-white',
    B: 'bg-teal-500 text-white',
    C: 'bg-yellow-500 text-black',
    D: 'bg-orange-500 text-white',
    U: 'bg-red-500 text-white',
  }

  const colorClass = colorMap[grade.toUpperCase()] || 'bg-gray-300 text-gray-600'

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>
      {grade.toUpperCase()}
    </span>
  )
}
