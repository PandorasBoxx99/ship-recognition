import { useState, useCallback, useMemo, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useShipEntities, useShipEntity, useDetectShip } from '@/hooks/useApi.ts'
import { Button } from '@/components/ui/Button.tsx'
import type { ShipEntity, ShipImage } from '@/types/index.ts'

function toSlug(ship: { name: string; id: number }): string {
  const name = (ship.name || 'unbekannt').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  return `${name}-${ship.id}`
}

function idFromSlug(slug: string): number | null {
  const match = slug.match(/-(\d+)$/)
  return match ? parseInt(match[1], 10) : null
}

/* ───────────────────── Image Gallery ───────────────────── */
function ImageGallery({ images, selectedIdx, onSelect }: {
  images: ShipImage[]
  selectedIdx: number
  onSelect: (idx: number) => void
}) {
  const safeIdx = Math.min(selectedIdx, Math.max(0, images.length - 1))
  const main = images[safeIdx]
  if (!main) {
    return <div className="w-full h-48 bg-[var(--bg)] rounded-lg flex items-center justify-center text-5xl">🚢</div>
  }

  return (
    <div>
      {main.src ? (
        <img src={main.src} alt="" className="w-full rounded-lg max-h-[400px] object-contain bg-black/20" />
      ) : (
        <div className="w-full h-48 bg-[var(--bg)] rounded-lg flex items-center justify-center text-5xl">🚢</div>
      )}
      {main.source_name && main.source_name !== 'detection_crop' && (
        <div className="mt-1 text-xs text-[var(--text-muted)]">
          Quelle: {main.source_name}
          {main.file_size ? ` — ${(main.file_size / 1024).toFixed(0)} KB` : ''}
        </div>
      )}
      {main.is_primary_crop && (
        <div className="mt-1 text-xs text-[var(--primary)]">Erkanntes Hauptschiff (Crop)</div>
      )}
      {images.length > 1 && (
        <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
          {images.map((img, i) => (
            <div
              key={img.id}
              onClick={() => onSelect(i)}
              className={`flex-shrink-0 w-16 h-16 rounded cursor-pointer border-2 transition-all overflow-hidden ${
                i === safeIdx ? 'border-[var(--primary)]' : 'border-transparent opacity-60 hover:opacity-100'
              }`}
            >
              {img.src ? (
                <img src={img.src} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full bg-[var(--bg)] flex items-center justify-center text-sm">🚢</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ───────────────────── Detail Panel ───────────────────── */
function ShipDetail({ shipId, ships, onSelect }: {
  shipId: number
  ships: ShipEntity[]
  onSelect: (s: ShipEntity) => void
}) {
  const { data: ship } = useShipEntity(shipId)
  const detectMutation = useDetectShip()
  const [selectedImg, setSelectedImg] = useState(0)
  const [showCropsOnly, setShowCropsOnly] = useState(false)

  useEffect(() => { setSelectedImg(0) }, [shipId, showCropsOnly])

  const idx = ships.findIndex(s => s.id === shipId)
  const prev = idx > 0 ? ships[idx - 1] : null
  const next = idx < ships.length - 1 ? ships[idx + 1] : null

  // Filter images based on toggle — computed before render, not in JSX
  const displayImages = useMemo(() => {
    const all = ship?.images || []
    if (!showCropsOnly) {
      return all.filter(i => !i.parent_image_id)
    }
    const originals = all.filter(i => !i.parent_image_id)
    return originals.map(orig => {
      const primaryCrop = all.find(i => i.parent_image_id === orig.id && i.is_primary_crop)
      return primaryCrop || orig
    })
  }, [ship?.images, showCropsOnly])

  const hasCrops = useMemo(() => {
    return (ship?.images || []).some(i => i.is_primary_crop)
  }, [ship?.images])

  if (!ship) {
    return <div className="h-full flex items-center justify-center text-[var(--text-muted)]">Lade...</div>
  }

  const metaFields: [string, string | undefined | null][] = [
    ['Typ', ship.ship_type],
    ['IMO', ship.imo],
    ['MMSI', ship.mmsi],
    ['Flagge', ship.flag],
    ['Land', ship.country],
    ['Baujahr', ship.year_built?.toString()],
    ['Klasse', ship.ship_class],
    ['Operator', ship.operator],
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Navigation */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <Button size="sm" variant="ghost" disabled={!prev}
          onClick={() => prev && onSelect(prev)}>
          &larr; Vorheriges
        </Button>
        <span className="text-xs text-[var(--text-muted)]">{idx + 1} / {ships.length}</span>
        <Button size="sm" variant="ghost" disabled={!next}
          onClick={() => next && onSelect(next)}>
          Naechstes &rarr;
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {/* Ship name + badges */}
        <div>
          <h2 className="text-xl font-bold leading-tight">{ship.name}</h2>
          {ship.aliases && ship.aliases.length > 0 && (
            <div className="text-xs text-[var(--text-muted)] mt-1">
              Auch bekannt als: {ship.aliases.map(a => a.alias_name).join(', ')}
            </div>
          )}
          {ship.sources && ship.sources.length > 0 && (
            <div className="flex gap-1 mt-2">
              {ship.sources.map(src => (
                <span key={src} className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
                  {src}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Detection controls */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button size="sm" onClick={() => detectMutation.mutate(shipId)}
              disabled={detectMutation.isPending}>
              {detectMutation.isPending ? 'Erkenne...' : 'Schiffe erkennen'}
            </Button>
            {detectMutation.data && (
              <span className="text-xs text-[var(--text-muted)]">
                {detectMutation.data.detections_found} erkannt, {detectMutation.data.crops_created} Crops
              </span>
            )}
          </div>
          {hasCrops && (
            <label className="flex items-center gap-2 text-xs cursor-pointer select-none">
              <input type="checkbox" checked={showCropsOnly}
                onChange={() => setShowCropsOnly(!showCropsOnly)}
                className="accent-[var(--primary)]" />
              nur Schiff zeigen
            </label>
          )}
        </div>

        {/* Image gallery */}
        <ImageGallery images={displayImages} selectedIdx={selectedImg} onSelect={setSelectedImg} />

        {/* Metadata */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-[var(--bg)] rounded-lg p-3">
            <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide mb-2">
              Schiffsdaten
            </h3>
            <div className="space-y-1.5 text-sm">
              {metaFields.filter(([, v]) => v).map(([label, value]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[var(--text-muted)]">{label}</span>
                  <span className="font-medium text-right">{value}</span>
                </div>
              ))}
              {metaFields.every(([, v]) => !v) && (
                <span className="text-[var(--text-muted)] text-xs">Keine Daten vorhanden</span>
              )}
            </div>
          </div>

          <div className="bg-[var(--bg)] rounded-lg p-3">
            <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide mb-2">
              Quellen & Bilder
            </h3>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Originalbilder</span>
                <span className="font-medium">{ship.image_count}</span>
              </div>
              {hasCrops && (
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Erkannte Schiffe</span>
                  <span className="font-medium">{ship.images?.filter(i => i.is_primary_crop).length ?? 0} Primaer-Crops</span>
                </div>
              )}
              {ship.sources?.map(src => {
                const count = ship.images?.filter(i => i.source_name === src && !i.parent_image_id).length ?? 0
                return (
                  <div key={src} className="flex justify-between">
                    <span className="text-[var(--text-muted)]">{src}</span>
                    <span className="font-medium">{count} Fotos</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ───────────────────── Ship List Item ───────────────────── */
function ShipListItem({ ship, selected, onClick }: {
  ship: ShipEntity
  selected: boolean
  onClick: () => void
}) {
  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all ${
        selected
          ? 'bg-[var(--primary)]/15 ring-1 ring-[var(--primary)]'
          : 'hover:bg-[var(--bg)]'
      }`}
    >
      {ship.thumbnail ? (
        <img src={ship.thumbnail} alt={ship.name} className="w-14 h-14 rounded object-cover flex-shrink-0"
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
      ) : (
        <div className="w-14 h-14 rounded bg-[var(--bg)] flex items-center justify-center text-lg flex-shrink-0">
          🚢
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium truncate">{ship.name}</div>
        <div className="text-xs text-[var(--text-muted)] truncate">{ship.ship_type || '-'}</div>
        <div className="flex items-center gap-2 mt-0.5">
          {ship.imo && <span className="text-[10px] text-[var(--text-muted)]">IMO {ship.imo}</span>}
          {ship.image_count > 0 && (
            <span className="text-[10px] px-1.5 py-0 rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
              {ship.image_count} Fotos
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

/* ───────────────────── Main Page ───────────────────── */
export function ShipsPage() {
  const { shipSlug } = useParams<{ shipSlug?: string }>()
  const navigate = useNavigate()

  const [sourceFilter, setSourceFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const [selectedShipId, setSelectedShipId] = useState<number | null>(
    shipSlug ? idFromSlug(shipSlug) : null
  )

  const { data } = useShipEntities({
    search, ship_type: typeFilter, source: sourceFilter, page, per_page: 100,
  })

  const debounceSearch = useCallback((val: string) => {
    setSearchInput(val)
    const t = setTimeout(() => { setSearch(val); setPage(1) }, 300)
    return () => clearTimeout(t)
  }, [])

  const ships = data?.ships ?? []

  const handleSelect = useCallback((ship: ShipEntity) => {
    setSelectedShipId(ship.id)
    navigate(`/Schiffe/${toSlug(ship)}`, { replace: true })
  }, [navigate])

  const activeShipId = useMemo(() => {
    if (selectedShipId && ships.find(s => s.id === selectedShipId)) return selectedShipId
    return ships[0]?.id ?? null
  }, [selectedShipId, ships])

  useEffect(() => {
    if (shipSlug && !selectedShipId) {
      const id = idFromSlug(shipSlug)
      if (id) setSelectedShipId(id)
    }
  }, [shipSlug, selectedShipId])

  useEffect(() => {
    if (activeShipId && !shipSlug) {
      const ship = ships.find(s => s.id === activeShipId)
      if (ship) navigate(`/Schiffe/${toSlug(ship)}`, { replace: true })
    }
  }, [activeShipId, shipSlug, ships, navigate])

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Source Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)] overflow-x-auto flex-shrink-0 mb-3">
        <button
          onClick={() => { setSourceFilter(''); setPage(1) }}
          className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
            sourceFilter === ''
              ? 'border-[var(--primary)] text-[var(--primary)]'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
          }`}
        >
          Alle ({data?.total ?? 0})
        </button>
        {data?.sources?.map((src) => (
          <button
            key={src}
            onClick={() => { setSourceFilter(src); setPage(1) }}
            className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              sourceFilter === src
                ? 'border-[var(--primary)] text-[var(--primary)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
            }`}
          >
            {src}
          </button>
        ))}
      </div>

      {/* Master-Detail Layout */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Left: Ship List */}
        <div className="w-80 flex-shrink-0 flex flex-col bg-[var(--surface)] rounded-lg overflow-hidden">
          <div className="p-3 space-y-2 border-b border-[var(--border)] flex-shrink-0">
            <input
              type="text"
              placeholder="Suche (Name, IMO)..."
              value={searchInput}
              onChange={(e) => debounceSearch(e.target.value)}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-sm"
            />
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-sm"
            >
              <option value="">Alle Typen</option>
              {data?.types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {ships.map((ship) => (
              <ShipListItem
                key={ship.id}
                ship={ship}
                selected={activeShipId === ship.id}
                onClick={() => handleSelect(ship)}
              />
            ))}
            {ships.length === 0 && (
              <p className="text-sm text-[var(--text-muted)] text-center py-8">Keine Schiffe gefunden</p>
            )}
          </div>

          {data && data.pages > 1 && (
            <div className="flex items-center justify-between p-2 border-t border-[var(--border)] flex-shrink-0">
              <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                &larr;
              </Button>
              <span className="text-xs text-[var(--text-muted)]">{data.page}/{data.pages}</span>
              <Button size="sm" variant="ghost" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>
                &rarr;
              </Button>
            </div>
          )}
        </div>

        {/* Right: Detail Panel */}
        <div className="flex-1 bg-[var(--surface)] rounded-lg p-4 overflow-hidden">
          {activeShipId ? (
            <ShipDetail shipId={activeShipId} ships={ships} onSelect={handleSelect} />
          ) : (
            <div className="h-full flex items-center justify-center text-[var(--text-muted)]">
              <div className="text-center">
                <div className="text-5xl mb-3">🚢</div>
                <p>Waehle ein Schiff aus der Liste</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
