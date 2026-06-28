import { useState, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import axios from 'axios'
import { useUrls, useAddUrl, useDeleteUrl, useModelInfo, useVPNConnection, useVPNConfig } from '@/hooks/useApi.ts'
import { Card } from '@/components/ui/Card.tsx'
import { Button } from '@/components/ui/Button.tsx'
import { showToast } from '@/components/ui/Toast.tsx'

type Section = 'vpn' | 'scraper' | 'modell' | 'system'

const sections: { id: Section; label: string }[] = [
  { id: 'vpn', label: 'VPN' },
  { id: 'scraper', label: 'Scraper-Quellen' },
  { id: 'modell', label: 'Modell & Training' },
  { id: 'system', label: 'System & App' },
]

export function SettingsPage() {
  const { data: urls } = useUrls()
  const addUrl = useAddUrl()
  const deleteUrl = useDeleteUrl()
  const { data: modelInfo } = useModelInfo()

  const [activeSection, setActiveSection] = useState<Section>('vpn')
  const [newUrl, setNewUrl] = useState('')
  const [newName, setNewName] = useState('')

  // VPN settings — loaded from API, saved to .env
  const [vpnApiKey, setVpnApiKey] = useState('')
  const [vpnAutoConnect, setVpnAutoConnect] = useState(true)
  const [vpnCountry, setVpnCountry] = useState('Germany')
  const [vpnRotation, setVpnRotation] = useState('manual')
  const [vpnTesting, setVpnTesting] = useState(false)
  const [vpnTestResult, setVpnTestResult] = useState<'success' | 'error' | null>(null)
  const [vpnTokenVisible, setVpnTokenVisible] = useState(false)

  const { data: vpnSettings } = useQuery({
    queryKey: ['vpn-settings'],
    queryFn: () => axios.get('/api/settings/vpn').then(r => r.data),
  })

  const saveVpn = useMutation({
    mutationFn: (data: Record<string, unknown>) => axios.put('/api/settings/vpn', data).then(r => r.data),
    onSuccess: () => showToast('success', 'VPN-Einstellungen gespeichert'),
  })

  // Live VPN connection (direct + VPN IP, server, country) and real-time controls
  const { data: conn, isFetching: connFetching } = useVPNConnection()
  const vpnConfig = useVPNConfig()

  useEffect(() => {
    if (vpnSettings) {
      setVpnAutoConnect(vpnSettings.vpn_auto_connect ?? true)
      setVpnCountry(vpnSettings.vpn_default_country ?? 'Germany')
      setVpnRotation(vpnSettings.vpn_rotation ?? 'manual')
    }
  }, [vpnSettings])

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

      {/* ===== VPN ===== */}
      {activeSection === 'vpn' && (
        <div className="space-y-6">
          {/* ----- Live-Verbindungsstatus ----- */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">
                Verbindungsstatus
                {connFetching && <span className="ml-2 text-xs text-[var(--text-muted)]">aktualisiere…</span>}
              </h2>
              <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                <span className={conn?.vpn_enabled ? 'text-[var(--success)]' : 'text-[var(--text-muted)]'}>
                  {conn?.vpn_enabled ? 'VPN aktiv' : 'VPN aus (direkte IP)'}
                </span>
                <input
                  type="checkbox"
                  checked={!!conn?.vpn_enabled}
                  disabled={vpnConfig.isPending}
                  onChange={(e) => vpnConfig.mutate({ enabled: e.target.checked })}
                />
              </label>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-[var(--bg)] rounded-lg p-3">
                <div className="text-xs text-[var(--text-muted)]">Direkte IP</div>
                <div className="font-mono text-sm mt-0.5">{conn?.direct_ip ?? '—'}</div>
              </div>
              <div className="bg-[var(--bg)] rounded-lg p-3">
                <div className="text-xs text-[var(--text-muted)]">VPN-IP (Exit)</div>
                <div className="font-mono text-sm mt-0.5">
                  {conn?.vpn_ip ?? (conn?.vpn_enabled ? 'wird ermittelt…' : '—')}
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4 mt-4">
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Exit-Land (SOCKS5)</label>
                <select
                  value={conn?.proxy_country ?? 'Netherlands'}
                  disabled={!conn?.vpn_enabled || vpnConfig.isPending}
                  onChange={(e) => vpnConfig.mutate({ proxy_country: e.target.value })}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm disabled:opacity-50"
                >
                  {(conn?.available_countries ?? ['Netherlands', 'Sweden', 'United States']).map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <p className="text-xs text-[var(--text-muted)] mt-1">NordVPN-SOCKS5 nur NL / SE / US verfügbar</p>
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Aktueller Server</label>
                <div className="font-mono text-sm py-2">{conn?.server_host ?? '—'}</div>
              </div>
            </div>

            <div className="mt-4 text-sm">
              {conn?.protected ? (
                <span className="text-[var(--success)]">
                  {'✔'} Geschützt — Scraper-Traffic läuft über NordVPN ({conn.proxy_country})
                </span>
              ) : conn?.vpn_enabled ? (
                <span className="text-[var(--danger)]">
                  {'⚠'} VPN aktiv, aber Exit-IP nicht verifiziert (Token/Server prüfen)
                </span>
              ) : (
                <span className="text-[var(--text-muted)]">
                  Direkter Zugriff — Scraping läuft über deine echte IP
                </span>
              )}
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4">NordVPN — Access Token</h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Access Token</label>
                <div className="flex gap-2">
                  <input
                    type={vpnTokenVisible ? 'text' : 'password'}
                    value={vpnApiKey}
                    onChange={(e) => setVpnApiKey(e.target.value)}
                    placeholder={vpnSettings?.vpn_api_key === '***' ? '\u2022\u2022\u2022\u2022\u2022\u2022\u2022 Token gespeichert' : 'NordVPN Access Token eingeben...'}
                    className="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm font-mono"
                  />
                  <Button size="sm" variant="ghost" onClick={() => setVpnTokenVisible(!vpnTokenVisible)}>
                    {vpnTokenVisible ? 'Verbergen' : 'Anzeigen'}
                  </Button>
                </div>
                {vpnSettings?.vpn_api_key === '***' && !vpnApiKey && (
                  <p className="text-xs text-[var(--success)] mt-1">{'\u2714'} Token ist gespeichert</p>
                )}
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Token aus NordVPN Account: my.nordaccount.com &rarr; Services &rarr; NordVPN &rarr; Access Token
                </p>
              </div>

              <div className="flex gap-2 items-center">
                <Button size="sm" onClick={() => {
                  if (!vpnApiKey) {
                    showToast('error', 'Bitte Token eingeben')
                    return
                  }
                  saveVpn.mutate({ vpn_api_key: vpnApiKey })
                }} disabled={saveVpn.isPending || !vpnApiKey}>
                  {saveVpn.isPending ? 'Speichere...' : 'Token speichern'}
                </Button>
                <Button size="sm" variant="ghost" disabled={vpnTesting} onClick={async () => {
                  setVpnTesting(true)
                  setVpnTestResult(null)
                  try {
                    // Send token to test endpoint — uses saved token if field is empty
                    const res = await axios.post('/api/vpn/test-token', { token: vpnApiKey || '' })
                    if (res.data.valid) {
                      setVpnTestResult('success')
                      showToast('success', res.data.message || 'Token gueltig')
                    } else {
                      setVpnTestResult('error')
                      showToast('error', res.data.error || 'Token ungueltig')
                    }
                  } catch (e: unknown) {
                    setVpnTestResult('error')
                    const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error
                    showToast('error', msg || 'Token-Test fehlgeschlagen')
                  }
                  setVpnTesting(false)
                  setTimeout(() => setVpnTestResult(null), 5000)
                }}>
                  {vpnTesting ? 'Teste...' : 'Token testen'}
                </Button>
                {vpnTestResult === 'success' && <span className="text-xl text-[var(--success)]">{'\u2714'}</span>}
                {vpnTestResult === 'error' && <span className="text-xl text-[var(--danger)]">{'\u2718'}</span>}
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4">Verbindungsoptionen</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">Standard-Land</label>
                <select value={vpnCountry} onChange={(e) => setVpnCountry(e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm">
                  <option>Germany</option>
                  <option>Netherlands</option>
                  <option>Switzerland</option>
                  <option>United States</option>
                  <option>United Kingdom</option>
                  <option>Sweden</option>
                  <option>Austria</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-[var(--text-muted)] block mb-1">IP-Rotation</label>
                <select value={vpnRotation} onChange={(e) => setVpnRotation(e.target.value)}
                  className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm">
                  <option value="manual">Manuell</option>
                  <option value="per_job">Pro Job</option>
                  <option value="every_50">Alle 50 Downloads</option>
                  <option value="every_100">Alle 100 Downloads</option>
                </select>
              </div>
            </div>
            <div className="mt-4 flex gap-2 items-center">
              <Button size="sm" onClick={() => saveVpn.mutate({
                vpn_default_country: vpnCountry,
                vpn_rotation: vpnRotation,
                vpn_auto_connect: vpnAutoConnect,
              })} disabled={saveVpn.isPending}>Speichern</Button>
              <label className="flex items-center gap-2 text-sm cursor-pointer ml-4">
                <input type="checkbox" checked={vpnAutoConnect}
                  onChange={(e) => setVpnAutoConnect(e.target.checked)} />
                Auto-Connect bei Scraper-Jobs
              </label>
            </div>
          </Card>
        </div>
      )}

      {/* ===== SCRAPER-QUELLEN ===== */}
      {activeSection === 'scraper' && (
        <div className="space-y-6">
          <Card>
            <h2 className="text-lg font-semibold mb-4">Registrierte Quellen</h2>
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
