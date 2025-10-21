import { useState, useEffect } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import { Input } from '@/app/components/ui/input'
import { useConveyor } from '@/app/hooks/use-conveyor'
import type { Instance } from '@/lib/main/omni-api-client'

interface RuleFiltersProps {
  onInstanceFilterChange: (instanceName: string | null) => void
  onTypeFilterChange: (type: string | null) => void
  onSearchChange: (search: string) => void
  instanceFilter: string | null
  typeFilter: string | null
  searchQuery: string
}

export function RuleFilters({
  onInstanceFilterChange,
  onTypeFilterChange,
  onSearchChange,
  instanceFilter,
  typeFilter,
  searchQuery,
}: RuleFiltersProps) {
  const { omni } = useConveyor()
  const [instances, setInstances] = useState<Instance[]>([])
  const [loading, setLoading] = useState(false)

  const loadInstances = async () => {
    try {
      setLoading(true)
      const data = await omni.getInstances()
      setInstances(data)
    } catch (err) {
      console.error('Failed to load instances:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInstances()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleInstanceChange = (value: string) => {
    if (value === 'all') {
      onInstanceFilterChange(null)
    } else if (value === 'global') {
      onInstanceFilterChange('')
    } else {
      onInstanceFilterChange(value)
    }
  }

  const handleTypeChange = (value: string) => {
    onTypeFilterChange(value === 'all' ? null : value)
  }

  return (
    <div className="flex flex-col sm:flex-row gap-4">
      <div className="flex-1">
        <Input
          placeholder="Search by phone number..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="bg-zinc-800 border-zinc-700 text-white"
        />
      </div>

      <div className="w-full sm:w-48">
        <Select
          value={
            instanceFilter === null ? 'all' : instanceFilter === '' ? 'global' : instanceFilter
          }
          onValueChange={handleInstanceChange}
          disabled={loading}
        >
          <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
            <SelectValue placeholder="Filter by scope" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Scopes</SelectItem>
            <SelectItem value="global">Global Only</SelectItem>
            {instances.map((instance) => (
              <SelectItem key={instance.name} value={instance.name}>
                {instance.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="w-full sm:w-40">
        <Select value={typeFilter || 'all'} onValueChange={handleTypeChange}>
          <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="allow">Allow</SelectItem>
            <SelectItem value="block">Block</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}
