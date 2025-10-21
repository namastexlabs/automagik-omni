import { Badge } from '@/app/components/ui/badge'

interface ChatTypeFilterProps {
  selected: string | undefined
  onChange: (type: string | undefined) => void
  disabled?: boolean
}

const chatTypes = [
  { value: undefined, label: 'All' },
  { value: 'direct', label: 'Direct' },
  { value: 'group', label: 'Group' },
  { value: 'channel', label: 'Channel' },
]

export function ChatTypeFilter({ selected, onChange, disabled }: ChatTypeFilterProps) {
  return (
    <div className="flex gap-2">
      {chatTypes.map((type) => (
        <button
          key={type.label}
          onClick={() => onChange(type.value)}
          disabled={disabled}
          className="focus:outline-none disabled:opacity-50"
        >
          <Badge
            variant={selected === type.value ? 'default' : 'outline'}
            className="cursor-pointer hover:bg-zinc-800"
          >
            {type.label}
          </Badge>
        </button>
      ))}
    </div>
  )
}
