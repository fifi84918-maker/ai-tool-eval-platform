interface ScoreBarProps {
  score: number | null | undefined
}

export default function ScoreBar({ score }: ScoreBarProps) {
  if (score === null || score === undefined) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-gray-200 rounded-full h-2">
          <div className="bg-gray-400 h-2 rounded-full" style={{ width: '0%' }} />
        </div>
        <span className="text-sm text-gray-500 w-12 text-right">—</span>
      </div>
    )
  }

  const getColorClass = (value: number): string => {
    if (value >= 90) return 'bg-green-500'
    if (value >= 75) return 'bg-teal-500'
    if (value >= 60) return 'bg-yellow-500'
    if (value >= 40) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const colorClass = getColorClass(score)
  const width = Math.max(0, Math.min(100, score))

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div 
          className={`${colorClass} h-2 rounded-full transition-all duration-300`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-sm text-gray-700 font-medium w-12 text-right">
        {score.toFixed(1)}
      </span>
    </div>
  )
}
