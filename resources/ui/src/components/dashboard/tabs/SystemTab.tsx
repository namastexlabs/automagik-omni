import { useQuery } from '@tanstack/react-query';
import { api, TraceAnalytics, HealthResponse, ServerStats, cn } from '@/lib';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useTimeRange } from '../TimeRangeSelector';
import {
  Server,
  Cpu,
  Database,
  Clock,
  HardDrive,
  Activity,
  Smartphone,
  Gauge,
  Layers,
  CircleDot,
  CheckCircle,
  AlertCircle,
  Wifi,
  MemoryStick,
  MonitorCog,
} from 'lucide-react';

function formatUptime(seconds: number): string {
  if (!seconds || seconds < 0) return 'N/A';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours < 24) return `${hours}h ${minutes}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

function formatBytes(mb: number): string {
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)} GB`;
  }
  return `${mb.toFixed(1)} MB`;
}

interface ServiceCardProps {
  title: string;
  icon: React.ReactNode;
  status: 'up' | 'down' | 'degraded' | undefined;
  latency?: number;
  children: React.ReactNode;
  badge?: React.ReactNode;
}

function ServiceCard({ title, icon, status, latency, children, badge }: ServiceCardProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            {icon}
            {title}
          </CardTitle>
          <div className="flex items-center gap-2">
            {badge}
            <Badge
              variant={status === 'up' ? 'default' : status === 'degraded' ? 'secondary' : 'destructive'}
              className={cn('text-xs', status === 'up' && 'bg-success text-success-foreground')}
            >
              {status === 'up' ? 'Healthy' : status === 'degraded' ? 'Degraded' : 'Down'}
            </Badge>
          </div>
        </div>
        {latency !== undefined && <CardDescription className="text-xs">Response time: {latency}ms</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

interface MetricRowProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subValue?: string;
  progress?: number;
  progressColor?: string;
}

function MetricRow({ icon, label, value, subValue, progress, progressColor }: MetricRowProps) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
      <div className="p-2 rounded-md bg-primary/10 text-primary">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{label}</span>
          <span className="font-medium">{value}</span>
        </div>
        {subValue && <div className="text-xs text-muted-foreground mt-0.5">{subValue}</div>}
        {progress !== undefined && <Progress value={progress} className={cn('h-1.5 mt-2', progressColor)} />}
      </div>
    </div>
  );
}

interface ServerOverviewCardProps {
  server?: ServerStats;
  isLoading: boolean;
}

function ServerOverviewCard({ server, isLoading }: ServerOverviewCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <MonitorCog className="h-4 w-4" />
            Server Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!server) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <MonitorCog className="h-4 w-4" />
            Server Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-4">Server stats unavailable</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <MonitorCog className="h-4 w-4" />
            Server Overview
          </CardTitle>
          <Badge variant="outline" className="text-xs">
            {server.hostname} • {server.platform}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {/* RAM */}
          <div className="p-4 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <MemoryStick className="h-4 w-4" />
              <span className="text-xs font-medium">RAM</span>
            </div>
            <div className="text-2xl font-bold">{server.memory.usedPercent}%</div>
            <div className="text-xs text-muted-foreground mt-1">
              {server.memory.used.toFixed(1)} / {server.memory.total.toFixed(1)} GB
            </div>
            <Progress
              value={server.memory.usedPercent}
              className={cn('h-1.5 mt-2', server.memory.usedPercent > 90 ? '[&>div]:bg-destructive' : '')}
            />
          </div>

          {/* CPU */}
          <div className="p-4 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Cpu className="h-4 w-4" />
              <span className="text-xs font-medium">CPU</span>
            </div>
            <div className="text-2xl font-bold">{server.cpu.usagePercent}%</div>
            <div className="text-xs text-muted-foreground mt-1">{server.cpu.cores} cores</div>
            <Progress
              value={server.cpu.usagePercent}
              className={cn('h-1.5 mt-2', server.cpu.usagePercent > 90 ? '[&>div]:bg-destructive' : '')}
            />
          </div>

          {/* Disk */}
          <div className="p-4 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <HardDrive className="h-4 w-4" />
              <span className="text-xs font-medium">Disk ({server.disk.mountPoint})</span>
            </div>
            <div className="text-2xl font-bold">{server.disk.usedPercent}%</div>
            <div className="text-xs text-muted-foreground mt-1">
              {server.disk.used.toFixed(1)} / {server.disk.total.toFixed(1)} GB
            </div>
            <Progress
              value={server.disk.usedPercent}
              className={cn('h-1.5 mt-2', server.disk.usedPercent > 90 ? '[&>div]:bg-destructive' : '')}
            />
          </div>

          {/* Load Average */}
          <div className="p-4 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Gauge className="h-4 w-4" />
              <span className="text-xs font-medium">Load Average</span>
            </div>
            <div className="text-2xl font-bold">{server.loadAverage[0].toFixed(2)}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {server.loadAverage[1].toFixed(2)} / {server.loadAverage[2].toFixed(2)}
            </div>
            <div className="text-xs text-muted-foreground">1m / 5m / 15m</div>
          </div>

          {/* System Uptime */}
          <div className="p-4 rounded-lg bg-muted/30">
            <div className="flex items-center gap-2 text-muted-foreground mb-2">
              <Clock className="h-4 w-4" />
              <span className="text-xs font-medium">System Uptime</span>
            </div>
            <div className="text-2xl font-bold">{formatUptime(server.uptime)}</div>
            <div className="text-xs text-muted-foreground mt-1">Since boot</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function SystemTab() {
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
    refetchInterval: 5000, // More frequent for system metrics
  });

  const gatewayDetails = health?.services?.gateway?.details as
    | {
        memory?: { heapUsed: number; heapTotal: number; rss: number };
        uptime?: number;
        nodeVersion?: string;
        pid?: number;
        cpu?: number;
      }
    | undefined;

  const pythonDetails = health?.services?.python?.details as
    | {
        services?: {
          api?: {
            uptime?: number;
            memory_mb?: number;
            cpu_percent?: number;
            pid?: number;
          };
          database?: {
            status?: string;
            pool_size?: number;
            checked_out?: number;
            checked_in?: number;
            overflow?: number;
          };
        };
      }
    | undefined;

  const evolutionDetails = health?.services?.evolution?.details as
    | {
        version?: string;
        whatsappWebVersion?: string;
        instances?: { total: number; connected: number; disconnected: number };
        process?: {
          pid?: number;
          memory_mb?: number;
          cpu_percent?: number;
          uptime?: number;
        };
      }
    | undefined;

  const apiInfo = pythonDetails?.services?.api;
  const dbInfo = pythonDetails?.services?.database;
  const evolutionProcess = evolutionDetails?.process;

  const isLoading = healthLoading;

  // Calculate memory usage percentages
  const gatewayMemPercent = gatewayDetails?.memory
    ? Math.round((gatewayDetails.memory.heapUsed / gatewayDetails.memory.heapTotal) * 100)
    : 0;

  // Database pool usage
  const poolTotal = dbInfo?.pool_size || 5;
  const poolUsed = dbInfo?.checked_out || 0;
  const poolPercent = Math.round((poolUsed / poolTotal) * 100);

  return (
    <div className="space-y-6">
      {/* Server Overview - Full width */}
      <ServerOverviewCard server={health?.server} isLoading={isLoading} />

      {/* Services Row - 3 columns */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Gateway */}
        <ServiceCard
          title="Gateway"
          icon={<Server className="h-4 w-4" />}
          status={health?.services?.gateway?.status}
          latency={health?.services?.gateway?.latency}
        >
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ) : (
            <div className="space-y-3">
              <MetricRow
                icon={<HardDrive className="h-4 w-4" />}
                label="Memory"
                value={`${gatewayDetails?.memory?.heapUsed || 0} MB`}
                subValue={`Heap: ${gatewayDetails?.memory?.heapTotal || 0} MB • RSS: ${formatBytes(gatewayDetails?.memory?.rss || 0)}`}
                progress={gatewayMemPercent}
              />
              <MetricRow
                icon={<Cpu className="h-4 w-4" />}
                label="CPU"
                value={`${gatewayDetails?.cpu ?? 0}%`}
                subValue={`PID ${gatewayDetails?.pid || 'N/A'}`}
              />
              <MetricRow
                icon={<Clock className="h-4 w-4" />}
                label="Uptime"
                value={formatUptime(gatewayDetails?.uptime || 0)}
                subValue={`Node ${gatewayDetails?.nodeVersion || 'N/A'}`}
              />
            </div>
          )}
        </ServiceCard>

        {/* Python API */}
        <ServiceCard
          title="Python API"
          icon={<Cpu className="h-4 w-4" />}
          status={health?.services?.python?.status}
          latency={health?.services?.python?.latency}
        >
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ) : (
            <div className="space-y-3">
              <MetricRow
                icon={<HardDrive className="h-4 w-4" />}
                label="Memory"
                value={formatBytes(apiInfo?.memory_mb || 0)}
              />
              <MetricRow
                icon={<Cpu className="h-4 w-4" />}
                label="CPU"
                value={`${apiInfo?.cpu_percent ?? 0}%`}
                subValue={`PID ${apiInfo?.pid || 'N/A'}`}
              />
              <MetricRow
                icon={<Clock className="h-4 w-4" />}
                label="Uptime"
                value={formatUptime(apiInfo?.uptime || 0)}
              />
            </div>
          )}
        </ServiceCard>

        {/* WhatsApp Web API */}
        <ServiceCard
          title="WhatsApp Web API"
          icon={<Smartphone className="h-4 w-4" />}
          status={health?.services?.evolution?.status}
          latency={health?.services?.evolution?.latency}
          badge={
            evolutionDetails?.instances && (
              <Badge variant="outline" className="text-xs">
                <Wifi className="h-3 w-3 mr-1" />
                {evolutionDetails.instances.connected}/{evolutionDetails.instances.total}
              </Badge>
            )
          }
        >
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ) : evolutionProcess ? (
            <div className="space-y-3">
              <MetricRow
                icon={<HardDrive className="h-4 w-4" />}
                label="Memory"
                value={formatBytes(evolutionProcess.memory_mb || 0)}
              />
              <MetricRow
                icon={<Cpu className="h-4 w-4" />}
                label="CPU"
                value={`${evolutionProcess.cpu_percent ?? 0}%`}
                subValue={`PID ${evolutionProcess.pid || 'N/A'}`}
              />
              <MetricRow
                icon={<Clock className="h-4 w-4" />}
                label="Uptime"
                value={formatUptime(evolutionProcess.uptime || 0)}
                subValue={`v${evolutionDetails?.version || '?'}`}
              />
            </div>
          ) : (
            <div className="space-y-3">
              <MetricRow
                icon={<Activity className="h-4 w-4" />}
                label="Version"
                value={evolutionDetails?.version || 'Unknown'}
                subValue={`WhatsApp: ${evolutionDetails?.whatsappWebVersion || 'Unknown'}`}
              />
              <div className="p-3 rounded-lg bg-muted/30 text-center text-sm text-muted-foreground">
                Process stats unavailable
              </div>
            </div>
          )}
        </ServiceCard>
      </div>

      {/* Database Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Database className="h-4 w-4" />
              Database Connection Pool
            </CardTitle>
            <Badge
              variant={dbInfo?.status === 'connected' ? 'default' : 'destructive'}
              className={cn('text-xs', dbInfo?.status === 'connected' && 'bg-success text-success-foreground')}
            >
              {dbInfo?.status === 'connected' ? (
                <>
                  <CheckCircle className="h-3 w-3 mr-1" /> Connected
                </>
              ) : (
                <>
                  <AlertCircle className="h-3 w-3 mr-1" /> {dbInfo?.status || 'Unknown'}
                </>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <div className="space-y-4">
              {/* Pool visualization */}
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Pool Utilization</span>
                    <span className="font-medium">
                      {poolUsed} / {poolTotal} connections
                    </span>
                  </div>
                  <Progress value={poolPercent} className="h-3" />
                </div>
              </div>

              {/* Pool stats grid */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div className="p-3 rounded-lg bg-muted/30 text-center">
                  <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                    <Layers className="h-3.5 w-3.5" />
                    <span className="text-xs">Pool Size</span>
                  </div>
                  <div className="text-xl font-bold">{dbInfo?.pool_size || 0}</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/30 text-center">
                  <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                    <Activity className="h-3.5 w-3.5" />
                    <span className="text-xs">In Use</span>
                  </div>
                  <div className="text-xl font-bold text-warning">{dbInfo?.checked_out || 0}</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/30 text-center">
                  <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                    <CircleDot className="h-3.5 w-3.5" />
                    <span className="text-xs">Available</span>
                  </div>
                  <div className="text-xl font-bold text-success">{dbInfo?.checked_in || 0}</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/30 text-center">
                  <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                    <Gauge className="h-3.5 w-3.5" />
                    <span className="text-xs">Overflow</span>
                  </div>
                  <div className="text-xl font-bold">{dbInfo?.overflow || 0}</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/30 text-center">
                  <div className="flex items-center justify-center gap-1 text-muted-foreground mb-1">
                    <Activity className="h-3.5 w-3.5" />
                    <span className="text-xs">Utilization</span>
                  </div>
                  <div className="text-xl font-bold">{poolPercent}%</div>
                </div>
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
            Message Processing Performance
          </CardTitle>
          <CardDescription>Trace statistics for the selected time period</CardDescription>
        </CardHeader>
        <CardContent>
          {analyticsLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-lg bg-muted/30 text-center">
                <div className="text-3xl font-bold">
                  {analytics?.avg_processing_time_ms ? `${Math.round(analytics.avg_processing_time_ms)}` : '—'}
                </div>
                <div className="text-xs text-muted-foreground mt-1">ms avg total</div>
              </div>
              <div className="p-4 rounded-lg bg-muted/30 text-center">
                <div className="text-3xl font-bold">
                  {analytics?.avg_agent_time_ms ? `${Math.round(analytics.avg_agent_time_ms)}` : '—'}
                </div>
                <div className="text-xs text-muted-foreground mt-1">ms avg agent</div>
              </div>
              <div className="p-4 rounded-lg bg-muted/30 text-center">
                <div className="text-3xl font-bold text-success">{analytics?.successful_messages || 0}</div>
                <div className="text-xs text-muted-foreground mt-1">completed</div>
              </div>
              <div className="p-4 rounded-lg bg-muted/30 text-center">
                <div className="text-3xl font-bold text-warning">
                  {(analytics?.total_messages || 0) -
                    (analytics?.successful_messages || 0) -
                    (analytics?.failed_messages || 0)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">processing</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
