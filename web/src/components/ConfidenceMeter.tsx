interface ConfidenceMeterProps {
  score: number
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
}

function getColor(score: number): string {
  if (score >= 0.7) return 'bg-success-500'
  if (score >= 0.5) return 'bg-warning-500'
  return 'bg-danger-500'
}

function getLabel(score: number): string {
  if (score >= 0.8) return 'High Confidence'
  if (score >= 0.6) return 'Good Confidence'
  if (score >= 0.4) return 'Moderate Confidence'
  return 'Low Confidence'
}

function getTextColor(score: number): string {
  if (score >= 0.7) return 'text-success-600'
  if (score >= 0.5) return 'text-warning-600'
  return 'text-danger-600'
}

export default function ConfidenceMeter({ score, showLabel = true, size = 'sm' }: ConfidenceMeterProps) {
  const percentage = Math.round(score * 100)
  const barColor = getColor(score)
  const label = getLabel(score)
  const textColor = getTextColor(score)

  const heightClasses = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  }

  return (
    <div className="w-full max-w-xs">
      <div className="flex items-center justify-between mb-1">
        {showLabel && (
          <span className="text-xs text-warm-500">Confidence</span>
        )}
        <span className={`text-xs font-semibold ${textColor}`}>
          {percentage}%
        </span>
      </div>
      <div className={`w-full bg-warm-200 rounded-full ${heightClasses[size]} overflow-hidden`}>
        <div
          className={`${barColor} ${heightClasses[size]} rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <p className={`text-[11px] mt-0.5 ${textColor}`}>{label}</p>
      )}
    </div>
  )
}
