import { useState } from 'react'
import {
  useVPNStatus, useVPNConnect, useVPNDisconnect, useVPNRotate,
  useJobs, useCreateJob, useStartJob, usePauseJob, useDeleteJob,
  useAnalyze, useUrls,
} from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'
import { StatusBadge } from '@/components/ui/Badge.tsx'
import { ProgressBar } from '@/components/ui/ProgressBar.tsx'
import type { AnalyzeResult } from '@/types/index.ts'

export function ScraperPage() {
  const { data: vpn } = useVPNStatus()
  const vpnConnect = useVPNConnect()
  const vpnDisconnect = useVPNDisconnect()
  const vpnRotate = useVPNRotate()

  const { data: urls } = useUrls()
  const { data: jobs } = useJobs()
  const createJob = useCreateJob()
  const startJob = useStartJob()
  const pauseJob = usePauseJob()
  const deleteJob = useDeleteJob()
  const analyze = useAnalyze()

  const [selectedUrl, setSelectedUrl] = useState('')
  const [customUrl, setCustomUrl] = useState('')
  const [limit, setLimit] = useState(100)
  const [delayMin, setDelayMin] = useState(1)
  const [delayMax, setDelayMax] = useState(5)
  const [vpnRequired, setVpnRequired] = useState(true)
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResult | null>(null)

  const currentUrl = selectedUrl === 'custom' ? customUrl : selectedUrl

  const handleAnalyze = async () => {
    if (!currentUrl) return
    const result = await analyze.mutateAsync(currentUrl)
    setAnalysisResult(result)
  }

  const handleCreateJob = async () => {
    if (!currentUrl) return
    await createJob.mutateAsync({
      url: currentUrl,
      limit,
      delay_min: delayMin,
      delay_max: delayMax,
      vpn_required: vpnRequired,
    })
    setAnalysisResult(null)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Ship Scraper</h1>

      {/* VPN Control */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">VPN-Steuerung</h2>
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${vpn?.connected ? 'bg-[var(--success)]' : 'bg-[var(--danger)]'}`} />
            <span className="text-sm">
              {vpn?.connected ? `Verbunden: ${vpn.country} (${vpn.ip})` : 'Nicht verbunden'}
            </span>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="success" onClick={() => vpnConnect.mutate('Germany')}
              disabled={vpnConnect.isPending}>
              Verbinden
            </Button>
            <Button size="sm" variant="danger" onClick={() => vpnDisconnect.mutate()}
              disabled={vpnDisconnect.isPending}>
              Trennen
            </Button>
            <Button size="sm" variant="ghost" onClick={() => vpnRotate.mutate()}
              disabled={vpnRotate.isPending}>
              IP wechseln
            </Button>
          </div>
        </div>
      </Card>

      {/* New Job */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Neuer Job</h2>
        <div className="space-y-3">
          <div className="flex gap-2">
            <select
              value={selectedUrl}
              onChange={(e) => setSelectedUrl(e.target.value)}
              className="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
            >
              <option value="">-- Quelle wählen --</option>
              {urls?.map((u) => (
                <option key={u.id} value={u.url}>{u.name} ({u.url})</option>
              ))}
              <option value="custom">Eigene URL...</option>
            </select>
          </div>

          {selectedUrl === 'custom' && (
            <input
              type="text"
              placeholder="https://..."
              value={customUrl}
              onChange={(e) => setCustomUrl(e.target.value)}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
            />
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-[var(--text-muted)]">Limit</label>
              <input type="number" value={limit} onChange={(e) => setLimit(+e.target.value)}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="text-xs text-[var(--text-muted)]">Delay Min (s)</label>
              <input type="number" step="0.5" value={delayMin} onChange={(e) => setDelayMin(+e.target.value)}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="text-xs text-[var(--text-muted)]">Delay Max (s)</label>
              <input type="number" step="0.5" value={delayMax} onChange={(e) => setDelayMax(+e.target.value)}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 text-sm" />
            </div>
            <div className="flex items-end gap-2">
              <label className="flex items-center gap-1 text-sm cursor-pointer">
                <input type="checkbox" checked={vpnRequired} onChange={(e) => setVpnRequired(e.target.checked)} />
                VPN erforderlich
              </label>
            </div>
          </div>

          <div className="flex gap-2">
            <Button onClick={handleAnalyze} disabled={!currentUrl || analyze.isPending}>
              {analyze.isPending ? 'Analysiere...' : 'Website analysieren'}
            </Button>
            <Button variant="success" onClick={handleCreateJob} disabled={!currentUrl || createJob.isPending}>
              {createJob.isPending ? 'Erstelle...' : 'Job erstellen'}
            </Button>
          </div>

          {analysisResult?.success && (
            <div className="bg-[var(--bg)] rounded p-3 text-sm">
              <div className="font-medium">{analysisResult.title}</div>
              <div className="text-[var(--text-muted)] mt-1">
                {analysisResult.categories?.length ?? 0} Kategorien gefunden
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Job List */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Jobs ({jobs?.length ?? 0})</h2>
        <div className="space-y-3">
          {jobs?.map((job) => (
            <div key={job.id} className="bg-[var(--bg)] rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium truncate">{job.name ?? job.url}</div>
                  <div className="text-xs text-[var(--text-muted)]">{job.url}</div>
                </div>
                <StatusBadge status={job.status} />
              </div>
              <ProgressBar value={job.downloaded} max={job.total_items || 1}
                label={`${job.downloaded}/${job.total_items}`} />
              <div className="flex gap-2 mt-2">
                {(job.status === 'pending' || job.status === 'paused') && (
                  <Button size="sm" variant="success" onClick={() => startJob.mutate(job.id)}>Start</Button>
                )}
                {job.status === 'running' && (
                  <Button size="sm" variant="ghost" onClick={() => pauseJob.mutate(job.id)}>Pause</Button>
                )}
                <Button size="sm" variant="danger" onClick={() => { if (confirm('Job löschen?')) deleteJob.mutate(job.id) }}>
                  Löschen
                </Button>
              </div>
            </div>
          ))}
          {!jobs?.length && <p className="text-sm text-[var(--text-muted)]">Keine Jobs vorhanden</p>}
        </div>
      </Card>
    </div>
  )
}
