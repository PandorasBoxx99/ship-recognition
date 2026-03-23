import { NavLink } from 'react-router-dom'
import { useVPNStatus } from '@/hooks/useApi.ts'

const tabs = [
  { path: '/Dashboard', label: 'Dashboard' },
  { path: '/Scraper', label: 'Scraper' },
  { path: '/Schiffe', label: 'Schiffe' },
  { path: '/Erkennung', label: 'Erkennung' },
  { path: '/Training', label: 'Training' },
  { path: '/Einstellungen', label: 'Einstellungen' },
  { path: '/Doku', label: 'Doku' },
]

export function Header() {
  const { data: vpn } = useVPNStatus()

  return (
    <header className="sticky top-0 z-50 bg-[var(--surface)] border-b border-[var(--border)]">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <NavLink to="/Dashboard" className="flex items-center gap-3 no-underline text-[var(--text)]">
            <span className="text-xl">🚢</span>
            <span className="font-bold text-lg">Ship Recognition</span>
          </NavLink>

          <nav className="hidden md:flex items-center gap-1">
            {tabs.map((tab) => (
              <NavLink
                key={tab.path}
                to={tab.path}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
                    isActive
                      ? 'bg-[var(--primary)] text-white'
                      : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-hover)]'
                  }`
                }
              >
                {tab.label}
              </NavLink>
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
            <NavLink
              key={tab.path}
              to={tab.path}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap no-underline ${
                  isActive
                    ? 'bg-[var(--primary)] text-white'
                    : 'text-[var(--text-muted)] bg-[var(--surface-hover)]'
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </div>
      </div>
    </header>
  )
}
