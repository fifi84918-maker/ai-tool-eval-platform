interface GradeBadgeProps {
  grade: string | null | undefined
}

export default function GradeBadge({ grade }: GradeBadgeProps) {
  if (!grade) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-200 text-text-tertiary">
        —
      </span>
    )
  }

  const colorMap: Record<string, string> = {
    A: 'bg-grade-a text-white',
    B: 'bg-grade-b text-white',
    C: 'bg-grade-c text-white',
    D: 'bg-grade-d text-white',
    U: 'bg-grade-u text-white',
  }

  const colorClass = colorMap[grade.toUpperCase()] || 'bg-gray-300 text-text-tertiary'

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>
      {grade.toUpperCase()}
    </span>
  )
}
