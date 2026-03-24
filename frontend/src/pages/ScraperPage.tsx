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
import type { AnalyzeResult, Job } from '@/types/index.ts'
import axios from 'axios'

function JobLogPanel({ jobId }: { jobId: number }) {
  const [lines, setLines] = useState<string[]>([])
  const [open, setOpen] = useState(false)

  const loadLog = async () => {
    try {
      const res = await axios.get<{ lines: string[]; total: number }>(`/api/jobs/${jobId}/log?lines=50`)
      setLines(res.data.lines)
    } catch { setLines(['Log konnte nicht geladen werden.']) }
  }

  return (
    <div className="mt-2">
      <button
        onClick={() => { if (!open) loadLog(); setOpen(!open) }}
        className="text-xs text-[var(--text-muted)] hover:text-[var(--text)] underline"
      >
        {open ? 'Log ausblenden' : 'Log anzeigen'}
      </button>
      {open && (
        <div className="mt-1 bg-black/80 text-green-400 rounded p-2 max-h-48 overflow-y-auto font-mono text-[11px] leading-tight">
          {lines.length === 0 ? (
            <span className="text-gray-500">Keine Log-Eintraege vorhanden</span>
          ) : (
            lines.map((line, i) => <div key={i}>{line}</div>)
          )}
          <button onClick={loadLog} className="mt-1 text-blue-400 underline text-[10px]">Aktualisieren</button>
        </div>
      )}
    </div>
  )
}

function JobCard({ job, startJob, pauseJob, deleteJob }: {
  job: Job
  startJob: ReturnType<typeof useStartJob>
  pauseJob: ReturnType<typeof usePauseJob>
  deleteJob: ReturnType<typeof useDeleteJob>
}) {
  const canResume = job.status === 'pending' || job.status === 'paused' || job.status === 'failed'
  const isResuming = job.status === 'paused' || job.status === 'failed'

  return (
    <div key={job.id} className="bg-[var(--bg)] rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium truncate">{job.name ?? job.url}</div>
          <div className="text-xs text-[var(--text-muted)]">{job.url}</div>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Error message - prominent red box */}
      {job.error_message && (job.status === 'failed' || job.status === 'paused') && (
        <div className="mb-2 p-2 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
          <span className="font-semibold">Fehler: </span>{job.error_message}
        </div>
      )}

      {/* Running spinner */}
      {job.status === 'running' && (
        <div className="flex items-center gap-2 mb-2">
          <svg className="animate-spin h-4 w-4 text-[var(--primary)]" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-xs text-[var(--primary)] font-medium">Download laeuft...</span>
        </div>
      )}

      <ProgressBar
        value={job.downloaded}
        max={(job.total_items || job.limit_count) || 1}
        label={`${job.downloaded}/${job.total_items || job.limit_count || 0}`}
      />

      <div className="flex gap-2 mt-2">
        {canResume && (
          <Button size="sm" variant="success" onClick={() => startJob.mutate(job.id)}
            disabled={startJob.isPending}>
            {startJob.isPending ? 'Starte...' : isResuming ? 'Fortsetzen' : 'Start'}
          </Button>
        )}
        {job.status === 'running' && (
          <Button size="sm" variant="ghost" onClick={() => pauseJob.mutate(job.id)}
            disabled={pauseJob.isPending}>
            {pauseJob.isPending ? 'Pausiere...' : 'Pause'}
          </Button>
        )}
        <Button size="sm" variant="danger" onClick={() => { if (confirm('Job loeschen?')) deleteJob.mutate(job.id) }}>
          Loeschen
        </Button>
      </div>

      {/* Log panel */}
      <JobLogPanel jobId={job.id} />
    </div>
  )
}

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
    const job = await createJob.mutateAsync({
      url: currentUrl,
      limit,
      delay_min: delayMin,
      delay_max: delayMax,
      vpn_required: vpnRequired,
    })
    setAnalysisResult(null)
    // Auto-start the job immediately after creation
    if (job?.id && job.total_items > 0) {
      try {
        await startJob.mutateAsync(job.id)
      } catch { /* Start may fail if VPN required — user can start manually */ }
    }
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
              <option value="">-- Quelle waehlen --</option>
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
              {createJob.isPending ? 'Erstelle & starte...' : 'Job erstellen & starten'}
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
            <JobCard key={job.id} job={job} startJob={startJob} pauseJob={pauseJob} deleteJob={deleteJob} />
          ))}
          {!jobs?.length && <p className="text-sm text-[var(--text-muted)]">Keine Jobs vorhanden</p>}
        </div>
      </Card>
    </div>
  )
}
