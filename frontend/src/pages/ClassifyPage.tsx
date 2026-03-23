import { useState, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useClassifyUpload, useClassifications, useModelInfo } from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'
import type { Prediction } from '@/types/index.ts'

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#a855f7']

interface MLModelEntry {
  id: number
  name: string
  version: string
  model_type: string
  is_active: boolean
  input_size: string
}

export function ClassifyPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [predictions, setPredictions] = useState<Prediction[] | null>(null)
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const classify = useClassifyUpload()
  const { data: history } = useClassifications()
  const { data: modelInfo } = useModelInfo()

  // Fetch available models from registry
  const { data: models } = useQuery<MLModelEntry[]>({
    queryKey: ['models-list'],
    queryFn: () => axios.get('/api/models').then(r => r.data),
  })

  const handleFile = (file: File) => {
    setSelectedFile(file)
    setPredictions(null)
    const reader = new FileReader()
    reader.onload = (e) => setPreview(e.target?.result as string)
    reader.readAsDataURL(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleClassify = async () => {
    if (!selectedFile) return
    const result = await classify.mutateAsync(selectedFile)
    setPredictions(result.predictions)
  }

  const handleActivateModel = async (modelId: number) => {
    await axios.post(`/api/models/${modelId}/activate`)
    setSelectedModelId(modelId)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Erkennung</h1>

      {/* Model Selection */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Modell auswählen</h2>
        {models?.length ? (
          <div className="space-y-2">
            {models.map((m) => {
              const isActive = selectedModelId ? m.id === selectedModelId : m.is_active
              return (
                <div
                  key={m.id}
                  onClick={() => handleActivateModel(m.id)}
                  className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all ${
                    isActive
                      ? 'bg-[var(--primary)]/10 border-2 border-[var(--primary)]'
                      : 'bg-[var(--bg)] border-2 border-transparent hover:border-[var(--border)]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-[var(--success)]' : 'bg-[var(--border)]'}`} />
                    <div>
                      <div className="text-sm font-medium">{m.name} <span className="text-[var(--text-muted)]">v{m.version}</span></div>
                      <div className="text-xs text-[var(--text-muted)]">{m.model_type} &middot; {m.input_size}</div>
                    </div>
                  </div>
                  {isActive && (
                    <span className="text-xs bg-[var(--success)]/20 text-[var(--success)] px-2 py-0.5 rounded border border-[var(--success)]/30">
                      Aktiv
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-sm text-[var(--text-muted)]">
            <p>Kein Modell registriert.</p>
            <p className="mt-1">Das Standard-ViT-Modell wird beim ersten Erkennungsaufruf automatisch geladen.</p>
          </div>
        )}
        {modelInfo && (
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-[var(--text-muted)]">
            <div>Status: {modelInfo.loaded ? 'Geladen' : 'Nicht geladen'}</div>
            {modelInfo.num_labels && <div>Klassen: {modelInfo.num_labels}</div>}
            {modelInfo.accuracy && <div>Genauigkeit: {modelInfo.accuracy}</div>}
            {modelInfo.labels && <div>Typen: {modelInfo.labels.length}</div>}
          </div>
        )}
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Upload Area */}
        <Card>
          <h2 className="text-lg font-semibold mb-3">Bild hochladen</h2>
          <div
            className="border-2 border-dashed border-[var(--border)] rounded-lg p-8 text-center cursor-pointer hover:border-[var(--primary)] transition-colors"
            onClick={() => fileRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            {preview ? (
              <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded" />
            ) : (
              <>
                <div className="text-4xl mb-2">🚢</div>
                <p className="text-sm text-[var(--text-muted)]">
                  Bild hierher ziehen oder klicken zum Auswählen
                </p>
              </>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]) }}
            />
          </div>
          {selectedFile && (
            <div className="mt-3 flex items-center justify-between">
              <span className="text-sm text-[var(--text-muted)]">{selectedFile.name}</span>
              <Button onClick={handleClassify} disabled={classify.isPending}>
                {classify.isPending ? 'Klassifiziere...' : 'Erkennung starten'}
              </Button>
            </div>
          )}
        </Card>

        {/* Results */}
        <Card>
          <h2 className="text-lg font-semibold mb-3">Ergebnis</h2>
          {predictions ? (
            <div className="space-y-3">
              {predictions.slice(0, 5).map((p, i) => (
                <div key={p.label}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className={i === 0 ? 'font-bold' : ''}>{p.label}</span>
                    <span className="font-mono">{(p.confidence * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-[var(--bg)] rounded-full h-4">
                    <div
                      className="h-4 rounded-full transition-all duration-500"
                      style={{ width: `${p.confidence * 100}%`, backgroundColor: COLORS[i % COLORS.length] }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[var(--text-muted)] text-sm">Laden Sie ein Bild hoch und starten Sie die Erkennung</p>
          )}
        </Card>
      </div>

      {/* History */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Letzte Klassifikationen</h2>
        {history?.classifications.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                  <th className="pb-2">Typ</th>
                  <th className="pb-2">Konfidenz</th>
                  <th className="pb-2">Modell</th>
                  <th className="pb-2">Datum</th>
                </tr>
              </thead>
              <tbody>
                {history.classifications.map((c) => (
                  <tr key={c.id} className="border-b border-[var(--border)]/50">
                    <td className="py-2 font-medium">{c.predicted_type}</td>
                    <td className="py-2">{(c.confidence * 100).toFixed(1)}%</td>
                    <td className="py-2 text-[var(--text-muted)]">{c.model_name || '-'}</td>
                    <td className="py-2 text-[var(--text-muted)]">
                      {c.created_at ? new Date(c.created_at).toLocaleDateString('de-DE') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-[var(--text-muted)] text-sm">Noch keine Klassifikationen</p>
        )}
      </Card>
    </div>
  )
}
