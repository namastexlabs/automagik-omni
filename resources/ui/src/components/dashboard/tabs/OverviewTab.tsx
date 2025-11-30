import { useQuery } from '@tanstack/react-query';
import { api, TraceAnalytics, HealthResponse, cn } from '@/lib';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBreakdownChart } from '../charts/StatusBreakdownChart';
import { MessageTypesChart } from '../charts/MessageTypesChart';
import { useTimeRange } from '../TimeRangeSelector';
import { MessageSquare, CheckCircle, Clock, Server, Circle } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  isLoading?: boolean;
}

function MetricCard({ title, value, subtitle, icon, isLoading }: MetricCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {icon}
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-24" />
          {subtitle && <Skeleton className="h-4 w-32 mt-1" />}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

interface InstanceCardProps {
  name: string;
  status: 'connected' | 'disconnected';
  messages: number;
  contacts: number;
  chats: number;
}

function InstanceCard({ name, status, messages, contacts, chats }: InstanceCardProps) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center gap-3">
          <Circle
            className={cn(
              'h-3 w-3 fill-current',
              status === 'connected' ? 'text-success' : 'text-destructive'
            )}
          />
          <div className="flex-1">
            <div className="font-medium">{name}</div>
            <div className="text-sm text-muted-foreground">
              {messages.toLocaleString()} msgs | {contacts} contacts | {chats} chats
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function OverviewTab() {
  const { dateRange } = useTimeRange();

  const { data: analytics, isLoading: analyticsLoading, error: analyticsError } = useQuery<TraceAnalytics>({
    queryKey: ['traceAnalytics', dateRange],
    queryFn: () => api.traces.getAnalytics({
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
    }),
    refetchInterval: 30000,
  });

  const { data: health, isLoading: healthLoading, error: healthError } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000,
  });

  // Log errors for debugging
  if (analyticsError) {
    console.error('[OverviewTab] Analytics error:', analyticsError);
  }
  if (healthError) {
    console.error('[OverviewTab] Health error:', healthError);
  }

  const evolutionDetails = health?.services?.evolution?.details as {
    instances?: { total: number; connected: number };
    totals?: { messages: number; contacts: number; chats: number };
  } | undefined;

  // Calculate status breakdown from analytics
  const statusData = {
    completed: analytics?.successful_messages || 0,
    processing: (analytics?.total_messages || 0) - (analytics?.successful_messages || 0) - (analytics?.failed_messages || 0),
    failed: analytics?.failed_messages || 0,
  };

  return (
    <div className="space-y-6">
      {/* Error Banner */}
      {analyticsError && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-destructive">
          <strong>Analytics Error:</strong> {analyticsError instanceof Error ? analyticsError.message : 'Failed to load analytics'}
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Messages"
          value={analytics?.total_messages?.toLocaleString() || '0'}
          subtitle="In selected period"
          icon={<MessageSquare className="h-4 w-4 text-muted-foreground" />}
          isLoading={analyticsLoading}
        />
        <MetricCard
          title="Success Rate"
          value={`${analytics?.success_rate?.toFixed(1) || '0'}%`}
          subtitle={`${analytics?.successful_messages || 0} successful`}
          icon={<CheckCircle className="h-4 w-4 text-muted-foreground" />}
          isLoading={analyticsLoading}
        />
        <MetricCard
          title="Avg Processing"
          value={analytics?.avg_processing_time_ms ? `${Math.round(analytics.avg_processing_time_ms)}ms` : 'N/A'}
          subtitle={analytics?.avg_agent_time_ms ? `Agent: ${Math.round(analytics.avg_agent_time_ms)}ms` : undefined}
          icon={<Clock className="h-4 w-4 text-muted-foreground" />}
          isLoading={analyticsLoading}
        />
        <MetricCard
          title="Active Instances"
          value={`${evolutionDetails?.instances?.connected || 0}/${evolutionDetails?.instances?.total || 0}`}
          subtitle="Connected instances"
          icon={<Server className="h-4 w-4 text-muted-foreground" />}
          isLoading={healthLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {analyticsLoading ? (
              <Skeleton className="h-[200px] w-full" />
            ) : (
              <StatusBreakdownChart data={statusData} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Message Types</CardTitle>
          </CardHeader>
          <CardContent>
            {analyticsLoading ? (
              <Skeleton className="h-[200px] w-full" />
            ) : (
              <MessageTypesChart data={analytics?.message_types || {}} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Instance Cards */}
      <div>
        <h3 className="text-lg font-medium mb-4">Evolution Instances</h3>
        {healthLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : evolutionDetails?.totals ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* For now we have one instance from health data */}
            <InstanceCard
              name="genie"
              status={evolutionDetails.instances?.connected ? 'connected' : 'disconnected'}
              messages={evolutionDetails.totals.messages}
              contacts={evolutionDetails.totals.contacts}
              chats={evolutionDetails.totals.chats}
            />
          </div>
        ) : (
          <p className="text-muted-foreground">No instance data available</p>
        )}
      </div>
    </div>
  );
}
