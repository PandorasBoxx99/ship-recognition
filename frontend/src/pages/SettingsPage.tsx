import { useState } from 'react'
import { useUrls, useAddUrl, useDeleteUrl, useModelInfo } from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'

export function SettingsPage() {
  const { data: urls } = useUrls()
  const addUrl = useAddUrl()
  const deleteUrl = useDeleteUrl()
  const { data: modelInfo } = useModelInfo()

  const [newUrl, setNewUrl] = useState('')
  const [newName, setNewName] = useState('')

  const handleAdd = async () => {
    if (!newUrl) return
    await addUrl.mutateAsync({ url: newUrl, name: newName })
    setNewUrl('')
    setNewName('')
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Einstellungen</h1>

      {/* URL Management */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">Vordefinierte URLs</h2>
        <div className="space-y-3">
          {urls?.map((u) => (
            <div key={u.id} className="flex items-center justify-between bg-[var(--bg)] rounded p-2">
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">{u.name}</div>
                <div className="text-xs text-[var(--text-muted)] truncate">{u.url}</div>
              </div>
              <Button size="sm" variant="danger" onClick={() => { if (confirm('URL löschen?')) deleteUrl.mutate(u.id) }}>
                Löschen
              </Button>
            </div>
          ))}
        </div>
        <div className="mt-4 flex gap-2">
          <input type="text" placeholder="URL" value={newUrl} onChange={(e) => setNewUrl(e.target.value)}
            className="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
          <input type="text" placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)}
            className="w-32 bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
          <Button onClick={handleAdd} disabled={!newUrl || addUrl.isPending}>Hinzufügen</Button>
        </div>
      </Card>

      {/* App Info */}
      <Card>
        <h2 className="text-lg font-semibold mb-3">App-Info</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <div><span className="text-[var(--text-muted)]">Version:</span> 2.0.0</div>
          <div><span className="text-[var(--text-muted)]">Port:</span> 3025</div>
          <div><span className="text-[var(--text-muted)]">Datenbank:</span> SQLite</div>
          <div><span className="text-[var(--text-muted)]">Backend:</span> FastAPI</div>
          <div><span className="text-[var(--text-muted)]">Frontend:</span> React + TypeScript</div>
          <div><span className="text-[var(--text-muted)]">Modell:</span> {modelInfo?.model_name || 'ViT Ship Classifier'}</div>
          {modelInfo?.num_labels && (
            <div><span className="text-[var(--text-muted)]">Schiffstypen:</span> {modelInfo.num_labels}</div>
          )}
          {modelInfo?.accuracy && (
            <div><span className="text-[var(--text-muted)]">Genauigkeit:</span> {modelInfo.accuracy}</div>
          )}
        </div>
      </Card>
    </div>
  )
}
