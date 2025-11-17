import { useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  ColumnDef,
  flexRender,
  SortingState,
} from '@tanstack/react-table'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/app/components/ui/table'
import { Button } from '@/app/components/ui/button'
import { Badge } from '@/app/components/ui/badge'
import { InstanceStatusBadge } from './InstanceStatusBadge'
import { MessageSquareText, MessageSquareDashed } from 'lucide-react'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'
import { useConveyor } from '@/app/hooks/use-conveyor'

interface InstanceTableProps {
  instances: Instance[]
  onRefresh: () => void
  onShowQR: (instanceName: string) => void
  onDelete: (instanceName: string) => void
  onEdit: (instance: Instance) => void
}

export function InstanceTable({ instances, onRefresh, onShowQR, onDelete, onEdit }: InstanceTableProps) {
  const { omni } = useConveyor()
  const [sorting, setSorting] = useState<SortingState>([])
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const handleAction = async (
    action: 'connect' | 'disconnect' | 'restart',
    instanceName: string
  ) => {
    try {
      setActionLoading(`${action}-${instanceName}`)

      if (action === 'connect') {
        await omni.connectInstance(instanceName)
      } else if (action === 'disconnect') {
        await omni.disconnectInstance(instanceName)
      } else if (action === 'restart') {
        await omni.restartInstance(instanceName)
      }

      await new Promise((resolve) => setTimeout(resolve, 1000))
      onRefresh()
    } catch (err) {
      console.error(`Failed to ${action} instance:`, err)
    } finally {
      setActionLoading(null)
    }
  }

  const handleToggleAutoSplit = async (instanceName: string, currentValue: boolean) => {
    try {
      setActionLoading(`autosplit-${instanceName}`)

      // Update instance with toggled value
      await omni.updateInstance(instanceName, {
        enable_auto_split: !currentValue,
      })

      // Refresh to show updated value
      await new Promise((resolve) => setTimeout(resolve, 500))
      onRefresh()
    } catch (err) {
      console.error('Failed to toggle auto-split:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const columns: ColumnDef<Instance>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div className="font-medium text-white">
          {row.original.name}
          {row.original.is_default && (
            <span className="ml-2 text-xs text-yellow-400">(Default)</span>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'channel_type',
      header: 'Channel Type',
      cell: ({ row }) => (
        <span className="capitalize text-zinc-300">{row.original.channel_type}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <InstanceStatusBadge status={row.original.status} channelType={row.original.channel_type} />
      ),
    },
    {
      accessorKey: 'enable_auto_split',
      header: 'Auto-Split',
      cell: ({ row }) => {
        const enabled = row.original.enable_auto_split ?? true
        const isLoading = actionLoading === `autosplit-${row.original.name}`

        return (
          <Badge
            variant={enabled ? 'default' : 'outline'}
            className={`cursor-pointer transition-opacity ${
              enabled ? 'bg-green-600 hover:bg-green-700 border-green-600' : 'text-zinc-400 hover:bg-zinc-800'
            } ${isLoading ? 'opacity-50 cursor-wait' : ''}`}
            onClick={() => !isLoading && handleToggleAutoSplit(row.original.name, enabled)}
            title={`Click to turn ${enabled ? 'OFF' : 'ON'}`}
          >
            {enabled ? (
              <>
                <MessageSquareText className="h-3 w-3" />
                <span>{isLoading ? '...' : 'ON'}</span>
              </>
            ) : (
              <>
                <MessageSquareDashed className="h-3 w-3" />
                <span>{isLoading ? '...' : 'OFF'}</span>
              </>
            )}
          </Badge>
        )
      },
    },
    {
      accessorKey: 'agent_api_url',
      header: 'Agent API',
      cell: ({ row }) => (
        <span className="text-sm text-zinc-400 truncate max-w-[200px] block">
          {row.original.agent_api_url}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const instance = row.original
        const isWhatsApp = instance.channel_type === 'whatsapp'

        return (
          <div className="flex gap-2 flex-wrap">
            {isWhatsApp && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onShowQR(instance.name)}
                disabled={!!actionLoading}
              >
                QR Code
              </Button>
            )}

            {instance.status === 'disconnected' && (
              <Button
                size="sm"
                variant="default"
                onClick={() => handleAction('connect', instance.name)}
                disabled={actionLoading === `connect-${instance.name}`}
              >
                {actionLoading === `connect-${instance.name}` ? 'Connecting...' : 'Connect'}
              </Button>
            )}

            {instance.status === 'connected' && (
              <>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleAction('restart', instance.name)}
                  disabled={actionLoading === `restart-${instance.name}`}
                >
                  {actionLoading === `restart-${instance.name}` ? 'Restarting...' : 'Restart'}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleAction('disconnect', instance.name)}
                  disabled={actionLoading === `disconnect-${instance.name}`}
                >
                  {actionLoading === `disconnect-${instance.name}`
                    ? 'Disconnecting...'
                    : 'Disconnect'}
                </Button>
              </>
            )}

            <Button
              size="sm"
              variant="destructive"
              onClick={() => onDelete(instance.name)}
              disabled={!!actionLoading}
            >
              Delete
            </Button>
          </div>
        )
      },
    },
  ]

  const table = useReactTable({
    data: instances,
    columns,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && 'selected'}
                className="cursor-pointer hover:bg-zinc-800/50 transition-colors"
                onClick={(e) => {
                  // Don't trigger row click if clicking on buttons, badges, or other interactive elements
                  const target = e.target as HTMLElement
                  if (
                    target.closest('button') ||
                    target.closest('[role="button"]') ||
                    target.closest('a')
                  ) {
                    return
                  }
                  onEdit(row.original)
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center text-zinc-400">
                No instances found. Create your first instance to get started.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
