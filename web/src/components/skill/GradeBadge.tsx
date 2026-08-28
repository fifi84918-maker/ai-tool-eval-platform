interface GradeBadgeProps {
  grade: string | null | undefined
}

export default function GradeBadge({ grade }: GradeBadgeProps) {
  if (!grade) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-gray-200 text-[#86909C]">
        —
      </span>
    )
  }

  const colorMap: Record<string, string> = {
    A: 'bg-[#00B42A] text-white',
    B: 'bg-[#165DFF] text-white',
    C: 'bg-[#FF7D00] text-white',
    D: 'bg-[#F53F3F] text-white',
    U: 'bg-[#86909C] text-white',
  }

  const colorClass = colorMap[grade.toUpperCase()] || 'bg-gray-300 text-[#86909C]'

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>
      {grade.toUpperCase()}
    </span>
  )
}
