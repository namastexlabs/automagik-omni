import { Badge } from '@/app/components/ui/badge'

interface InstanceStatusBadgeProps {
  status?: 'connected' | 'disconnected' | 'connecting' | 'error'
  channelType: string
}

export function InstanceStatusBadge({ status, channelType }: InstanceStatusBadgeProps) {
  if (!status) {
    return <Badge variant="outline">Unknown</Badge>
  }

  const statusConfig = {
    connected: { variant: 'default' as const, label: 'Connected' },
    disconnected: { variant: 'destructive' as const, label: 'Disconnected' },
    connecting: { variant: 'outline' as const, label: 'Connecting...' },
    error: { variant: 'destructive' as const, label: 'Error' },
  }

  const config = statusConfig[status]

  return (
    <div className="flex items-center gap-2">
      <Badge variant={config.variant}>{config.label}</Badge>
      <span className="text-xs text-zinc-500">{channelType}</span>
    </div>
  )
}
