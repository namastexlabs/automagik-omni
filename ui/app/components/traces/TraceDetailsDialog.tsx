import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/app/components/ui/dialog'
import { Badge } from '@/app/components/ui/badge'
import { Button } from '@/app/components/ui/button'
import type { Trace } from '@/lib/conveyor/schemas/omni-schema'
import { format } from 'date-fns'

interface TraceDetailsDialogProps {
  trace: Trace | null
  open: boolean
  onClose: () => void
}

export function TraceDetailsDialog({ trace, open, onClose }: TraceDetailsDialogProps) {
  if (!trace) return null

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
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl bg-zinc-900 border-zinc-800 text-white max-h-[80vh] overflow-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">Trace Details</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Complete information about this message trace
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Basic Information */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-zinc-400 mb-1">Trace ID</p>
              <p className="text-sm font-mono text-zinc-200 break-all">{trace.id}</p>
            </div>
            <div>
              <p className="text-sm text-zinc-400 mb-1">Status</p>
              <Badge variant={getStatusBadgeVariant(trace.status)}>{trace.status}</Badge>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-zinc-400 mb-1">Instance</p>
              <p className="text-sm text-zinc-200">{trace.instance_name}</p>
            </div>
            <div>
              <p className="text-sm text-zinc-400 mb-1">Message Type</p>
              <p className="text-sm text-zinc-200 capitalize">{trace.message_type}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-zinc-400 mb-1">Phone Number</p>
              <p className="text-sm font-mono text-zinc-200">{trace.phone_number}</p>
            </div>
            <div>
              <p className="text-sm text-zinc-400 mb-1">Created At</p>
              <p className="text-sm text-zinc-200">
                {format(new Date(trace.created_at), 'MMM dd, yyyy HH:mm:ss')}
              </p>
            </div>
          </div>

          {/* Error Message */}
          {trace.error && (
            <div>
              <p className="text-sm text-zinc-400 mb-2">Error</p>
              <div className="bg-red-900/20 border border-red-500/30 rounded-md p-3">
                <p className="text-sm text-red-300 font-mono">{trace.error}</p>
              </div>
            </div>
          )}

          {/* Payload */}
          {trace.payload && (
            <div>
              <p className="text-sm text-zinc-400 mb-2">Payload</p>
              <div className="bg-zinc-800 border border-zinc-700 rounded-md p-3 max-h-60 overflow-auto">
                <pre className="text-xs text-zinc-300 font-mono whitespace-pre-wrap">
                  {JSON.stringify(trace.payload, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end mt-6">
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
