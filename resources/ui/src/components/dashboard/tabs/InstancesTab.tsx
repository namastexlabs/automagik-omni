import { useQuery } from '@tanstack/react-query';
import { api, TraceAnalytics, HealthResponse, cn } from '@/lib';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useTimeRange } from '../TimeRangeSelector';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { ChartContainer, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { Circle, MessageSquare, Users, MessagesSquare, Smartphone } from 'lucide-react';

const chartConfig = {
  messages: {
    label: 'Messages',
    color: 'hsl(var(--chart-1))',
  },
} satisfies ChartConfig;

interface InstanceDetailCardProps {
  name: string;
  status: 'connected' | 'disconnected';
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
  status,
  version,
  whatsappVersion,
  messages,
  contacts,
  chats,
  tracedMessages,
  successRate,
}: InstanceDetailCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <Circle
            className={cn('h-3 w-3 fill-current', status === 'connected' ? 'text-success' : 'text-destructive')}
          />
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
            <Smartphone className="h-4 w-4 text-muted-foreground" />
            <div>
              <div className="font-medium truncate max-w-[100px]" title={whatsappVersion}>
                {whatsappVersion ? whatsappVersion.split('.').slice(0, 2).join('.') : 'N/A'}
              </div>
              <div className="text-xs text-muted-foreground">WhatsApp</div>
            </div>
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

        {version && <div className="text-xs text-muted-foreground">WhatsApp Web v{version}</div>}
      </CardContent>
    </Card>
  );
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

  const evolutionDetails = health?.services?.evolution?.details as
    | {
        version?: string;
        whatsappWebVersion?: string;
        instances?: { total: number; connected: number };
        totals?: { messages: number; contacts: number; chats: number };
      }
    | undefined;

  // Prepare chart data from analytics.instances
  const instanceChartData = Object.entries(analytics?.instances || {}).map(([name, count]) => ({
    name,
    messages: count,
    fill: 'hsl(var(--chart-1))',
  }));

  const isLoading = analyticsLoading || healthLoading;

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

      {/* Instance Detail Cards */}
      <div>
        <h3 className="text-lg font-medium mb-4">Instance Details</h3>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-48" />
          </div>
        ) : evolutionDetails?.totals ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <InstanceDetailCard
              name="genie"
              status={evolutionDetails.instances?.connected ? 'connected' : 'disconnected'}
              version={evolutionDetails.version}
              whatsappVersion={evolutionDetails.whatsappWebVersion}
              messages={evolutionDetails.totals.messages}
              contacts={evolutionDetails.totals.contacts}
              chats={evolutionDetails.totals.chats}
              tracedMessages={analytics?.instances?.['genie']}
              successRate={analytics?.success_rate}
            />
          </div>
        ) : (
          <p className="text-muted-foreground">No instance data available</p>
        )}
      </div>
    </div>
  );
}
