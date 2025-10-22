import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/app/components/ui/card'
import { Badge } from '@/app/components/ui/badge'
import { Button } from '@/app/components/ui/button'
import { ChevronDown, ChevronRight, Download, Copy } from 'lucide-react'

interface TracePayload {
  id: number
  stage: string
  payload_type: string
  timestamp: string
  status_code?: number
  payload_size_original?: number
  payload_size_compressed?: number
  compression_ratio?: number
  contains_media: boolean
  contains_base64: boolean
  payload?: any
}

interface TracePayloadsPanelProps {
  traceId: string
}

export function TracePayloadsPanel({ traceId }: TracePayloadsPanelProps) {
  const { omni } = useConveyor()
  const [payloads, setPayloads] = useState<TracePayload[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadPayloads()
  }, [traceId])

  const loadPayloads = async () => {
    try {
      setLoading(true)
      // Call backend endpoint with include_payload=true
      const data = await omni.getTracePayloads(traceId, true)
      setPayloads(data)
    } catch (err) {
      console.error('Failed to load payloads:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleStage = (stage: string) => {
    const newExpanded = new Set(expandedStages)
    if (newExpanded.has(stage)) {
      newExpanded.delete(stage)
    } else {
      newExpanded.add(stage)
    }
    setExpandedStages(newExpanded)
  }

  const copyPayload = (payload: any, e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
  }

  const downloadPayload = (payload: any, stage: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `trace-${traceId}-${stage}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const getStageBadge = (stage: string) => {
    const colors: Record<string, string> = {
      webhook_received: 'bg-blue-600',
      agent_request: 'bg-purple-600',
      agent_response: 'bg-green-600',
      evolution_send: 'bg-orange-600',
    }
    return colors[stage] || 'bg-gray-600'
  }

  if (loading) {
    return <div className="text-center py-8 text-zinc-400">Loading payloads...</div>
  }

  if (payloads.length === 0) {
    return <div className="text-center py-8 text-zinc-400">No payloads available</div>
  }

  return (
    <div className="space-y-4">
      {payloads.map((payload) => {
        const isExpanded = expandedStages.has(payload.stage)

        return (
          <Card key={payload.id} className="bg-zinc-900 border-zinc-800">
            <CardHeader
              className="pb-3 cursor-pointer hover:bg-zinc-800/50 transition-colors"
              onClick={() => toggleStage(payload.stage)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleStage(payload.stage)
                    }}
                    className="h-8 w-8 p-0"
                  >
                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </Button>
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Badge className={getStageBadge(payload.stage)}>
                        {payload.stage.replace(/_/g, ' ')}
                      </Badge>
                      <span className="text-zinc-400 text-sm font-normal">
                        {payload.payload_type}
                      </span>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {new Date(payload.timestamp).toLocaleString()}
                    </CardDescription>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {payload.payload_size_original && (
                    <div className="text-xs text-zinc-400">
                      {(payload.payload_size_original / 1024).toFixed(1)} KB
                      {payload.compression_ratio && (
                        <span className="ml-2">({(payload.compression_ratio * 100).toFixed(0)}% compressed)</span>
                      )}
                    </div>
                  )}
                  {payload.payload && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => copyPayload(payload.payload, e)}
                      >
                        <Copy className="h-3 w-3 mr-1" />
                        Copy
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => downloadPayload(payload.payload, payload.stage, e)}
                      >
                        <Download className="h-3 w-3 mr-1" />
                        Download
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </CardHeader>

            {isExpanded && payload.payload && (
              <CardContent>
                <pre className="bg-black p-4 rounded-lg overflow-auto max-h-96 text-xs text-zinc-300">
                  {JSON.stringify(payload.payload, null, 2)}
                </pre>
              </CardContent>
            )}
          </Card>
        )
      })}
    </div>
  )
}
