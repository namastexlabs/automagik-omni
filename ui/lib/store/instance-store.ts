import { create } from 'zustand'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'

interface InstanceStore {
  instances: Instance[]
  selectedInstance: Instance | null
  loading: boolean
  error: string | null
  setInstances: (instances: Instance[]) => void
  setSelectedInstance: (instance: Instance | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void
}

export const useInstanceStore = create<InstanceStore>((set) => ({
  instances: [],
  selectedInstance: null,
  loading: false,
  error: null,
  setInstances: (instances) => set({ instances }),
  setSelectedInstance: (instance) => set({ selectedInstance: instance }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
}))
