/**
 * Example Component: Instance Selector with Store Integration
 *
 * This demonstrates how to use the Zustand app store in a real component.
 * This file is for reference only and can be deleted after reviewing.
 */

import { useAppStore } from './index'
import type { Instance } from './index'
import { useEffect } from 'react'

/**
 * Example: Instance selector dropdown
 */
export function InstanceSelector() {
  const { selectedInstance, setSelectedInstance, instances } = useAppStore()

  return (
    <select
      value={selectedInstance || ''}
      onChange={(e) => setSelectedInstance(e.target.value || null)}
      className="px-4 py-2 border rounded-lg"
    >
      <option value="">Select Instance</option>
      {instances.map((instance) => (
        <option key={instance.name} value={instance.name}>
          {instance.name} ({instance.channelType})
        </option>
      ))}
    </select>
  )
}

/**
 * Example: Optimized component using selector
 * Only re-renders when selectedInstance changes
 */
export function CurrentInstanceDisplay() {
  const selectedInstance = useAppStore((state) => state.selectedInstance)

  if (!selectedInstance) {
    return <p className="text-gray-500">No instance selected</p>
  }

  return <p className="font-semibold">Current: {selectedInstance}</p>
}

/**
 * Example: Loading instances from API
 */
export function InstancesLoader() {
  const setInstances = useAppStore((state) => state.setInstances)

  useEffect(() => {
    async function loadInstances() {
      try {
        const response = await fetch('http://localhost:8000/api/v1/instances', {
          headers: {
            'x-api-key': import.meta.env.VITE_API_KEY || ''
          }
        })

        if (!response.ok) throw new Error('Failed to load instances')

        const data = await response.json()

        // Transform API response to store format
        const instances: Instance[] = data.instances.map((inst: any) => ({
          name: inst.name,
          channelType: inst.channel_type,
          status: inst.status
        }))

        setInstances(instances)
      } catch (error) {
        console.error('Failed to load instances:', error)
      }
    }

    loadInstances()
  }, [setInstances])

  return null // This is a utility component, no UI
}

/**
 * Example: Sidebar toggle button
 */
export function SidebarToggle() {
  const sidebarCollapsed = useAppStore((state) => state.sidebarCollapsed)
  const toggleSidebar = useAppStore((state) => state.toggleSidebar)

  return (
    <button
      onClick={toggleSidebar}
      className="p-2 rounded hover:bg-gray-100"
      aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
    >
      {sidebarCollapsed ? '→' : '←'}
    </button>
  )
}

/**
 * Example: Message count badge
 */
export function MessageBadge() {
  const count = useAppStore((state) => state.recentMessagesCount)

  if (count === 0) return null

  return (
    <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white bg-red-600 rounded-full">
      {count > 99 ? '99+' : count}
    </span>
  )
}

/**
 * Example: Complete instance card with store integration
 */
export function InstanceCard({ instance }: { instance: Instance }) {
  const { selectedInstance, setSelectedInstance } = useAppStore()
  const isSelected = selectedInstance === instance.name

  return (
    <div
      className={`
        p-4 border rounded-lg cursor-pointer transition-colors
        ${isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}
      `}
      onClick={() => setSelectedInstance(instance.name)}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{instance.name}</h3>
        {isSelected && (
          <span className="text-xs text-blue-600 font-medium">SELECTED</span>
        )}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span className="text-sm text-gray-600">{instance.channelType}</span>
        <span
          className={`
            text-xs px-2 py-1 rounded
            ${instance.status === 'connected' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}
          `}
        >
          {instance.status}
        </span>
      </div>
    </div>
  )
}

/**
 * Example: Using store outside React components
 */
export function nonReactExample() {
  // Get current state
  const state = useAppStore.getState()
  // eslint-disable-next-line no-console
  console.log('Current instance:', state.selectedInstance)

  // Update state
  useAppStore.setState({ selectedInstance: 'new-instance' })

  // Subscribe to changes
  const unsubscribe = useAppStore.subscribe(
    (state) => state.selectedInstance,
    (selectedInstance) => {
      // eslint-disable-next-line no-console
      console.log('Selected instance changed to:', selectedInstance)
    }
  )

  // Don't forget to unsubscribe when done
  return unsubscribe
}
