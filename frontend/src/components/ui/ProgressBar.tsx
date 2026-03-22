interface ProgressBarProps {
  value: number
  max?: number
  color?: string
  label?: string
}

export function ProgressBar({ value, max = 100, color = 'var(--primary)', label }: ProgressBarProps) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div>
      {label && <div className="text-xs text-[var(--text-muted)] mb-1">{label} ({pct}%)</div>}
      <div className="w-full bg-[var(--bg)] rounded-full h-2">
        <div
          className="h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  )
}
