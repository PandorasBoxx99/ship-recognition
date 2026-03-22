interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'purple'
  children: React.ReactNode
}

const colors: Record<string, string> = {
  default: 'bg-slate-600 text-slate-200',
  success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  warning: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  danger: 'bg-red-500/20 text-red-400 border border-red-500/30',
  purple: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[variant]}`}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { variant: BadgeProps['variant']; label: string }> = {
    pending: { variant: 'warning', label: 'Ausstehend' },
    running: { variant: 'purple', label: 'Läuft' },
    paused: { variant: 'warning', label: 'Pausiert' },
    completed: { variant: 'success', label: 'Fertig' },
    failed: { variant: 'danger', label: 'Fehler' },
    downloaded: { variant: 'success', label: 'Heruntergeladen' },
  }
  const { variant, label } = map[status] ?? { variant: 'default' as const, label: status }
  return <Badge variant={variant}>{label}</Badge>
}
