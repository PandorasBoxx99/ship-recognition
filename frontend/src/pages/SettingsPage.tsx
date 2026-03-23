import { useState } from 'react'
import { useUrls, useAddUrl, useDeleteUrl, useModelInfo } from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'

type Section = 'scraper' | 'modell' | 'system'

const sections: { id: Section; label: string }[] = [
  { id: 'scraper', label: 'Scraper & VPN' },
  { id: 'modell', label: 'Modell & Training' },
  { id: 'system', label: 'System & App' },
]

export function SettingsPage() {
  const { data: urls } = useUrls()
  const addUrl = useAddUrl()
  const deleteUrl = useDeleteUrl()
  const { data: modelInfo } = useModelInfo()

  const [activeSection, setActiveSection] = useState<Section>('scraper')
  const [newUrl, setNewUrl] = useState('')
  const [newName, setNewName] = useState('')

  // VPN settings (local state — could be persisted via API later)
  const [vpnUser, setVpnUser] = useState('')
  const [vpnApiKey, setVpnApiKey] = useState('')
  const [vpnProvider, setVpnProvider] = useState('nordvpn')
  const [vpnAutoConnect, setVpnAutoConnect] = useState(true)

  // Training settings
  const [defaultEpochs, setDefaultEpochs] = useState(5)
  const [defaultBatchSize, setDefaultBatchSize] = useState(8)
  const [defaultLr, setDefaultLr] = useState('0.00005')
  const [modelDir, setModelDir] = useState('models/ship_classifier')

  const handleAddUrl = async () => {
    if (!newUrl) return
    await addUrl.mutateAsync({ url: newUrl, name: newName })
    setNewUrl('')
    setNewName('')
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Einstellungen</h1>

      {/* Section Nav */}
      <div className="flex gap-2 border-b border-[var(--border)] pb-2">
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors ${
              activeSection === s.id
                ? 'bg-[var(--surface)] text-white border border-[var(--border)] border-b-transparent'
                : 'text-[var(--text-muted)] hover:text-[var(--text)]'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ===== SCRAPER & VPN ===== */}
      {activeSection === 'scraper' && (
        <div className="space-y-6">
          {/* VPN / NordVPN */}
          <Card>
            <h2 className="text-lg font-semibold mb-4">VPN-Konfiguration (NordVPN)</h2>
            <div className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-[var(--text-muted)] block mb-1">VPN-Provider</label>
                  <select
                    value={vpnProvider}
                    onChange={(e) => setVpnProvider(e.target.value)}
                    className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="nordvpn">NordVPN</option>
                    <option value="expressvpn">ExpressVPN</option>
                    <option value="surfshark">Surfshark</option>
                    <option value="custom">Benutzerdefiniert</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={vpnAutoConnect}
                      onChange={(e) => setVpnAutoConnect(e.target.checked)}
                    />
                    Automatisch verbinden bei Scraper-Jobs
                  </label>
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-[var(--text-muted)] block mb-1">Benutzername / E-Mail</label>
                  <input
                    type="text"
                    value={vpnUser}
                    onChange={(e) => setVpnUser(e.target.value)}
                    placeholder="vpn@example.com"
                    className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--text-muted)] block mb-1">API-Key / Token</label>
                  <input
                    type="password"
                    value={vpnApiKey}
                    onChange={(e) => setVpnApiKey(e.target.value)}
                    placeholder="API-Key eingeben..."
                    className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm">Speichern</Button>
                <Button size="sm" variant="ghost">Verbindung testen</Button>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                NordVPN CLI muss installiert und eingeloggt sein. Die Zugangsdaten werden lokal gespeichert.
              </p>
            </div>
          </Card>

          {/* Scraper-Quellen */}
          <Card>
            <h2 className="text-lg font-semibold mb-4">Scraper-Quellen</h2>
            <div className="space-y-3">
              {urls?.map((u) => (
                <div key={u.id} className="flex items-center justify-between bg-[var(--bg)] rounded-lg p-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">{u.name}</div>
                    <div className="text-xs text-[var(--text-muted)] truncate">{u.url}</div>
                  </div>
                  <Button size="sm" variant="danger" onClick={() => { if (confirm('URL entfernen?')) deleteUrl.mutate(u.id) }}>
                    Entfernen
                  </Button>
                </div>
              ))}
              {!urls?.length && <p className="text-sm text-[var(--text-muted)]">Keine Quellen konfiguriert</p>}
            </div>
            <div className="mt-4 flex gap-2">
              <input type="text" placeholder="https://..." value={newUrl} onChange={(e) => setNewUrl(e.target.value)}
                className="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm" />
              <input type="text" placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)}
                className="w-32 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm" />
              <Button onClick={handleAddUrl} disabled={!newUrl || addUrl.isPending}>Hinzufügen</Button>
            </div>
          </Card>

          {/* Scraper-Defaults */}
          <Card>
            <h2 className="text-lg font-semibold mb-4">Scraper-Standardwerte</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Standard-Limit</label>
                <input type="number" defaultValue={100}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Delay Min (s)</label>
                <input type="number" step="0.5" defaultValue={1.0}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Delay Max (s)</label>
                <input type="number" step="0.5" defaultValue={5.0}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Max Retries</label>
                <input type="number" defaultValue={3}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ===== MODELL & TRAINING ===== */}
      {activeSection === 'modell' && (
        <div className="space-y-6">
          <Card>
            <h2 className="text-lg font-semibold mb-4">Aktives Modell</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              <div><span className="text-[var(--text-muted)]">Name:</span> {modelInfo?.model_name || 'ViT Ship Classifier'}</div>
              {modelInfo?.num_labels && (
                <div><span className="text-[var(--text-muted)]">Klassen:</span> {modelInfo.num_labels}</div>
              )}
              {modelInfo?.accuracy && (
                <div><span className="text-[var(--text-muted)]">Genauigkeit:</span> {modelInfo.accuracy}</div>
              )}
              <div><span className="text-[var(--text-muted)]">Status:</span> {modelInfo?.loaded ? 'Geladen' : 'Nicht geladen'}</div>
            </div>
            {modelInfo?.labels && (
              <div className="mt-3">
                <span className="text-xs text-[var(--text-muted)]">Erkannte Typen:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {modelInfo.labels.map((l: string) => (
                    <span key={l} className="text-xs bg-[var(--bg)] px-2 py-0.5 rounded">{l}</span>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4">Training-Standardwerte</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Epochen</label>
                <input type="number" value={defaultEpochs} onChange={(e) => setDefaultEpochs(+e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Batch Size</label>
                <input type="number" value={defaultBatchSize} onChange={(e) => setDefaultBatchSize(+e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Learning Rate</label>
                <input type="text" value={defaultLr} onChange={(e) => setDefaultLr(e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Modell-Verzeichnis</label>
                <input type="text" value={modelDir} onChange={(e) => setModelDir(e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded px-3 py-2 text-sm" />
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4">Augmentation-Defaults</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {['horizontal_flip', 'rotation', 'color_jitter', 'random_crop', 'gaussian_blur', 'perspective'].map((t) => (
                <label key={t} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" defaultChecked={['horizontal_flip', 'rotation', 'color_jitter', 'random_crop'].includes(t)} />
                  {t.replace(/_/g, ' ')}
                </label>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ===== SYSTEM & APP ===== */}
      {activeSection === 'system' && (
        <div className="space-y-6">
          <Card>
            <h2 className="text-lg font-semibold mb-4">System-Information</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              <div><span className="text-[var(--text-muted)]">Version:</span> 2.0.0</div>
              <div><span className="text-[var(--text-muted)]">Port:</span> 3025</div>
              <div><span className="text-[var(--text-muted)]">Backend:</span> FastAPI + Uvicorn</div>
              <div><span className="text-[var(--text-muted)]">Frontend:</span> React + TypeScript</div>
              <div><span className="text-[var(--text-muted)]">Datenbank:</span> SQLite (17 Tabellen)</div>
              <div><span className="text-[var(--text-muted)]">ML-Framework:</span> PyTorch + HuggingFace</div>
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4">API-Konfiguration</h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Secret Key (Agent API)</label>
                <input type="password" defaultValue="" placeholder="Für Agent-API-Authentifizierung"
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm" />
                <p className="text-xs text-[var(--text-muted)] mt-1">Wird als X-API-Key Header für /api/agent/* Endpoints verwendet</p>
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">CORS Origins</label>
                <input type="text" defaultValue="http://localhost:3025, http://localhost:5173"
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Max Upload (MB)</label>
                <input type="number" defaultValue={25}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm" />
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4 text-[var(--danger)]">Gefahrenzone</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">Datenbank zurücksetzen</div>
                  <div className="text-xs text-[var(--text-muted)]">Alle Daten werden gelöscht</div>
                </div>
                <Button size="sm" variant="danger">Zurücksetzen</Button>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">Downloads bereinigen</div>
                  <div className="text-xs text-[var(--text-muted)]">Alle heruntergeladenen Bilder löschen</div>
                </div>
                <Button size="sm" variant="danger">Bereinigen</Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
