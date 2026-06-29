import { useStats, useShipEntities } from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'

const DB_TABLES = [
  { name: 'jobs', desc: 'Scraping-Jobs', group: 'Legacy v1' },
  { name: 'items', desc: 'Heruntergeladene Bilder (Einzeleintraege)', group: 'Legacy v1' },
  { name: 'categories', desc: 'Kategorien', group: 'Legacy v1' },
  { name: 'vpn_log', desc: 'VPN-Verbindungslog', group: 'Legacy v1' },
  { name: 'predefined_urls', desc: 'Vordefinierte Quellen-URLs', group: 'Legacy v1' },
  { name: 'classifications', desc: 'KI-Klassifizierungen', group: 'Legacy v1' },
  { name: 'augmentation_log', desc: 'Augmentierungs-Protokoll', group: 'Legacy v1' },
  { name: 'ships', desc: 'Normalisierte Schiffs-Entitaeten (gruppiert)', group: 'Normalized v2' },
  { name: 'ship_aliases', desc: 'Alternative Schiffsnamen', group: 'Normalized v2' },
  { name: 'images', desc: 'Bilder mit Crops (Parent-Child)', group: 'Normalized v2' },
  { name: 'image_annotations', desc: 'Bounding Boxes, Segmentierung', group: 'Normalized v2' },
  { name: 'scrape_sources', desc: 'Scraping-Quellen', group: 'Normalized v2' },
  { name: 'scrape_jobs', desc: 'Normalisierte Scrape-Jobs', group: 'Normalized v2' },
  { name: 'ml_models', desc: 'ML-Modell-Registry', group: 'ML' },
  { name: 'training_runs', desc: 'Trainingslaeufe', group: 'ML' },
  { name: 'inference_logs', desc: 'Inferenz-Protokoll', group: 'ML' },
  { name: 'synthetic_jobs', desc: 'Synthetische Daten-Jobs', group: 'ML' },
]

export function DatenbankPage() {
  const { data: stats } = useStats()
  const { data: shipData } = useShipEntities({ per_page: 1 })

  const kpis = [
    { label: 'Jobs', value: stats?.total_jobs ?? '-' },
    { label: 'Schiffe (v2)', value: stats?.total_ships ?? '-' },
    { label: 'Bilder (v2)', value: stats?.total_images ?? '-' },
    { label: 'Ausstehend', value: stats?.pending ?? '-' },
    { label: 'Fehlgeschlagen', value: stats?.failed ?? '-' },
    { label: 'Klassifizierungen', value: stats?.classifications ?? '-' },
    { label: 'Ships (v2, API)', value: shipData?.total ?? '-' },
    { label: 'Quellen', value: shipData?.sources?.length ?? '-' },
  ]

  const groups = [...new Set(DB_TABLES.map(t => t.group))]

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Datenbank-Uebersicht</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {kpis.map(kpi => (
            <div key={kpi.label} className="bg-[var(--bg)] rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-[var(--primary)]">{kpi.value}</div>
              <div className="text-xs text-[var(--text-muted)]">{kpi.label}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Type Distribution */}
      {stats?.type_distribution && stats.type_distribution.length > 0 && (
        <Card>
          <h2 className="text-lg font-semibold mb-3">Typ-Verteilung</h2>
          <div className="space-y-2">
            {stats.type_distribution.map(t => (
              <div key={t.type} className="flex items-center gap-3">
                <div className="flex-1 bg-[var(--bg)] rounded-full h-4 overflow-hidden">
                  <div
                    className="h-4 rounded-full bg-[var(--primary)] transition-all"
                    style={{ width: `${Math.max(5, (t.count / (stats.total_images || 1)) * 100)}%` }}
                  />
                </div>
                <span className="text-sm w-40 truncate">{t.type || 'Unbekannt'}</span>
                <span className="text-sm font-mono w-10 text-right">{t.count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Table Structure */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Tabellen-Struktur (SQLite)</h2>
        {groups.map(group => (
          <div key={group} className="mb-4">
            <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide mb-2">{group}</h3>
            <div className="space-y-1">
              {DB_TABLES.filter(t => t.group === group).map(table => (
                <div key={table.name} className="flex items-center gap-3 bg-[var(--bg)] rounded px-3 py-1.5">
                  <span className="text-sm font-mono text-[var(--primary)] w-40">{table.name}</span>
                  <span className="text-xs text-[var(--text-muted)]">{table.desc}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}
