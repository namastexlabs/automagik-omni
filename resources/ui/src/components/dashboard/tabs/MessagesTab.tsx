import { useQuery } from '@tanstack/react-query';
import { api, TraceAnalytics, Trace, cn } from '@/lib';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { MessageTypesChart } from '../charts/MessageTypesChart';
import { useTimeRange } from '../TimeRangeSelector';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';

function StatusBadge({ status }: { status: Trace['status'] }) {
  const variants: Record<string, { className: string; label: string }> = {
    completed: { className: 'bg-success/10 text-success border-success/20', label: 'Completed' },
    processing: { className: 'bg-warning/10 text-warning border-warning/20', label: 'Processing' },
    failed: { className: 'bg-destructive/10 text-destructive border-destructive/20', label: 'Failed' },
    access_denied: { className: 'bg-muted text-muted-foreground border-border', label: 'Denied' },
    received: { className: 'bg-info/10 text-info border-info/20', label: 'Received' },
  };

  const variant = variants[status] || variants.received;

  return (
    <Badge variant="outline" className={cn('text-xs', variant.className)}>
      {variant.label}
    </Badge>
  );
}

function TracesTable({ traces, isLoading }: { traces: Trace[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No messages in selected period
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-3 px-2 font-medium text-muted-foreground">Time</th>
            <th className="text-left py-3 px-2 font-medium text-muted-foreground">Sender</th>
            <th className="text-left py-3 px-2 font-medium text-muted-foreground">Type</th>
            <th className="text-left py-3 px-2 font-medium text-muted-foreground">Status</th>
            <th className="text-right py-3 px-2 font-medium text-muted-foreground">Duration</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((trace) => (
            <tr key={trace.trace_id} className="border-b hover:bg-muted/50">
              <td className="py-3 px-2 text-muted-foreground">
                {trace.received_at
                  ? formatDistanceToNow(new Date(trace.received_at), { addSuffix: true })
                  : '-'}
              </td>
              <td className="py-3 px-2">
                <div className="font-medium">{trace.sender_name || 'Unknown'}</div>
                <div className="text-xs text-muted-foreground">
                  {trace.sender_phone?.slice(-10) || '-'}
                </div>
              </td>
              <td className="py-3 px-2">
                <Badge variant="secondary" className="text-xs">
                  {trace.message_type_display || trace.message_type || 'Unknown'}
                </Badge>
              </td>
              <td className="py-3 px-2">
                <StatusBadge status={trace.status} />
              </td>
              <td className="py-3 px-2 text-right text-muted-foreground">
                {trace.total_processing_time_ms
                  ? `${trace.total_processing_time_ms}ms`
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MessagesTab() {
  const { dateRange } = useTimeRange();

  const { data: analytics, isLoading: analyticsLoading } = useQuery<TraceAnalytics>({
    queryKey: ['traceAnalytics', dateRange],
    queryFn: () => api.traces.getAnalytics({
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
    }),
    refetchInterval: 30000,
  });

  const { data: traces, isLoading: tracesLoading } = useQuery<Trace[]>({
    queryKey: ['traces', dateRange],
    queryFn: () => api.traces.list({
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
      limit: 50,
    }),
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-6">
      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Messages by Type</CardTitle>
          </CardHeader>
          <CardContent>
            {analyticsLoading ? (
              <Skeleton className="h-[200px] w-full" />
            ) : (
              <MessageTypesChart data={analytics?.message_types || {}} horizontal={false} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Error Stages</CardTitle>
          </CardHeader>
          <CardContent>
            {analyticsLoading ? (
              <Skeleton className="h-[200px] w-full" />
            ) : Object.keys(analytics?.error_stages || {}).length > 0 ? (
              <MessageTypesChart data={analytics?.error_stages || {}} />
            ) : (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground">
                No errors in selected period
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Traces Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Messages</CardTitle>
        </CardHeader>
        <CardContent>
          <TracesTable traces={traces || []} isLoading={tracesLoading} />
        </CardContent>
      </Card>
    </div>
  );
}
