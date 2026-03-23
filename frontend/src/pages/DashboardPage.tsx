import { useNavigate } from 'react-router-dom'
import { useStats, useJobs } from '@/hooks/useApi.ts'
import { MetricCard } from '@/components/ui/Card.tsx'
import { Card } from '@/components/ui/Card.tsx'
import { StatusBadge } from '@/components/ui/Badge.tsx'
import { Button } from '@/components/ui/Button.tsx'

export function DashboardPage() {
  const { data: stats } = useStats()
  const { data: jobs } = useJobs()
  const navigate = useNavigate()

  const recentJobs = jobs?.slice(0, 5) ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <MetricCard label="Jobs" value={stats?.total_jobs ?? 0} />
        <MetricCard label="Downloads" value={stats?.downloaded ?? 0} />
        <MetricCard label="Ausstehend" value={stats?.pending ?? 0} />
        <MetricCard label="Klassifiziert" value={stats?.classifications ?? 0} />
        <MetricCard label="Gesamt" value={stats?.total_items ?? 0} />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Type Distribution */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Schiffstypen-Verteilung</h2>
          {stats?.type_distribution?.length ? (
            <div className="space-y-2">
              {stats.type_distribution.map((t) => {
                const maxCount = Math.max(...stats.type_distribution.map((x) => x.count))
                const pct = maxCount > 0 ? (t.count / maxCount) * 100 : 0
                return (
                  <div key={t.type} className="flex items-center gap-3">
                    <span className="text-sm text-[var(--text-muted)] w-32 truncate">{t.type}</span>
                    <div className="flex-1 bg-[var(--bg)] rounded-full h-4">
                      <div
                        className="h-4 rounded-full bg-[var(--primary)]"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono w-8 text-right">{t.count}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-[var(--text-muted)] text-sm">Noch keine Daten</p>
          )}
        </Card>

        {/* Recent Jobs */}
        <Card>
          <h2 className="text-lg font-semibold mb-4">Letzte Jobs</h2>
          {recentJobs.length ? (
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <div key={job.id} className="flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm truncate">{job.name ?? job.url}</div>
                    <div className="text-xs text-[var(--text-muted)]">
                      {job.downloaded}/{job.total_items} Bilder
                    </div>
                  </div>
                  <StatusBadge status={job.status} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[var(--text-muted)] text-sm">Keine Jobs vorhanden</p>
          )}
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Schnellzugriff</h2>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => navigate('/Scraper')}>Neuer Scraper-Job</Button>
          <Button variant="success" onClick={() => navigate('/KI-Erkennung')}>Bild klassifizieren</Button>
          <Button variant="ghost" onClick={() => navigate('/Schiffe')}>Schiffe ansehen</Button>
        </div>
      </Card>
    </div>
  )
}
