import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/app/components/ui/table'
import { Badge } from '@/app/components/ui/badge'
import { Button } from '@/app/components/ui/button'
import type { Trace } from '@/lib/conveyor/schemas/omni-schema'
import { format } from 'date-fns'

interface TracesTableProps {
  traces: Trace[]
  totalCount: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
  onTraceClick: (trace: Trace) => void
  loading?: boolean
}

export function TracesTable({
  traces,
  totalCount,
  page,
  pageSize,
  onPageChange,
  onTraceClick,
  loading,
}: TracesTableProps) {
  const totalPages = Math.ceil(totalCount / pageSize)
  const hasNextPage = page < totalPages
  const hasPrevPage = page > 1

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed':
        return 'default'
      case 'failed':
        return 'destructive'
      case 'processing':
        return 'outline'
      default:
        return 'outline'
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-zinc-800 bg-zinc-900">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-zinc-400">Timestamp</TableHead>
              <TableHead className="text-zinc-400">Instance</TableHead>
              <TableHead className="text-zinc-400">Phone</TableHead>
              <TableHead className="text-zinc-400">Type</TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
              <TableHead className="text-zinc-400 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-zinc-500 py-8">
                  Loading traces...
                </TableCell>
              </TableRow>
            ) : traces.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-zinc-500 py-8">
                  No traces found
                </TableCell>
              </TableRow>
            ) : (
              traces.map((trace) => (
                <TableRow key={trace.trace_id} className="hover:bg-zinc-800/50 cursor-pointer">
                  <TableCell className="text-zinc-300">
                    {format(new Date(trace.received_at), 'MMM dd, yyyy HH:mm:ss')}
                  </TableCell>
                  <TableCell className="text-zinc-300">{trace.instance_name}</TableCell>
                  <TableCell className="text-zinc-300 font-mono text-sm">
                    {trace.sender_phone}
                  </TableCell>
                  <TableCell className="text-zinc-300 capitalize">{trace.message_type}</TableCell>
                  <TableCell>
                    <Badge variant={getStatusBadgeVariant(trace.trace_status)}>{trace.trace_status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onTraceClick(trace)}
                      className="text-xs"
                    >
                      View Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-zinc-400">
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of{' '}
            {totalCount} traces
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={!hasPrevPage || loading}
            >
              Previous
            </Button>
            <div className="flex items-center gap-2 px-4 text-sm text-zinc-300">
              Page {page} of {totalPages}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={!hasNextPage || loading}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
