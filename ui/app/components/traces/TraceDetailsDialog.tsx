import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/app/components/ui/dialog'
import { Badge } from '@/app/components/ui/badge'
import { Button } from '@/app/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs'
import { TracePayloadsPanel } from './TracePayloadsPanel'
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
      <DialogContent className="max-w-4xl bg-zinc-900 border-zinc-800 text-white max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">Trace Details</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Complete information about this message trace
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="details" className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="mb-4">
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="payloads">Payloads</TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="flex-1 overflow-auto space-y-4 mt-0">
          {/* Basic Information */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-zinc-400 mb-1">Trace ID</p>
              <p className="text-sm font-mono text-zinc-200 break-all">{trace.trace_id}</p>
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
              <p className="text-sm text-zinc-200 capitalize">{trace.message_type || 'N/A'}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-zinc-400 mb-1">Phone Number</p>
              <p className="text-sm font-mono text-zinc-200">{trace.sender_phone || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-zinc-400 mb-1">Sender Name</p>
              <p className="text-sm text-zinc-200">{trace.sender_name || 'N/A'}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-zinc-400 mb-1">WhatsApp Message ID</p>
              <p className="text-sm font-mono text-zinc-200 break-all">{trace.whatsapp_message_id || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-zinc-400 mb-1">Session Name</p>
              <p className="text-sm text-zinc-200">{trace.session_name || 'N/A'}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-zinc-400 mb-1">Has Media</p>
              <p className="text-sm text-zinc-200">{trace.has_media ? 'Yes' : 'No'}</p>
            </div>
            <div>
              <p className="text-sm text-zinc-400 mb-1">Has Quoted Message</p>
              <p className="text-sm text-zinc-200">{trace.has_quoted_message ? 'Yes' : 'No'}</p>
            </div>
          </div>

          {/* Timestamps */}
          <div className="border-t border-zinc-800 pt-4">
            <h4 className="text-sm font-semibold text-zinc-300 mb-3">Timestamps</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-zinc-400 mb-1">Received At</p>
                <p className="text-sm text-zinc-200">
                  {trace.received_at ? format(new Date(trace.received_at), 'MMM dd, yyyy HH:mm:ss') : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-zinc-400 mb-1">Completed At</p>
                <p className="text-sm text-zinc-200">
                  {trace.completed_at ? format(new Date(trace.completed_at), 'MMM dd, yyyy HH:mm:ss') : 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Processing Times */}
          {(trace.agent_processing_time_ms !== null || trace.total_processing_time_ms !== null) && (
            <div className="border-t border-zinc-800 pt-4">
              <h4 className="text-sm font-semibold text-zinc-300 mb-3">Processing Times</h4>
              <div className="grid grid-cols-2 gap-4">
                {trace.agent_processing_time_ms !== null && (
                  <div>
                    <p className="text-sm text-zinc-400 mb-1">Agent Processing Time</p>
                    <p className="text-sm text-zinc-200">{trace.agent_processing_time_ms} ms</p>
                  </div>
                )}
                {trace.total_processing_time_ms !== null && (
                  <div>
                    <p className="text-sm text-zinc-400 mb-1">Total Processing Time</p>
                    <p className="text-sm text-zinc-200">{trace.total_processing_time_ms} ms</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Success Flags */}
          {(trace.agent_response_success !== null || trace.evolution_success !== null) && (
            <div className="border-t border-zinc-800 pt-4">
              <h4 className="text-sm font-semibold text-zinc-300 mb-3">Success Indicators</h4>
              <div className="grid grid-cols-2 gap-4">
                {trace.agent_response_success !== null && (
                  <div>
                    <p className="text-sm text-zinc-400 mb-1">Agent Response Success</p>
                    <Badge variant={trace.agent_response_success ? 'default' : 'destructive'}>
                      {trace.agent_response_success ? 'Success' : 'Failed'}
                    </Badge>
                  </div>
                )}
                {trace.evolution_success !== null && (
                  <div>
                    <p className="text-sm text-zinc-400 mb-1">Evolution API Success</p>
                    <Badge variant={trace.evolution_success ? 'default' : 'destructive'}>
                      {trace.evolution_success ? 'Success' : 'Failed'}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error Information */}
          {(trace.error_message || trace.error_stage) && (
            <div className="border-t border-zinc-800 pt-4">
              <h4 className="text-sm font-semibold text-red-300 mb-3">Error Details</h4>
              {trace.error_stage && (
                <div className="mb-3">
                  <p className="text-sm text-zinc-400 mb-1">Error Stage</p>
                  <p className="text-sm text-red-300 font-mono">{trace.error_stage}</p>
                </div>
              )}
              {trace.error_message && (
                <div>
                  <p className="text-sm text-zinc-400 mb-2">Error Message</p>
                  <div className="bg-red-900/20 border border-red-500/30 rounded-md p-3">
                    <p className="text-sm text-red-300 font-mono break-words">{trace.error_message}</p>
                  </div>
                </div>
              )}
            </div>
          )}
          </TabsContent>

          <TabsContent value="payloads" className="flex-1 overflow-auto mt-0">
            <TracePayloadsPanel traceId={trace.trace_id} />
          </TabsContent>
        </Tabs>

        <div className="flex justify-end mt-4 pt-4 border-t border-zinc-800">
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
