import { useState } from 'react'
import { useShipEntities, useDetectShip } from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'
import { ProgressBar } from '@/components/ui/ProgressBar.tsx'
import axios from 'axios'
import type { DetectionStatus } from '@/types/index.ts'

export function ExtraktorPage() {
  const { data } = useShipEntities({ per_page: 200 })
  const detectShip = useDetectShip()
  const [batchStatus, setBatchStatus] = useState<DetectionStatus | null>(null)
  const [batchRunning, setBatchRunning] = useState(false)

  const ships = data?.ships ?? []
  const shipsWithCrops = ships.filter(s => s.thumbnail?.includes('crop'))

  const startBatch = async () => {
    try {
      setBatchRunning(true)
      await axios.post('/api/detect/batch')
      // Poll status
      const poll = setInterval(async () => {
        try {
          const res = await axios.get<DetectionStatus>('/api/detect/batch/status')
          setBatchStatus(res.data)
          if (!res.data.running) {
            clearInterval(poll)
            setBatchRunning(false)
          }
        } catch {
          clearInterval(poll)
          setBatchRunning(false)
        }
      }, 2000)
    } catch {
      setBatchRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Overview */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Schiffserkennung & Extraktion</h2>
        <p className="text-sm text-[var(--text-muted)] mb-4">
          Erkennt Schiffe in Bildern mittels Faster R-CNN (COCO vortrainiert) und extrahiert
          das Hauptschiff als Crop-Bild. Das groesste erkannte Schiff wird als Primaerbild
          fuer das ML-Training verwendet.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="bg-[var(--bg)] rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-[var(--primary)]">{ships.length}</div>
            <div className="text-xs text-[var(--text-muted)]">Schiffe gesamt</div>
          </div>
          <div className="bg-[var(--bg)] rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-[var(--success)]">{shipsWithCrops.length}</div>
            <div className="text-xs text-[var(--text-muted)]">Mit Crops</div>
          </div>
          <div className="bg-[var(--bg)] rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-[var(--warning)]">{ships.length - shipsWithCrops.length}</div>
            <div className="text-xs text-[var(--text-muted)]">Ohne Crops</div>
          </div>
          <div className="bg-[var(--bg)] rounded-lg p-3 text-center">
            <div className="text-2xl font-bold">
              {ships.reduce((sum, s) => sum + s.image_count, 0)}
            </div>
            <div className="text-xs text-[var(--text-muted)]">Originalbilder</div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Button onClick={startBatch} disabled={batchRunning}>
            {batchRunning ? 'Erkennung laeuft...' : 'Alle Schiffe erkennen'}
          </Button>
          {batchStatus && (
            <span className="text-sm text-[var(--text-muted)]">{batchStatus.message}</span>
          )}
        </div>

        {batchRunning && batchStatus && (
          <div className="mt-4">
            <ProgressBar
              value={batchStatus.progress}
              max={batchStatus.total || 1}
              label={`${batchStatus.progress}/${batchStatus.total}`}
            />
          </div>
        )}
      </Card>

      {/* Ship list with detection status */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Schiffe ({ships.length})</h2>
        <div className="space-y-2">
          {ships.map(ship => {
            const hasCrops = ship.thumbnail?.includes('crop')
            return (
              <div key={ship.id} className="flex items-center gap-3 bg-[var(--bg)] rounded-lg p-2">
                {ship.thumbnail ? (
                  <img src={ship.thumbnail} alt={ship.name} className="w-12 h-12 rounded object-cover flex-shrink-0" />
                ) : (
                  <div className="w-12 h-12 rounded bg-[var(--surface)] flex items-center justify-center text-sm flex-shrink-0">🚢</div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{ship.name}</div>
                  <div className="text-xs text-[var(--text-muted)]">
                    {ship.image_count} Bilder
                    {ship.imo ? ` — IMO ${ship.imo}` : ''}
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {hasCrops ? (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--success)]/10 text-[var(--success)]">
                      Erkannt
                    </span>
                  ) : (
                    <Button size="sm" variant="ghost"
                      onClick={() => detectShip.mutate(ship.id)}
                      disabled={detectShip.isPending}>
                      Erkennen
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
