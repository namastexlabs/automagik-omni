import { Input } from '@/app/components/ui/input'

interface ContactSearchProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export function ContactSearch({ value, onChange, disabled }: ContactSearchProps) {
  return (
    <div className="flex-1 max-w-sm">
      <Input
        type="text"
        placeholder="Search contacts by name..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full"
      />
    </div>
  )
}
