import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header.tsx'
import { DashboardPage } from '@/pages/DashboardPage.tsx'
import { ScraperPage } from '@/pages/ScraperPage.tsx'
import { ShipsPage } from '@/pages/ShipsPage.tsx'
import { ClassifyPage } from '@/pages/ClassifyPage.tsx'
import { TrainingPage } from '@/pages/TrainingPage.tsx'
import { SettingsPage } from '@/pages/SettingsPage.tsx'
import { DokuPage } from '@/pages/DokuPage.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen">
          <Header />
          <main className="max-w-7xl mx-auto px-4 py-6">
            <Routes>
              <Route path="/Dashboard" element={<DashboardPage />} />
              <Route path="/Scraper" element={<ScraperPage />} />
              <Route path="/Schiffe" element={<ShipsPage />} />
              <Route path="/Erkennung" element={<ClassifyPage />} />
              <Route path="/KI-Erkennung" element={<Navigate to="/Erkennung" replace />} />
              <Route path="/Training" element={<TrainingPage />} />
              <Route path="/Einstellungen" element={<SettingsPage />} />
              <Route path="/Doku" element={<DokuPage />} />
              <Route path="/" element={<Navigate to="/Dashboard" replace />} />
              <Route path="*" element={<Navigate to="/Dashboard" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
