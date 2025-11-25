import { useQuery } from '@tanstack/react-query';
import { api, TraceAnalytics, HealthResponse } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useTimeRange } from '../TimeRangeSelector';
import { Server, Cpu, Database, Clock, HardDrive, Activity, MessageSquare, Users, MessagesSquare, Phone, Settings, Check, X, Smartphone } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SystemMetricProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subValue?: string;
  status?: 'up' | 'down' | 'degraded';
}

function SystemMetric({ icon, label, value, subValue, status }: SystemMetricProps) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
      <div className={cn(
        'p-2 rounded-md',
        status === 'up' ? 'bg-success/10 text-success' :
        status === 'down' ? 'bg-destructive/10 text-destructive' :
        'bg-primary/10 text-primary'
      )}>
        {icon}
      </div>
      <div>
        <div className="text-sm text-muted-foreground">{label}</div>
        <div className="font-medium">{value}</div>
        {subValue && <div className="text-xs text-muted-foreground">{subValue}</div>}
      </div>
    </div>
  );
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours < 24) return `${hours}h ${minutes}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

// Evolution instance detail type
interface EvolutionInstanceDetail {
  name: string;
  connectionStatus: string;
  profileName?: string;
  profilePicUrl?: string;
  ownerJid?: string;
  integration?: string;
  createdAt?: string;
  updatedAt?: string;
  counts: {
    messages: number;
    contacts: number;
    chats: number;
  };
  settings?: {
    rejectCall?: boolean;
    groupsIgnore?: boolean;
    alwaysOnline?: boolean;
    readMessages?: boolean;
    readStatus?: boolean;
    syncFullHistory?: boolean;
  };
  integrations?: {
    chatwoot?: boolean;
    rabbitmq?: boolean;
    websocket?: boolean;
  };
}

interface EvolutionInstanceCardProps {
  instance: EvolutionInstanceDetail;
}

function EvolutionInstanceCard({ instance }: EvolutionInstanceCardProps) {
  const isConnected = instance.connectionStatus === 'open';

  // Format phone number from ownerJid (e.g., "553497400888@s.whatsapp.net" -> "+55 34 9740-0888")
  const formatPhone = (jid?: string) => {
    if (!jid) return null;
    const phone = jid.split('@')[0];
    if (phone.length >= 12) {
      return `+${phone.slice(0, 2)} ${phone.slice(2, 4)} ${phone.slice(4, 9)}-${phone.slice(9)}`;
    }
    return phone;
  };

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start gap-4">
          {/* Profile Picture */}
          <Avatar className="h-12 w-12">
            {instance.profilePicUrl ? (
              <AvatarImage src={instance.profilePicUrl} alt={instance.profileName || instance.name} />
            ) : null}
            <AvatarFallback className="bg-primary/10 text-primary">
              {(instance.profileName || instance.name).slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>

          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold truncate">{instance.profileName || instance.name}</span>
              <Badge variant={isConnected ? 'default' : 'destructive'} className="text-xs">
                {isConnected ? 'Connected' : instance.connectionStatus}
              </Badge>
            </div>

            {/* Phone Number */}
            {instance.ownerJid && (
              <div className="flex items-center gap-1 text-sm text-muted-foreground mb-2">
                <Phone className="h-3 w-3" />
                <span>{formatPhone(instance.ownerJid)}</span>
              </div>
            )}

            {/* Stats Row */}
            <div className="flex items-center gap-4 text-sm mb-3">
              <div className="flex items-center gap-1">
                <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
                <span>{instance.counts.messages.toLocaleString()}</span>
              </div>
              <div className="flex items-center gap-1">
                <Users className="h-3.5 w-3.5 text-muted-foreground" />
                <span>{instance.counts.contacts}</span>
              </div>
              <div className="flex items-center gap-1">
                <MessagesSquare className="h-3.5 w-3.5 text-muted-foreground" />
                <span>{instance.counts.chats}</span>
              </div>
            </div>

            {/* Settings Pills */}
            {instance.settings && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                <SettingPill label="Auto-read" enabled={instance.settings.readMessages} />
                <SettingPill label="Always online" enabled={instance.settings.alwaysOnline} />
                <SettingPill label="Reject calls" enabled={instance.settings.rejectCall} />
                <SettingPill label="Full sync" enabled={instance.settings.syncFullHistory} />
              </div>
            )}

            {/* Integration badges */}
            {instance.integration && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Smartphone className="h-3 w-3" />
                <span>{instance.integration}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SettingPill({ label, enabled }: { label: string; enabled?: boolean }) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs',
      enabled ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'
    )}>
      {enabled ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
      {label}
    </span>
  );
}

export function SystemTab() {
  const { dateRange } = useTimeRange();

  const { data: analytics, isLoading: analyticsLoading } = useQuery<TraceAnalytics>({
    queryKey: ['traceAnalytics', dateRange],
    queryFn: () => api.traces.getAnalytics({
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
    }),
    refetchInterval: 30000,
  });

  const { data: health, isLoading: healthLoading } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 10000, // More frequent for system metrics
  });

  const gatewayDetails = health?.services?.gateway?.details as {
    memory?: { heapUsed: number; heapTotal: number; rss: number };
    uptime?: number;
    nodeVersion?: string;
    pid?: number;
  } | undefined;

  const pythonDetails = health?.services?.python?.details as {
    services?: {
      api?: {
        uptime?: number;
        memory_mb?: number;
      };
      database?: {
        status?: string;
        pool_size?: number;
        checked_out?: number;
        checked_in?: number;
        overflow?: number;
      };
    };
  } | undefined;

  const apiInfo = pythonDetails?.services?.api;
  const dbInfo = pythonDetails?.services?.database;

  // Evolution instance details
  const evolutionDetails = health?.services?.evolution?.details as {
    instances?: { total: number; connected: number; disconnected: number };
    totals?: { messages: number; contacts: number; chats: number };
    instanceDetails?: EvolutionInstanceDetail[];
  } | undefined;

  const isLoading = analyticsLoading || healthLoading;

  return (
    <div className="space-y-6">
      {/* Gateway & Python API Row */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Server className="h-4 w-4" />
              Gateway
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : (
              <div className="grid gap-3">
                <SystemMetric
                  icon={<HardDrive className="h-4 w-4" />}
                  label="Heap Memory"
                  value={`${gatewayDetails?.memory?.heapUsed || 0} / ${gatewayDetails?.memory?.heapTotal || 0} MB`}
                  subValue={`RSS: ${gatewayDetails?.memory?.rss || 0} MB`}
                  status={health?.services?.gateway?.status}
                />
                <SystemMetric
                  icon={<Clock className="h-4 w-4" />}
                  label="Uptime"
                  value={gatewayDetails?.uptime ? formatUptime(gatewayDetails.uptime) : 'N/A'}
                  subValue={`Node ${gatewayDetails?.nodeVersion || 'N/A'} | PID ${gatewayDetails?.pid || 'N/A'}`}
                  status={health?.services?.gateway?.status}
                />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Python API
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : (
              <div className="grid gap-3">
                <SystemMetric
                  icon={<HardDrive className="h-4 w-4" />}
                  label="Memory Usage"
                  value={`${apiInfo?.memory_mb || 0} MB`}
                  status={health?.services?.python?.status}
                />
                <SystemMetric
                  icon={<Clock className="h-4 w-4" />}
                  label="Uptime"
                  value={apiInfo?.uptime ? formatUptime(apiInfo.uptime) : 'N/A'}
                  subValue={`Latency: ${health?.services?.python?.latency || 0}ms`}
                  status={health?.services?.python?.status}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Database Pool Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Database className="h-4 w-4" />
            Database Pool
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <div className="grid gap-4 md:grid-cols-4">
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold">{dbInfo?.pool_size || 0}</div>
                <div className="text-sm text-muted-foreground">Pool Size</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold">{dbInfo?.checked_out || 0}</div>
                <div className="text-sm text-muted-foreground">In Use</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold">{dbInfo?.checked_in || 0}</div>
                <div className="text-sm text-muted-foreground">Available</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className={cn(
                  'text-2xl font-bold',
                  dbInfo?.status === 'connected' ? 'text-success' : 'text-destructive'
                )}>
                  {dbInfo?.status || 'Unknown'}
                </div>
                <div className="text-sm text-muted-foreground">Status</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Processing Performance */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Processing Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          {analyticsLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <div className="grid gap-4 md:grid-cols-4">
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold">
                  {analytics?.avg_processing_time_ms
                    ? `${Math.round(analytics.avg_processing_time_ms)}ms`
                    : 'N/A'}
                </div>
                <div className="text-sm text-muted-foreground">Avg Total Time</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold">
                  {analytics?.avg_agent_time_ms
                    ? `${Math.round(analytics.avg_agent_time_ms)}ms`
                    : 'N/A'}
                </div>
                <div className="text-sm text-muted-foreground">Avg Agent Time</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold text-success">
                  {analytics?.successful_messages || 0}
                </div>
                <div className="text-sm text-muted-foreground">Completed</div>
              </div>
              <div className="text-center p-4 rounded-lg bg-muted/50">
                <div className="text-2xl font-bold text-warning">
                  {(analytics?.total_messages || 0) - (analytics?.successful_messages || 0) - (analytics?.failed_messages || 0)}
                </div>
                <div className="text-sm text-muted-foreground">Processing</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Evolution Instances */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Smartphone className="h-4 w-4" />
            Evolution WhatsApp Instances
            {evolutionDetails?.instances && (
              <Badge variant="outline" className="ml-2">
                {evolutionDetails.instances.connected}/{evolutionDetails.instances.total} connected
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {healthLoading ? (
            <div className="grid gap-4 md:grid-cols-2">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : evolutionDetails?.instanceDetails && evolutionDetails.instanceDetails.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {evolutionDetails.instanceDetails.map((instance) => (
                <EvolutionInstanceCard key={instance.name} instance={instance} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Smartphone className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No Evolution instances found</p>
              <p className="text-sm">Evolution API may be unavailable</p>
            </div>
          )}

          {/* Evolution Totals Summary */}
          {evolutionDetails?.totals && (
            <div className="mt-4 pt-4 border-t">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                  <MessageSquare className="h-5 w-5 text-primary" />
                  <div>
                    <div className="font-semibold">{evolutionDetails.totals.messages.toLocaleString()}</div>
                    <div className="text-xs text-muted-foreground">Total Messages</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                  <Users className="h-5 w-5 text-primary" />
                  <div>
                    <div className="font-semibold">{evolutionDetails.totals.contacts.toLocaleString()}</div>
                    <div className="text-xs text-muted-foreground">Total Contacts</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                  <MessagesSquare className="h-5 w-5 text-primary" />
                  <div>
                    <div className="font-semibold">{evolutionDetails.totals.chats.toLocaleString()}</div>
                    <div className="text-xs text-muted-foreground">Total Chats</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
