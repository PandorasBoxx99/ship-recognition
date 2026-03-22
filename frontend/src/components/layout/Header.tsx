import { useVPNStatus } from '@/hooks/useApi.ts'
import { useUIStore } from '@/stores/uiStore.ts'
import type { TabId } from '@/types/index.ts'

const tabs: { id: TabId; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'scraper', label: 'Scraper' },
  { id: 'ships', label: 'Schiffe' },
  { id: 'classify', label: 'KI-Erkennung' },
  { id: 'training', label: 'Training' },
  { id: 'settings', label: 'Einstellungen' },
]

export function Header() {
  const { activeTab, setActiveTab } = useUIStore()
  const { data: vpn } = useVPNStatus()

  return (
    <header className="sticky top-0 z-50 bg-[var(--surface)] border-b border-[var(--border)]">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-3">
            <span className="text-xl">🚢</span>
            <span className="font-bold text-lg">Ship Recognition</span>
          </div>

          <nav className="hidden md:flex items-center gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-[var(--primary)] text-white'
                    : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-hover)]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${vpn?.connected ? 'bg-[var(--success)]' : 'bg-[var(--danger)]'}`} />
            <span className="text-xs text-[var(--text-muted)]">
              VPN: {vpn?.connected ? vpn.country ?? 'Verbunden' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Mobile nav */}
        <div className="md:hidden flex overflow-x-auto gap-1 pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-[var(--primary)] text-white'
                  : 'text-[var(--text-muted)] bg-[var(--surface-hover)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
