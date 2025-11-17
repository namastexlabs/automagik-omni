import { useState } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/app/components/ui/select'
import { Input } from '@/app/components/ui/input'
import type { Instance } from '@/lib/main/omni-api-client'

interface RuleFiltersProps {
  instances: Instance[]
  onFilterChange: (filters: { search: string; instanceName: string; ruleType: string }) => void
  className?: string
}

export function RuleFilters({
  instances,
  onFilterChange,
  className,
}: RuleFiltersProps) {
  const [search, setSearch] = useState('')
  const [instanceName, setInstanceName] = useState('')
  const [ruleType, setRuleType] = useState('')

  const handleSearchChange = (value: string) => {
    setSearch(value)
    onFilterChange({ search: value, instanceName, ruleType })
  }

  const handleInstanceChange = (value: string) => {
    const instance = value === 'all' ? '' : value
    setInstanceName(instance)
    onFilterChange({ search, instanceName: instance, ruleType })
  }

  const handleTypeChange = (value: string) => {
    const type = value === 'all' ? '' : value
    setRuleType(type)
    onFilterChange({ search, instanceName, ruleType: type })
  }

  return (
    <div className={`flex flex-col sm:flex-row gap-4 ${className || ''}`}>
      <div className="flex-1">
        <Input
          placeholder="Search by phone number..."
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="bg-zinc-800 border-zinc-700 text-white"
        />
      </div>

      <div className="w-full sm:w-48">
        <Select
          value={instanceName || 'all'}
          onValueChange={handleInstanceChange}
        >
          <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
            <SelectValue placeholder="Filter by scope" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Scopes</SelectItem>
            {instances.map((instance) => (
              <SelectItem key={instance.name} value={instance.name}>
                {instance.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="w-full sm:w-40">
        <Select value={ruleType || 'all'} onValueChange={handleTypeChange}>
          <SelectTrigger className="bg-zinc-800 border-zinc-700 text-white">
            <SelectValue placeholder="All Types" />
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
