import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Instance {
  name: string
  channelType: string
  status: string
}

export interface AppState {
  // Selected instance across app
  selectedInstance: string | null
  setSelectedInstance: (name: string | null) => void

  // Instance cache
  instances: Instance[]
  setInstances: (instances: Instance[]) => void

  // UI state
  sidebarCollapsed: boolean
  toggleSidebar: () => void

  // Recent activity
  recentMessagesCount: number
  setRecentMessagesCount: (count: number) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      selectedInstance: null,
      setSelectedInstance: (name) => set({ selectedInstance: name }),

      instances: [],
      setInstances: (instances) => set({ instances }),

      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      recentMessagesCount: 0,
      setRecentMessagesCount: (count) => set({ recentMessagesCount: count })
    }),
    {
      name: 'automagik-omni-app-storage',
      partialize: (state) => ({
        selectedInstance: state.selectedInstance,
        sidebarCollapsed: state.sidebarCollapsed
      })
    }
  )
)
