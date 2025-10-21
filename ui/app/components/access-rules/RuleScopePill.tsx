import { Badge } from '@/app/components/ui/badge'

interface RuleScopePillProps {
  instanceName: string | null
}

export function RuleScopePill({ instanceName }: RuleScopePillProps) {
  if (!instanceName) {
    return (
      <Badge className="bg-amber-900/50 text-amber-300 border-amber-600 hover:bg-amber-900/70">
        <span className="mr-1">🌍</span>
        Global
      </Badge>
    )
  }

  return (
    <Badge className="bg-blue-900/50 text-blue-300 border-blue-600 hover:bg-blue-900/70">
      {instanceName}
    </Badge>
  )
}
