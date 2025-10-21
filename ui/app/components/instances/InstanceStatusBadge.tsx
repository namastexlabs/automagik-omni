import { Badge } from '@/app/components/ui/badge'

interface InstanceStatusBadgeProps {
  status?: 'connected' | 'disconnected' | 'connecting' | 'error'
  channelType: string
}

export function InstanceStatusBadge({ status, channelType }: InstanceStatusBadgeProps) {
  if (!status) {
    return (
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="bg-zinc-800 text-zinc-400">
          Unknown
        </Badge>
        <span className="text-xs text-zinc-500 capitalize">{channelType}</span>
      </div>
    )
  }

  // Map status to badge styling
  const statusConfig: Record<
    string,
    { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string; className?: string }
  > = {
    connected: {
      variant: 'default',
      label: 'Connected',
      className: 'bg-green-600 hover:bg-green-700 text-white',
    },
    disconnected: {
      variant: 'outline',
      label: 'Disconnected',
      className: 'bg-zinc-800 text-zinc-400 border-zinc-700',
    },
    connecting: {
      variant: 'secondary',
      label: 'Connecting...',
      className: 'bg-yellow-600 hover:bg-yellow-700 text-white',
    },
    error: {
      variant: 'destructive',
      label: 'Error',
      className: 'bg-red-600 hover:bg-red-700 text-white',
    },
  }

  const config = statusConfig[status] || statusConfig.error

  return (
    <div className="flex items-center gap-2">
      <Badge variant={config.variant} className={config.className}>
        {config.label}
      </Badge>
      <span className="text-xs text-zinc-500 capitalize">{channelType}</span>
    </div>
  )
}
