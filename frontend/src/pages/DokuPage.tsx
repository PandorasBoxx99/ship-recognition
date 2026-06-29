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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const useModelDocs = () => useQuery<any>({ queryKey: ['docs-models'], queryFn: () => axios.get('/api/docs/models').then(r => r.data) })

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

interface MlParam { name: string; default: string; desc: string }
interface MlConfig { key: string; value: string; desc: string }
interface MlComponent {
  id: string
  name: string
  model: string
  purpose: string
  how: string[]
  parameters: MlParam[]
  config: MlConfig[]
  endpoints: string[]
}
interface MlDocs { title: string; overview: string; components: MlComponent[] }

const useMlDocs = () =>
  useQuery<MlDocs>({ queryKey: ['docs-ml'], queryFn: () => axios.get('/api/docs/ml').then(r => r.data) })

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
  const { data: modelDocs } = useModelDocs()
  const { data: ml } = useMlDocs()
  const am = modelDocs?.active_model

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

      {/* ML-Kette: Komponenten & Parameter */}
      {ml && (
        <Card>
          <h2 className="text-xl font-semibold mb-1">{ml.title}</h2>
          <p className="text-sm text-[var(--text-muted)] mb-4">{ml.overview}</p>
          <div className="space-y-4">
            {ml.components.map((c) => (
              <div key={c.id} className="border border-[var(--border)] rounded-lg p-4">
                <div className="flex items-baseline justify-between flex-wrap gap-2">
                  <h3 className="font-semibold">{c.name}</h3>
                  <span className="text-xs font-mono text-[var(--text-muted)]">{c.model}</span>
                </div>
                <p className="text-sm text-[var(--text-muted)] mt-1">{c.purpose}</p>

                <h4 className="text-xs uppercase tracking-wider text-[var(--text-muted)] mt-3 mb-1">
                  Funktionsweise
                </h4>
                <ul className="text-sm space-y-0.5">
                  {c.how.map((h, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-[var(--primary)] mt-0.5">·</span>
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>

                {c.parameters.length > 0 && (
                  <>
                    <h4 className="text-xs uppercase tracking-wider text-[var(--text-muted)] mt-3 mb-1">
                      Parameter
                    </h4>
                    <div className="space-y-1">
                      {c.parameters.map((p) => (
                        <div key={p.name} className="text-sm flex gap-2 flex-wrap">
                          <span className="font-mono text-[var(--primary)] w-44 flex-shrink-0">{p.name}</span>
                          <span className="font-mono text-[var(--text-muted)] w-16 flex-shrink-0">{p.default}</span>
                          <span className="text-[var(--text-muted)] flex-1 min-w-[12rem]">{p.desc}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {c.config.length > 0 && (
                  <>
                    <h4 className="text-xs uppercase tracking-wider text-[var(--text-muted)] mt-3 mb-1">
                      .env-Konfiguration
                    </h4>
                    <div className="space-y-1">
                      {c.config.map((cf) => (
                        <div key={cf.key} className="text-sm flex gap-2 flex-wrap">
                          <span className="font-mono text-[var(--primary)] w-56 flex-shrink-0">{cf.key}</span>
                          <span className="font-mono text-[var(--text-muted)] w-20 flex-shrink-0">{cf.value}</span>
                          <span className="text-[var(--text-muted)] flex-1 min-w-[12rem]">{cf.desc}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {c.endpoints.length > 0 && (
                  <>
                    <h4 className="text-xs uppercase tracking-wider text-[var(--text-muted)] mt-3 mb-1">
                      Endpunkte
                    </h4>
                    <div className="flex flex-wrap gap-1">
                      {c.endpoints.map((e) => (
                        <code key={e} className="text-xs bg-[var(--bg)] px-1.5 py-0.5 rounded text-[var(--text-muted)]">
                          {e}
                        </code>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Active Model Details */}
      {am && (
        <Card>
          <h2 className="text-xl font-semibold mb-4">Aktives Modell — {am.short_name}</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Kenndaten</h3>
              <div className="space-y-1.5 text-sm">
                {[
                  ['Modell', am.name],
                  ['Architektur', am.architecture],
                  ['Basis', am.base_model],
                  ['Parameter', am.parameters],
                  ['Genauigkeit', am.accuracy],
                  ['F1-Score', am.f1_score],
                  ['Testbilder', am.test_samples?.toLocaleString('de-DE')],
                  ['Trainingsdaten', am.training_dataset],
                  ['Input', am.input_size],
                  ['Lizenz', am.license],
                ].map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-[var(--text-muted)] w-28 flex-shrink-0">{k}:</span>
                    <span>{v}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 mt-3">
                <a href={am.huggingface_url} target="_blank" rel="noopener"
                  className="text-xs text-[var(--primary)] hover:underline">HuggingFace</a>
                <a href={am.kaggle_url} target="_blank" rel="noopener"
                  className="text-xs text-[var(--primary)] hover:underline">Kaggle</a>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Klassen (Precision / Recall)</h3>
              <div className="space-y-1">
                {am.classes?.map((c: { name: string; precision: number; recall: number; description: string }) => (
                  <div key={c.name} className="flex items-center gap-2 text-sm">
                    <span className="w-36 truncate font-medium">{c.name}</span>
                    <div className="flex-1 bg-[var(--bg)] rounded-full h-2">
                      <div className="h-2 rounded-full bg-[var(--success)]"
                        style={{ width: `${c.precision * 100}%` }} />
                    </div>
                    <span className="text-xs font-mono w-20 text-right text-[var(--text-muted)]">
                      {(c.precision * 100).toFixed(1)}% / {(c.recall * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-[var(--success)] uppercase mb-1">Stärken</h4>
              <ul className="text-sm space-y-0.5">
                {am.strengths?.map((s: string, i: number) => <li key={i} className="text-[var(--text-muted)]">{s}</li>)}
              </ul>
            </div>
            <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-3">
              <h4 className="text-xs font-semibold text-[var(--warning)] uppercase mb-1">Limitierungen</h4>
              <ul className="text-sm space-y-0.5">
                {am.limitations?.map((s: string, i: number) => <li key={i} className="text-[var(--text-muted)]">{s}</li>)}
              </ul>
            </div>
          </div>
        </Card>
      )}

      {/* Alternative Models */}
      {modelDocs?.alternatives && (
        <Card>
          <h2 className="text-xl font-semibold mb-4">Alternative Modelle</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                  <th className="pb-2 pr-3">Modell</th>
                  <th className="pb-2 pr-3">Typ</th>
                  <th className="pb-2 pr-3">Genauigkeit</th>
                  <th className="pb-2 pr-3">Klassen</th>
                  <th className="pb-2 pr-3">Vorteile</th>
                  <th className="pb-2">Nachteile</th>
                </tr>
              </thead>
              <tbody>
                {modelDocs.alternatives.map((m: { name: string; type: string; accuracy: string; classes: number | string; pros: string; cons: string; url: string }) => (
                  <tr key={m.name} className="border-b border-[var(--border)]/30">
                    <td className="py-2 pr-3">
                      <a href={m.url} target="_blank" rel="noopener" className="text-[var(--primary)] hover:underline">{m.name}</a>
                    </td>
                    <td className="py-2 pr-3 text-[var(--text-muted)]">{m.type}</td>
                    <td className="py-2 pr-3 font-mono">{m.accuracy}</td>
                    <td className="py-2 pr-3">{m.classes}</td>
                    <td className="py-2 pr-3 text-xs text-[var(--text-muted)]">{m.pros}</td>
                    <td className="py-2 text-xs text-[var(--text-muted)]">{m.cons}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Available Datasets */}
      {modelDocs?.datasets && (
        <Card>
          <h2 className="text-xl font-semibold mb-4">Verfügbare Datasets</h2>
          <div className="grid md:grid-cols-2 gap-3">
            {modelDocs.datasets.map((d: { name: string; images: number | string; classes: number | string; types: string; source: string }) => (
              <div key={d.name} className="bg-[var(--bg)] rounded-lg p-3">
                <div className="font-medium text-sm">{d.name}</div>
                <div className="text-xs text-[var(--text-muted)] mt-1">
                  {d.images} Bilder &middot; {d.classes} Klassen &middot; {d.source}
                </div>
                <div className="text-xs text-[var(--text-muted)]">{d.types}</div>
              </div>
            ))}
          </div>
        </Card>
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
