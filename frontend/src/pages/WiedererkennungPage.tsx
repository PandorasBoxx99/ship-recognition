import { useState } from 'react'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'
import { ProgressBar } from '@/components/ui/ProgressBar.tsx'
import { showToast } from '@/components/ui/Toast.tsx'
import {
  useSimilaritySearch, useSimilarityReindex,
  useReidReadiness, useReidStatus, useReidTrain,
} from '@/hooks/useApi.ts'
import type { SimilarityResponse } from '@/types/index.ts'

export function WiedererkennungPage() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [model, setModel] = useState('dinov2')
  const [result, setResult] = useState<SimilarityResponse | null>(null)

  const search = useSimilaritySearch()
  const reindex = useSimilarityReindex()
  const readiness = useReidReadiness()
  const reidStatus = useReidStatus()
  const reidTrain = useReidTrain()

  const onFile = (f: File | null) => {
    setFile(f)
    setResult(null)
    if (f) {
      const reader = new FileReader()
      reader.onload = (e) => setPreview(e.target?.result as string)
      reader.readAsDataURL(f)
    } else {
      setPreview(null)
    }
  }

  const runSearch = () => {
    if (!file) return
    search.mutate(
      { file, model },
      {
        onSuccess: setResult,
        onError: () => showToast('error', 'Suche fehlgeschlagen'),
      },
    )
  }

  const runReindex = () => {
    reindex.mutate(undefined, {
      onSuccess: (d) =>
        showToast('success', `Galerie aufgebaut: ${d.gallery_size} Bilder (${d.failed} Fehler)`),
      onError: () => showToast('error', 'Reindex fehlgeschlagen'),
    })
  }

  const best = result?.best_match
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl font-bold">Schiffs-Wiedererkennung</h1>
        <Button variant="ghost" onClick={runReindex} disabled={reindex.isPending}>
          {reindex.isPending ? 'Baue Galerie…' : 'Galerie neu aufbauen'}
        </Button>
      </div>
      <p className="text-sm text-[var(--text-muted)]">
        Lade ein Foto hoch — die Ähnlichkeitssuche (DINOv2) findet das wahrscheinlichste Schiff und
        gibt einen Konfidenzwert. „Galerie neu aufbauen" indexiert alle gespeicherten Bilder neu.
      </p>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Upload + Steuerung */}
        <Card>
          <h2 className="text-lg font-semibold mb-3">Abfragebild</h2>
          {preview ? (
            <img src={preview} alt="Vorschau" className="max-h-56 mx-auto rounded mb-3" />
          ) : (
            <div className="h-40 flex items-center justify-center text-sm text-[var(--text-muted)] border border-dashed border-[var(--border)] rounded mb-3">
              Kein Bild ausgewählt
            </div>
          )}
          <div className="flex flex-wrap gap-2 items-center">
            <label className="px-3 py-2 text-sm rounded-lg bg-[var(--bg)] border border-[var(--border)] cursor-pointer">
              Bild wählen
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => onFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
            >
              <option value="dinov2">DINOv2 (empfohlen)</option>
              <option value="vit">ViT</option>
            </select>
            <Button onClick={runSearch} disabled={!file || search.isPending}>
              {search.isPending ? 'Analysiere…' : 'Identifizieren'}
            </Button>
          </div>
        </Card>

        {/* Konfidenz / bester Treffer */}
        <Card>
          <h2 className="text-lg font-semibold mb-3">Ergebnis</h2>
          {!best ? (
            <p className="text-sm text-[var(--text-muted)]">Noch kein Bild analysiert.</p>
          ) : best.confident ? (
            <div className="space-y-2">
              <div className="text-[var(--success)] font-semibold">
                {'✔'} Erkannt: {best.ship_name ?? 'Unbenanntes Schiff'}
              </div>
              <div className="text-sm">Konfidenz: <span className="font-mono">{pct(best.confidence)}</span></div>
              {best.ship_type && (
                <div className="text-sm text-[var(--text-muted)]">Typ: {best.ship_type}</div>
              )}
              <div className="text-xs text-[var(--text-muted)]">
                Abstand zum 2. Treffer: {pct(best.margin)} · Galerie: {result?.gallery_size ?? '–'} Bilder
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-[var(--danger)] font-semibold">
                {'⚠'} Kein sicherer Treffer
              </div>
              <div className="text-sm text-[var(--text-muted)]">
                Bestes Vergleichsschiff: {best.ship_name ?? '–'} (nur {pct(best.confidence)})
              </div>
              <div className="text-xs text-[var(--text-muted)]">
                Unter der Schwelle ({pct(result?.threshold ?? 0)}) — Schiff vermutlich nicht in der Galerie.
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Trefferliste */}
      {result?.results?.length ? (
        <Card>
          <h2 className="text-lg font-semibold mb-4">Ähnlichste Bilder</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {result.results.map((m) => (
              <div key={m.image_id} className="text-xs">
                {m.src ? (
                  <img
                    src={m.src}
                    alt={m.ship_name ?? ''}
                    className="w-full h-24 object-cover rounded mb-1 bg-black/20"
                    onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden' }}
                  />
                ) : (
                  <div className="w-full h-24 rounded mb-1 bg-[var(--bg)]" />
                )}
                <div className="truncate font-medium">{m.ship_name ?? 'Unbekannt'}</div>
                <div className="flex items-center gap-1">
                  <div className="flex-1 h-1.5 bg-[var(--bg)] rounded-full">
                    <div
                      className="h-1.5 rounded-full bg-[var(--primary)]"
                      style={{ width: `${Math.max(2, m.similarity * 100)}%` }}
                    />
                  </div>
                  <span className="font-mono text-[var(--text-muted)]">{pct(m.similarity)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {/* ArcFace Fine-Tuning */}
      <Card>
        <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
          <h2 className="text-lg font-semibold">Fine-Tuning (ArcFace)</h2>
          {readiness.data?.has_trained_model && (
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--success)]/20 text-[var(--success)]">
              Modell aktiv
            </span>
          )}
        </div>
        <p className="text-sm text-[var(--text-muted)] mb-3">
          Trainiert eine schiffsspezifische Projektion auf den DINOv2-Features und verbessert die
          Unterscheidung einzelner Schiffe. Braucht mehrere Bilder pro Schiff.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-3">
          <div>
            <span className="text-[var(--text-muted)]">Schiffe gesamt:</span>{' '}
            {readiness.data?.total_ships_with_images ?? '–'}
          </div>
          <div>
            <span className="text-[var(--text-muted)]">Qualifizieren (≥{readiness.data?.min_images ?? '?'}):</span>{' '}
            {readiness.data?.qualifying_ships ?? '–'}
          </div>
          <div>
            <span className="text-[var(--text-muted)]">Nutzbare Bilder:</span>{' '}
            {readiness.data?.usable_images ?? '–'}
          </div>
          <div>
            <span className="text-[var(--text-muted)]">Bereit:</span>{' '}
            {readiness.data?.ready ? 'ja' : 'nein'}
          </div>
        </div>
        {reidStatus.data?.running ? (
          <div className="space-y-1">
            <ProgressBar value={reidStatus.data.progress} />
            <div className="text-xs text-[var(--text-muted)]">{reidStatus.data.message}</div>
          </div>
        ) : (
          <div className="flex items-center gap-3 flex-wrap">
            <Button
              onClick={() =>
                reidTrain.mutate(undefined, {
                  onSuccess: (d) =>
                    showToast(d.error ? 'error' : 'success', d.error || 'Training gestartet'),
                  onError: () => showToast('error', 'Start fehlgeschlagen'),
                })
              }
              disabled={!readiness.data?.ready || reidTrain.isPending}
            >
              Training starten
            </Button>
            {!readiness.data?.ready && (
              <span className="text-xs text-[var(--text-muted)]">
                Mind. 2 Schiffe mit genügend Bildern nötig.
              </span>
            )}
            {reidStatus.data?.message && reidStatus.data.message !== 'Idle' && (
              <span className="text-xs text-[var(--text-muted)]">{reidStatus.data.message}</span>
            )}
          </div>
        )}
        <p className="text-xs text-[var(--text-muted)] mt-2">
          Nach dem Training die Galerie oben neu aufbauen, damit die neuen Embeddings genutzt werden.
        </p>
      </Card>
    </div>
  )
}
