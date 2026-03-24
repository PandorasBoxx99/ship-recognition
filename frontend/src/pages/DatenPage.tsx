import { NavLink, Outlet, useLocation, Navigate } from 'react-router-dom'

const tabs = [
  { path: '/daten/scraper', label: 'Scraper' },
  { path: '/daten/extraktor', label: 'Extraktor' },
  { path: '/daten/db', label: 'Datenbank' },
]

export function DatenPage() {
  const location = useLocation()

  // Redirect bare /daten to /daten/scraper
  if (location.pathname === '/daten') {
    return <Navigate to="/daten/scraper" replace />
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Daten</h1>

      {/* Sub-Navigation Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {tabs.map(tab => (
          <NavLink
            key={tab.path}
            to={tab.path}
            className={({ isActive }) =>
              `px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? 'border-[var(--primary)] text-[var(--primary)]'
                  : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      {/* Active sub-page */}
      <Outlet />
    </div>
  )
}
