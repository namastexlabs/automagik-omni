# Zustand App Store

Global state management for Automagik Omni UI using Zustand.

## Features

- **Persistent Storage**: Selected instance and sidebar state persist across sessions
- **TypeScript Support**: Full type safety with exported interfaces
- **Lightweight**: Minimal overhead with Zustand's simple API
- **React Integration**: Works seamlessly with React hooks

## Store Structure

### State Properties

- `selectedInstance`: Currently selected instance name (persisted)
- `instances`: Cached list of all instances
- `sidebarCollapsed`: Sidebar collapsed/expanded state (persisted)
- `recentMessagesCount`: Count of recent unread messages

### Actions

- `setSelectedInstance(name)`: Set the currently selected instance
- `setInstances(instances)`: Update the instances cache
- `toggleSidebar()`: Toggle sidebar collapsed state
- `setRecentMessagesCount(count)`: Update recent messages count

## Usage Examples

### Basic Usage in Components

```typescript
import { useAppStore } from '@/store'

function InstanceSelector() {
  const { selectedInstance, setSelectedInstance, instances } = useAppStore()

  return (
    <select
      value={selectedInstance || ''}
      onChange={(e) => setSelectedInstance(e.target.value)}
    >
      <option value="">Select Instance</option>
      {instances.map(instance => (
        <option key={instance.name} value={instance.name}>
          {instance.name} ({instance.channelType})
        </option>
      ))}
    </select>
  )
}
```

### Using Individual State Slices (Optimized)

```typescript
import { useAppStore } from '@/store'

function Sidebar() {
  // Only re-render when sidebarCollapsed changes
  const sidebarCollapsed = useAppStore(state => state.sidebarCollapsed)
  const toggleSidebar = useAppStore(state => state.toggleSidebar)

  return (
    <div className={sidebarCollapsed ? 'w-16' : 'w-64'}>
      <button onClick={toggleSidebar}>
        {sidebarCollapsed ? '→' : '←'}
      </button>
    </div>
  )
}
```

### Setting Instances from API

```typescript
import { useAppStore } from '@/store'
import { useEffect } from 'react'

function InstancesLoader() {
  const setInstances = useAppStore(state => state.setInstances)

  useEffect(() => {
    async function loadInstances() {
      const response = await fetch('/api/v1/instances')
      const data = await response.json()
      setInstances(data.instances)
    }

    loadInstances()
  }, [setInstances])

  return null
}
```

### Reading Selected Instance Across Pages

```typescript
import { useAppStore } from '@/store'

function MessagesPage() {
  const selectedInstance = useAppStore(state => state.selectedInstance)

  if (!selectedInstance) {
    return <div>Please select an instance</div>
  }

  return <MessagesList instanceName={selectedInstance} />
}
```

### Using with TypeScript Types

```typescript
import { useAppStore, type Instance } from '@/store'

function InstanceCard({ instance }: { instance: Instance }) {
  const { selectedInstance, setSelectedInstance } = useAppStore()
  const isSelected = selectedInstance === instance.name

  return (
    <div
      className={isSelected ? 'selected' : ''}
      onClick={() => setSelectedInstance(instance.name)}
    >
      <h3>{instance.name}</h3>
      <p>{instance.channelType}</p>
      <span>{instance.status}</span>
    </div>
  )
}
```

### Accessing Store Outside Components

```typescript
import { useAppStore } from '@/store'

// Get current state value
const currentInstance = useAppStore.getState().selectedInstance

// Subscribe to changes
const unsubscribe = useAppStore.subscribe(
  state => state.selectedInstance,
  (selectedInstance) => {
    console.log('Selected instance changed:', selectedInstance)
  }
)

// Update state
useAppStore.setState({ selectedInstance: 'my-instance' })
```

## Persistence

The following state is automatically persisted to `localStorage`:
- `selectedInstance`
- `sidebarCollapsed`

Other state (instances cache, message counts) is ephemeral and cleared on page reload.

## TypeScript Types

All types are exported from the store:

```typescript
import type { Instance, AppState } from '@/store'
// or
import type { Instance } from '@/types'
```

## Best Practices

1. **Use Selectors**: Extract only the state you need to minimize re-renders
   ```typescript
   const name = useAppStore(state => state.selectedInstance)
   ```

2. **Separate Actions**: Extract actions separately if you don't need state
   ```typescript
   const setInstance = useAppStore(state => state.setSelectedInstance)
   ```

3. **Type Safety**: Always use TypeScript types for better IDE support
   ```typescript
   const instances: Instance[] = useAppStore(state => state.instances)
   ```

4. **Avoid Store Mutations**: Always use provided actions
   ```typescript
   // ✅ Good
   setInstances([...instances, newInstance])

   // ❌ Bad - Don't mutate store directly
   instances.push(newInstance)
   ```
