import { Select } from '@/app/components/ui/select'
import { Input } from '@/app/components/ui/input'
import { Button } from '@/app/components/ui/button'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'

interface TraceFiltersProps {
  instances: Instance[]
  selectedInstance: string
  startDate: string
  endDate: string
  status: string
  messageType: string
  onInstanceChange: (value: string) => void
  onStartDateChange: (value: string) => void
  onEndDateChange: (value: string) => void
  onStatusChange: (value: string) => void
  onMessageTypeChange: (value: string) => void
  onRefresh: () => void
  loading?: boolean
}

export function TraceFilters({
  instances,
  selectedInstance,
  startDate,
  endDate,
  status,
  messageType,
  onInstanceChange,
  onStartDateChange,
  onEndDateChange,
  onStatusChange,
  onMessageTypeChange,
  onRefresh,
  loading,
}: TraceFiltersProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
      {/* Instance Selector */}
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-2">Instance</label>
        <Select value={selectedInstance} onChange={(e) => onInstanceChange(e.target.value)}>
          <option value="">All Instances</option>
          {instances.map((instance) => (
            <option key={instance.id} value={instance.name}>
              {instance.name}
            </option>
          ))}
        </Select>
      </div>

      {/* Start Date */}
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-2">Start Date</label>
        <Input
          type="date"
          value={startDate}
          onChange={(e) => onStartDateChange(e.target.value)}
        />
      </div>

      {/* End Date */}
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-2">End Date</label>
        <Input type="date" value={endDate} onChange={(e) => onEndDateChange(e.target.value)} />
      </div>

      {/* Status Filter */}
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-2">Status</label>
        <Select value={status} onChange={(e) => onStatusChange(e.target.value)}>
          <option value="">All</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="processing">Processing</option>
          <option value="received">Received</option>
        </Select>
      </div>

      {/* Message Type Filter */}
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-2">Message Type</label>
        <Select value={messageType} onChange={(e) => onMessageTypeChange(e.target.value)}>
          <option value="">All Types</option>
          <option value="text">Text</option>
          <option value="media">Media</option>
          <option value="audio">Audio</option>
          <option value="sticker">Sticker</option>
          <option value="contact">Contact</option>
          <option value="reaction">Reaction</option>
        </Select>
      </div>

      {/* Refresh Button */}
      <div className="flex items-end">
        <Button onClick={onRefresh} disabled={loading} className="w-full">
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>
    </div>
  )
}
