import { useQuery } from '@tanstack/react-query';
import { api, TraceAnalytics, HealthResponse, cn, InstanceConfig } from '@/lib';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useTimeRange } from '../TimeRangeSelector';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { ChartContainer, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { Circle, MessageSquare, Users, MessagesSquare, Smartphone, Bot } from 'lucide-react';
import { WhatsAppIcon, DiscordIcon } from '@/components/icons/BrandIcons';

const chartConfig = {
  messages: {
    label: 'Messages',
    color: 'hsl(var(--chart-1))',
  },
} satisfies ChartConfig;

interface InstanceDetailCardProps {
  name: string;
  channelType: 'whatsapp' | 'discord' | 'slack';
  status: 'connected' | 'disconnected' | 'unknown';
  version?: string;
  whatsappVersion?: string;
  messages: number;
  contacts: number;
  chats: number;
  tracedMessages?: number;
  successRate?: number;
}

function InstanceDetailCard({
  name,
  channelType,
  status,
  version,
  whatsappVersion,
  messages,
  contacts,
  chats,
  tracedMessages,
  successRate,
}: InstanceDetailCardProps) {
  const getChannelIcon = () => {
    switch (channelType) {
      case 'discord':
        return <DiscordIcon className="h-4 w-4 text-[#5865F2]" />;
      case 'whatsapp':
      default:
        return <WhatsAppIcon className="h-4 w-4 text-[#25D366]" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'text-success';
      case 'disconnected':
        return 'text-destructive';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          {getChannelIcon()}
          <Circle className={cn('h-3 w-3 fill-current', getStatusColor())} />
          <CardTitle className="text-base">{name}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="font-medium">{messages.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground">Total Messages</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="font-medium">{contacts}</div>
              <div className="text-xs text-muted-foreground">Contacts</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <MessagesSquare className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="font-medium">{chats}</div>
              <div className="text-xs text-muted-foreground">Chats</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {channelType === 'discord' ? (
              <>
                <Bot className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium">Discord</div>
                  <div className="text-xs text-muted-foreground">Bot</div>
                </div>
              </>
            ) : (
              <>
                <Smartphone className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="font-medium truncate max-w-[100px]" title={whatsappVersion}>
                    {whatsappVersion ? whatsappVersion.split('.').slice(0, 2).join('.') : 'N/A'}
                  </div>
                  <div className="text-xs text-muted-foreground">WhatsApp</div>
                </div>
              </>
            )}
          </div>
        </div>

        {(tracedMessages !== undefined || successRate !== undefined) && (
          <div className="pt-2 border-t">
            <div className="grid grid-cols-2 gap-4 text-sm">
              {tracedMessages !== undefined && (
                <div>
                  <div className="font-medium">{tracedMessages.toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">Traced</div>
                </div>
              )}
              {successRate !== undefined && (
                <div>
                  <div className="font-medium">{successRate.toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">Success Rate</div>
                </div>
              )}
            </div>
          </div>
        )}

        {version && channelType === 'whatsapp' && (
          <div className="text-xs text-muted-foreground">WhatsApp Web v{version}</div>
        )}
      </CardContent>
    </Card>
  );
}

// Helper to get connection status from InstanceConfig
function getInstanceStatus(instance: InstanceConfig): 'connected' | 'disconnected' | 'unknown' {
  // Check connection_status field first
  if (instance.connection_status) {
    const status = instance.connection_status.toLowerCase();
    if (status === 'connected' || status === 'open') return 'connected';
    if (status === 'disconnected' || status === 'close' || status === 'closed') return 'disconnected';
  }

  // For Discord
  if (instance.channel_type === 'discord') {
    return instance.has_discord_bot_token ? 'unknown' : 'disconnected';
  }

  // For WhatsApp - check whatsapp_web_status
  const state =
    instance.whatsapp_web_status?.state ||
    instance.whatsapp_web_status?.instance?.state ||
    instance.evolution_status?.state;

  if (!state) return 'unknown';

  const normalizedState = state.toLowerCase();
  if (normalizedState === 'open' || normalizedState === 'connected') return 'connected';
  if (normalizedState === 'close' || normalizedState === 'closed' || normalizedState === 'disconnected')
    return 'disconnected';

  return 'unknown';
}

export function InstancesTab() {
  const { dateRange } = useTimeRange();

  const { data: analytics, isLoading: analyticsLoading } = useQuery<TraceAnalytics>({
    queryKey: ['traceAnalytics', dateRange],
    queryFn: () =>
      api.traces.getAnalytics({
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
      }),
    refetchInterval: 30000,
  });

  const { data: health, isLoading: healthLoading } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000,
  });

  // Fetch ALL instances (WhatsApp + Discord)
  const { data: instances, isLoading: instancesLoading } = useQuery<InstanceConfig[]>({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_live_status: true }),
    refetchInterval: 30000,
  });

  interface EvolutionInstanceDetail {
    name: string;
    connectionStatus: 'open' | 'close' | 'connecting' | string;
    profileName?: string;
    profilePicUrl?: string;
    ownerJid?: string;
    integration?: string;
    counts: {
      messages: number;
      contacts: number;
      chats: number;
    };
  }

  const evolutionDetails = health?.services?.evolution?.details as
    | {
        version?: string;
        whatsappWebVersion?: string;
        instances?: { total: number; connected: number };
        totals?: { messages: number; contacts: number; chats: number };
        instanceDetails?: EvolutionInstanceDetail[];
      }
    | undefined;

  // Build a map of Evolution instance details for WhatsApp counts
  const evolutionInstanceMap = new Map<string, EvolutionInstanceDetail>();
  evolutionDetails?.instanceDetails?.forEach((detail) => {
    evolutionInstanceMap.set(detail.name, detail);
  });

  // Prepare chart data from analytics.instances
  const instanceChartData = Object.entries(analytics?.instances || {}).map(([name, count]) => ({
    name,
    messages: count,
    fill: 'hsl(var(--chart-1))',
  }));

  const isLoading = analyticsLoading || healthLoading || instancesLoading;

  return (
    <div className="space-y-6">
      {/* Messages by Instance Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Messages by Instance</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[150px] w-full" />
          ) : instanceChartData.length > 0 ? (
            <ChartContainer config={chartConfig} className="h-[150px]">
              <BarChart data={instanceChartData} layout="vertical" margin={{ left: 20, right: 40 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={80}
                  tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<ChartTooltipContent />} />
                <Bar dataKey="messages" radius={[0, 4, 4, 0]} barSize={24}>
                  {instanceChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          ) : (
            <div className="flex items-center justify-center h-[150px] text-muted-foreground">
              No instance data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Instance Detail Cards - ALL instances (WhatsApp + Discord) */}
      <div>
        <h3 className="text-lg font-medium mb-4">Instance Details</h3>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-48" />
          </div>
        ) : instances && instances.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {instances.map((instance) => {
              const evoDetail = evolutionInstanceMap.get(instance.name);
              return (
                <InstanceDetailCard
                  key={instance.name}
                  name={instance.name}
                  channelType={instance.channel_type || 'whatsapp'}
                  status={getInstanceStatus(instance)}
                  version={evolutionDetails?.version}
                  whatsappVersion={evolutionDetails?.whatsappWebVersion}
                  messages={evoDetail?.counts?.messages ?? 0}
                  contacts={evoDetail?.counts?.contacts ?? 0}
                  chats={evoDetail?.counts?.chats ?? 0}
                  tracedMessages={analytics?.instances?.[instance.name]}
                  successRate={analytics?.success_rate}
                />
              );
            })}
          </div>
        ) : (
          <p className="text-muted-foreground">No instance data available</p>
        )}
      </div>
    </div>
  );
}
