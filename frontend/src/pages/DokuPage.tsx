import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { Card } from '@/components/ui/Card.tsx'

interface Phase {
  id: number
  name: string
  status: string
  date: string
  items: string[]
}

interface PlanData {
  title: string
  phases: Phase[]
  requirements: Record<string, string>
  stats: Record<string, number>
}

interface ChangelogEntry {
  hash: string
  date: string
  message: string
  details: string
}

const usePlan = () =>
  useQuery<PlanData>({
    queryKey: ['docs-plan'],
    queryFn: () => axios.get('/api/docs/plan').then(r => r.data),
  })

const useChangelog = () =>
  useQuery<{ changelog: ChangelogEntry[] }>({
    queryKey: ['docs-changelog'],
    queryFn: () => axios.get('/api/docs/changelog').then(r => r.data),
  })

const statusColors: Record<string, string> = {
  done: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  'in-progress': 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  pending: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
}

const statusLabels: Record<string, string> = {
  done: 'Abgeschlossen',
  'in-progress': 'In Arbeit',
  pending: 'Ausstehend',
}

export function DokuPage() {
  const { data: plan } = usePlan()
  const { data: changelogData } = useChangelog()

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dokumentation</h1>

      {/* Project Stats */}
      {plan?.stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            { label: 'Dateien', value: plan.stats.files },
            { label: 'Code-Zeilen', value: plan.stats.lines_of_code?.toLocaleString('de-DE') },
            { label: 'API-Routes', value: plan.stats.api_routes },
            { label: 'DB-Tabellen', value: plan.stats.database_tables },
            { label: 'Tests', value: plan.stats.tests },
            { label: 'Seiten', value: plan.stats.frontend_pages },
          ].map((s) => (
            <div key={s.label} className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3 text-center">
              <div className="text-xl font-bold">{s.value}</div>
              <div className="text-xs text-[var(--text-muted)]">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Implementation Plan */}
      <Card>
        <h2 className="text-xl font-semibold mb-4">
          {plan?.title ?? 'Implementierungsplan'}
        </h2>

        <div className="space-y-4">
          {plan?.phases.map((phase) => (
            <div key={phase.id} className="border border-[var(--border)] rounded-lg overflow-hidden">
              <div className="flex items-center justify-between bg-[var(--bg)] px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-[var(--text-muted)]">Phase {phase.id}</span>
                  <span className="font-semibold">{phase.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-[var(--text-muted)]">{phase.date}</span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusColors[phase.status] ?? statusColors.pending}`}>
                    {statusLabels[phase.status] ?? phase.status}
                  </span>
                </div>
              </div>
              <ul className="px-4 py-3 space-y-1">
                {phase.items.map((item, i) => (
                  <li key={i} className="text-sm text-[var(--text-muted)] flex gap-2">
                    <span className="text-[var(--success)] mt-0.5">&#10003;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Card>

      {/* Tech Stack */}
      {plan?.requirements && (
        <Card>
          <h2 className="text-xl font-semibold mb-4">Technologie-Stack</h2>
          <div className="grid md:grid-cols-2 gap-3">
            {Object.entries(plan.requirements).map(([key, value]) => (
              <div key={key} className="bg-[var(--bg)] rounded-lg p-3">
                <div className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
                  {key}
                </div>
                <div className="text-sm">{value}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Changelog */}
      <Card>
        <h2 className="text-xl font-semibold mb-4">Änderungshistorie</h2>
        {changelogData?.changelog.length ? (
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[15px] top-2 bottom-2 w-px bg-[var(--border)]" />

            <div className="space-y-4">
              {[...changelogData.changelog].reverse().map((entry, i) => (
                <div key={entry.hash} className="flex gap-4 relative">
                  {/* Timeline dot */}
                  <div className={`w-[9px] h-[9px] rounded-full mt-1.5 flex-shrink-0 relative z-10 ring-2 ring-[var(--bg)] ${
                    i === 0 ? 'bg-[var(--primary)]' : 'bg-[var(--border)]'
                  }`} style={{ marginLeft: '11px' }} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-xs bg-[var(--surface-hover)] px-1.5 py-0.5 rounded text-[var(--text-muted)]">
                        {entry.hash}
                      </span>
                      <span className="text-xs text-[var(--text-muted)]">{entry.date}</span>
                    </div>
                    <p className="text-sm mt-1 font-medium">{entry.message}</p>
                    {entry.details && (
                      <p className="text-xs text-[var(--text-muted)] mt-0.5 whitespace-pre-line">
                        {entry.details.split('\n').filter(Boolean).slice(0, 5).join('\n')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">Keine Einträge</p>
        )}
      </Card>
    </div>
  )
}
