import { useState, useEffect } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { TraceFilters } from '@/app/components/traces/TraceFilters'
import { AnalyticsCards } from '@/app/components/traces/AnalyticsCards'
import { MessagesOverTimeChart } from '@/app/components/traces/MessagesOverTimeChart'
import { SuccessRateChart } from '@/app/components/traces/SuccessRateChart'
import { MessageTypesChart } from '@/app/components/traces/MessageTypesChart'
import { TracesTable } from '@/app/components/traces/TracesTable'
import { TraceDetailsDialog } from '@/app/components/traces/TraceDetailsDialog'
import { Button } from '@/app/components/ui/button'
import type { Instance, Trace } from '@/lib/conveyor/schemas/omni-schema'
import { format, subDays } from 'date-fns'

interface AnalyticsData {
  total_messages: number
  success_rate: number
  average_duration: number
  failed_count: number
  messages_over_time: Array<{ date: string; count: number }>
  success_vs_failed: Array<{ name: string; value: number }>
  message_types: Array<{ type: string; count: number }>
  top_contacts: Array<{ phone: string; count: number }>
}

export default function Traces() {
  const { omni } = useConveyor()

  // State
  const [instances, setInstances] = useState<Instance[]>([])
  const [traces, setTraces] = useState<Trace[]>([])
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [selectedInstance, setSelectedInstance] = useState('')
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 7), 'yyyy-MM-dd'))
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [status, setStatus] = useState('')
  const [messageType, setMessageType] = useState('')

  // Pagination
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [totalCount, setTotalCount] = useState(0)

  // Load instances on mount
  useEffect(() => {
    loadInstances()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load data when filters change
  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedInstance, startDate, endDate, status, messageType, page])

  const loadInstances = async () => {
    try {
      const instancesData = await omni.listInstances()
      setInstances(instancesData)
    } catch (err) {
      console.error('Failed to load instances:', err)
    }
  }

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load traces
      const tracesResponse = await omni.listTraces(
        selectedInstance || undefined,
        page,
        pageSize,
        status || undefined
      )
      setTraces(tracesResponse.data)
      setTotalCount(tracesResponse.total_count)

      // Load analytics
      const analyticsData = await omni.getTraceAnalytics({
        instanceName: selectedInstance || undefined,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      })
      setAnalytics(analyticsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
      console.error('Failed to load traces data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    setPage(1)
    loadData()
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleTraceClick = async (trace: Trace) => {
    try {
      // Fetch full trace details if not already loaded
      const fullTrace = trace.payload ? trace : await omni.getTrace(trace.trace_id)
      setSelectedTrace(fullTrace)
    } catch (err) {
      console.error('Failed to load trace details:', err)
      setSelectedTrace(trace)
    }
  }

  const handleExportCSV = () => {
    if (!traces || traces.length === 0) return

    const headers = ['Timestamp', 'Instance', 'Phone', 'Type', 'Status', 'Error']
    const rows = traces.map((trace) => [
      trace.received_at,
      trace.instance_name,
      trace.sender_phone,
      trace.message_type,
      trace.status,
      trace.error_message || '',
    ])

    const csv = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `traces-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="h-screen bg-black text-white overflow-auto">
      <div className="max-w-7xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-bold">Traces Analytics</h1>
          <Button onClick={handleExportCSV} variant="outline" disabled={traces.length === 0}>
            Export CSV
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Filters */}
        <TraceFilters
          instances={instances}
          selectedInstance={selectedInstance}
          startDate={startDate}
          endDate={endDate}
          status={status}
          messageType={messageType}
          onInstanceChange={setSelectedInstance}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onStatusChange={setStatus}
          onMessageTypeChange={setMessageType}
          onRefresh={handleRefresh}
          loading={loading}
        />

        {/* Analytics Cards */}
        {analytics && (
          <AnalyticsCards
            totalMessages={analytics.total_messages}
            successRate={analytics.success_rate}
            averageDuration={analytics.average_duration}
            failedCount={analytics.failed_count}
          />
        )}

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Messages Over Time */}
          {analytics && (
            <MessagesOverTimeChart data={analytics.messages_over_time || []} />
          )}

          {/* Success vs Failed */}
          {analytics && <SuccessRateChart data={analytics.success_vs_failed || []} />}

          {/* Message Types */}
          {analytics && <MessageTypesChart data={analytics.message_types || []} />}

          {/* Top Contacts */}
          {analytics && analytics.top_contacts && analytics.top_contacts.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Most Active Contacts</h3>
              <div className="space-y-2">
                {analytics.top_contacts.slice(0, 10).map((contact, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <span className="text-zinc-300 font-mono text-sm">{contact.phone}</span>
                    <span className="text-zinc-400 text-sm">{contact.count} messages</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Traces Table */}
        <div>
          <h2 className="text-2xl font-semibold mb-4">Recent Traces</h2>
          <TracesTable
            traces={traces}
            totalCount={totalCount}
            page={page}
            pageSize={pageSize}
            onPageChange={handlePageChange}
            onTraceClick={handleTraceClick}
            loading={loading}
          />
        </div>

        {/* Trace Details Dialog */}
        <TraceDetailsDialog
          trace={selectedTrace}
          open={!!selectedTrace}
          onClose={() => setSelectedTrace(null)}
        />
      </div>
    </div>
  )
}
