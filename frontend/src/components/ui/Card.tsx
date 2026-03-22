interface CardProps {
  children: React.ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`bg-[var(--surface)] rounded-lg border border-[var(--border)] p-4 ${className}`}>
      {children}
    </div>
  )
}

export function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card>
      <div className="text-sm text-[var(--text-muted)]">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      {sub && <div className="text-xs text-[var(--text-muted)] mt-1">{sub}</div>}
    </Card>
  )
}
