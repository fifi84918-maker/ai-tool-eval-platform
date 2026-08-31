interface ScoreBarProps {
  score: number | null | undefined
}

export default function ScoreBar({ score }: ScoreBarProps) {
  if (score === null || score === undefined) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-border rounded-full h-2">
          <div className="bg-gray-400 h-2 rounded-full" style={{ width: '0%' }} />
        </div>
        <span className="text-sm text-text-tertiary w-12 text-right">—</span>
      </div>
    )
  }

  const width = Math.max(0, Math.min(100, score))

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-border rounded-full h-2">
        <div 
          className="bg-primary h-2 rounded-full transition-all duration-300"
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-sm text-text-primary font-medium w-12 text-right">
        {score.toFixed(1)}
      </span>
    </div>
  )
}
