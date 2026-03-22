import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header.tsx'
import { useUIStore } from '@/stores/uiStore.ts'
import { DashboardPage } from '@/pages/DashboardPage.tsx'
import { ScraperPage } from '@/pages/ScraperPage.tsx'
import { ShipsPage } from '@/pages/ShipsPage.tsx'
import { ClassifyPage } from '@/pages/ClassifyPage.tsx'
import { TrainingPage } from '@/pages/TrainingPage.tsx'
import { SettingsPage } from '@/pages/SettingsPage.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
    },
  },
})

function PageRouter() {
  const activeTab = useUIStore((s) => s.activeTab)

  switch (activeTab) {
    case 'dashboard': return <DashboardPage />
    case 'scraper': return <ScraperPage />
    case 'ships': return <ShipsPage />
    case 'classify': return <ClassifyPage />
    case 'training': return <TrainingPage />
    case 'settings': return <SettingsPage />
    default: return <DashboardPage />
  }
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen">
        <Header />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <PageRouter />
        </main>
      </div>
    </QueryClientProvider>
  )
}
