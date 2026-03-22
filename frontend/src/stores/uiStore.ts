import { create } from 'zustand'
import type { TabId } from '@/types/index.ts'

interface UIState {
  activeTab: TabId
  setActiveTab: (tab: TabId) => void
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: 'dashboard',
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
