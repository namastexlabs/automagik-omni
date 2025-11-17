import { Badge } from '@/app/components/ui/badge'

interface RuleTypeBadgeProps {
  type: 'allow' | 'block'
}

export function RuleTypeBadge({ type }: RuleTypeBadgeProps) {
  if (type === 'allow') {
    return (
      <Badge className="bg-green-900/50 text-green-300 border-green-600 hover:bg-green-900/70">
        <span className="mr-1">✓</span>
        Allow
      </Badge>
    )
  }

  return (
    <Badge className="bg-red-900/50 text-red-300 border-red-600 hover:bg-red-900/70">
      <span className="mr-1">✗</span>
      Block
    </Badge>
  )
}
