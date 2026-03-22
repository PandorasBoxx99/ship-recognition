import { useState, useCallback } from 'react'
import { useShips, useClassifyShip } from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'
import { StatusBadge } from '@/components/ui/Badge.tsx'
import type { Ship, Prediction } from '@/types/index.ts'

function getImageSrc(ship: Ship): string | null {
  if (!ship.local_path) return null
  const parts = ship.local_path.replace(/\\/g, '/').split('/')
  const dlIdx = parts.indexOf('downloads')
  if (dlIdx >= 0) return '/downloads/' + parts.slice(dlIdx + 1).join('/')
  return null
}

export function ShipsPage() {
  const [typeFilter, setTypeFilter] = useState('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const [selectedShip, setSelectedShip] = useState<Ship | null>(null)
  const [classifyResult, setClassifyResult] = useState<Prediction[] | null>(null)

  const { data } = useShips({ type: typeFilter, search, page })
  const classifyShip = useClassifyShip()

  const debounceSearch = useCallback((val: string) => {
    setSearchInput(val)
    const t = setTimeout(() => { setSearch(val); setPage(1) }, 300)
    return () => clearTimeout(t)
  }, [])

  const handleClassify = async (id: number) => {
    setClassifyResult(null)
    const result = await classifyShip.mutateAsync(id)
    setClassifyResult(result.predictions)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Schiffe ({data?.total ?? 0})</h1>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
          className="bg-[var(--surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Alle Typen</option>
          {data?.types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Suche (Name, IMO)..."
          value={searchInput}
          onChange={(e) => debounceSearch(e.target.value)}
          className="flex-1 min-w-[200px] bg-[var(--surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
        />
      </div>

      {/* Ship Detail Modal */}
      {selectedShip && (
        <Card className="border-[var(--primary)]">
          <div className="flex justify-between items-start mb-3">
            <h2 className="text-lg font-semibold">{selectedShip.ship_name || 'Unbekannt'}</h2>
            <Button size="sm" variant="ghost" onClick={() => { setSelectedShip(null); setClassifyResult(null) }}>
              Schliessen
            </Button>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              {getImageSrc(selectedShip) ? (
                <img src={getImageSrc(selectedShip)!} alt={selectedShip.ship_name ?? ''}
                  className="w-full rounded-lg max-h-64 object-cover" />
              ) : (
                <div className="w-full h-48 bg-[var(--bg)] rounded-lg flex items-center justify-center text-4xl">🚢</div>
              )}
            </div>
            <div className="space-y-2 text-sm">
              <div><span className="text-[var(--text-muted)]">Typ:</span> {selectedShip.ship_type || '-'}</div>
              <div><span className="text-[var(--text-muted)]">IMO:</span> {selectedShip.imo_number || '-'}</div>
              <div><span className="text-[var(--text-muted)]">MMSI:</span> {selectedShip.mmsi || '-'}</div>
              <div><span className="text-[var(--text-muted)]">Quelle:</span> {selectedShip.job_name || '-'}</div>
              <div><span className="text-[var(--text-muted)]">Status:</span> <StatusBadge status={selectedShip.status} /></div>
              <Button size="sm" onClick={() => handleClassify(selectedShip.id)}
                disabled={classifyShip.isPending}>
                {classifyShip.isPending ? 'Klassifiziere...' : 'KI-Erkennung starten'}
              </Button>
              {classifyResult && (
                <div className="mt-2 space-y-1">
                  {classifyResult.map((p, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="flex-1 bg-[var(--bg)] rounded-full h-3">
                        <div className="h-3 rounded-full bg-[var(--primary)]"
                          style={{ width: `${p.confidence * 100}%` }} />
                      </div>
                      <span className="text-xs w-28 truncate">{p.label}</span>
                      <span className="text-xs font-mono w-12 text-right">{(p.confidence * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Ship Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {data?.ships.map((ship) => {
          const src = getImageSrc(ship)
          return (
            <div
              key={ship.id}
              className="bg-[var(--surface)] rounded-lg overflow-hidden cursor-pointer hover:ring-2 ring-[var(--primary)] transition-all"
              onClick={() => { setSelectedShip(ship); setClassifyResult(null) }}
            >
              {src ? (
                <img src={src} alt={ship.ship_name ?? ''} className="w-full h-32 object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
              ) : (
                <div className="w-full h-32 bg-[var(--bg)] flex items-center justify-center text-2xl">🚢</div>
              )}
              <div className="p-2">
                <div className="text-sm truncate">{ship.ship_name || 'Unbekannt'}</div>
                <div className="text-xs text-[var(--text-muted)]">{ship.ship_type || '-'}</div>
              </div>
            </div>
          )
        })}
      </div>

      {!data?.ships.length && (
        <p className="text-center text-[var(--text-muted)]">Keine Schiffe gefunden</p>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex justify-center gap-2">
          <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Zurück
          </Button>
          <span className="text-sm py-2">Seite {data.page} von {data.pages}</span>
          <Button size="sm" variant="ghost" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
            Weiter
          </Button>
        </div>
      )}
    </div>
  )
}
