import { useQuery } from '@tanstack/react-query';
import { api, cn } from '@/lib';
import { Circle, Loader2, Database, Server, MessageSquare, Cpu } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// App version - will be replaced with npm package version
const APP_VERSION = '0.1.0';

// Format seconds to human readable duration
function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours < 24) return `${hours}h ${minutes}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

// Format large numbers with K/M suffix
function formatCount(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

interface ServiceHealth {
  status: 'up' | 'down' | 'degraded';
  latency?: number;
  details?: Record<string, unknown>;
}

interface HealthResponse {
  status: 'up' | 'down' | 'degraded';
  timestamp: string;
  services: {
    gateway: ServiceHealth;
    python: ServiceHealth;
    evolution: ServiceHealth;
  };
}

function StatusIndicator({
  status,
  label,
  latency,
  isLoading,
  icon: Icon,
  tooltipContent,
}: {
  status?: 'up' | 'down' | 'degraded';
  label: string;
  latency?: number;
  isLoading?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
  tooltipContent?: React.ReactNode;
}) {
  const statusColor = {
    up: 'text-success',
    down: 'text-destructive',
    degraded: 'text-warning',
  }[status || 'down'];

  const indicator = (
    <div className="flex items-center gap-1.5 cursor-default hover:opacity-80 transition-opacity">
      {isLoading ? (
        <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
      ) : (
        <Circle className={cn("h-2 w-2 fill-current", statusColor, status === 'up' && "animate-pulse")} />
      )}
      {Icon && <Icon className={cn("h-3 w-3", isLoading ? "text-muted-foreground" : statusColor)} />}
      <span className={cn("text-xs", isLoading ? "text-muted-foreground" : statusColor)}>{label}</span>
      {latency !== undefined && status === 'up' && (
        <span className="text-xs text-muted-foreground">({latency}ms)</span>
      )}
    </div>
  );

  if (!tooltipContent || isLoading) {
    return indicator;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        {indicator}
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs">
        {tooltipContent}
      </TooltipContent>
    </Tooltip>
  );
}

export function StatusFooter() {
  const { data: health, isLoading } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000,
    retry: 1,
  });

  const services = health?.services;

  // Gateway stats
  const gatewayDetails = services?.gateway?.details as {
    memory?: { heapUsed: number; heapTotal: number; rss: number };
    uptime?: number;
    nodeVersion?: string;
    pid?: number;
  } | undefined;

  // Python API details
  const pythonDetails = services?.python?.details as {
    status?: string;
    timestamp?: string;
    services?: {
      api?: {
        status?: string;
        uptime?: number;
        memory_mb?: number;
        checks?: {
          database?: string;
          runtime?: string;
        };
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

  // Evolution details
  const evolutionDetails = services?.evolution?.details as {
    version?: string;
    whatsappWebVersion?: string;
    clientName?: string;
    instances?: { total: number; connected: number; disconnected: number };
    totals?: { messages: number; contacts: number; chats: number };
  } | undefined;

  // Database status from Python API
  const dbInfo = pythonDetails?.services?.database;
  const apiInfo = pythonDetails?.services?.api;
  const dbStatus = dbInfo?.status === 'connected' || apiInfo?.checks?.database === 'connected' ? 'up' : 'down';

  return (
    <TooltipProvider delayDuration={200}>
      <footer className="flex items-center justify-between px-4 py-2 bg-card border-t border-border text-xs">
        <div className="flex items-center gap-4">
          {/* Gateway */}
          <StatusIndicator
            status={services?.gateway?.status}
            label="Gateway"
            latency={services?.gateway?.latency}
            isLoading={isLoading}
            icon={Server}
            tooltipContent={
              <div className="space-y-1.5 text-xs">
                <p className="font-semibold text-sm">Gateway</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="text-success">{services?.gateway?.status || 'unknown'}</span>

                  {gatewayDetails?.memory && (
                    <>
                      <span className="text-muted-foreground">Memory:</span>
                      <span>{gatewayDetails.memory.heapUsed} / {gatewayDetails.memory.heapTotal} MB</span>
                    </>
                  )}

                  {gatewayDetails?.uptime !== undefined && (
                    <>
                      <span className="text-muted-foreground">Uptime:</span>
                      <span>{formatUptime(gatewayDetails.uptime)}</span>
                    </>
                  )}

                  {gatewayDetails?.nodeVersion && (
                    <>
                      <span className="text-muted-foreground">Node:</span>
                      <span>{gatewayDetails.nodeVersion}</span>
                    </>
                  )}

                  {gatewayDetails?.pid && (
                    <>
                      <span className="text-muted-foreground">PID:</span>
                      <span>{gatewayDetails.pid}</span>
                    </>
                  )}
                </div>
              </div>
            }
          />

          {/* Python API */}
          <StatusIndicator
            status={services?.python?.status}
            label="API"
            latency={services?.python?.latency}
            isLoading={isLoading}
            icon={Cpu}
            tooltipContent={
              <div className="space-y-1.5 text-xs">
                <p className="font-semibold text-sm">Python API</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="text-success">{services?.python?.status || 'unknown'}</span>

                  <span className="text-muted-foreground">Latency:</span>
                  <span>{services?.python?.latency ?? '-'}ms</span>

                  {apiInfo?.memory_mb && (
                    <>
                      <span className="text-muted-foreground">Memory:</span>
                      <span>{apiInfo.memory_mb} MB</span>
                    </>
                  )}

                  {apiInfo?.uptime !== undefined && (
                    <>
                      <span className="text-muted-foreground">Uptime:</span>
                      <span>{formatUptime(apiInfo.uptime)}</span>
                    </>
                  )}

                  <span className="text-muted-foreground">Runtime:</span>
                  <span>{apiInfo?.checks?.runtime || 'unknown'}</span>
                </div>
              </div>
            }
          />

          {/* Database */}
          <StatusIndicator
            status={dbStatus as 'up' | 'down'}
            label="Database"
            isLoading={isLoading}
            icon={Database}
            tooltipContent={
              <div className="space-y-1.5 text-xs">
                <p className="font-semibold text-sm">PostgreSQL</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <span className="text-muted-foreground">Status:</span>
                  <span className={dbStatus === 'up' ? 'text-success' : 'text-destructive'}>
                    {dbInfo?.status || apiInfo?.checks?.database || 'unknown'}
                  </span>

                  {dbInfo?.pool_size !== undefined && (
                    <>
                      <span className="text-muted-foreground">Pool Size:</span>
                      <span>{dbInfo.pool_size}</span>
                    </>
                  )}

                  {dbInfo?.checked_out !== undefined && (
                    <>
                      <span className="text-muted-foreground">In Use:</span>
                      <span>{dbInfo.checked_out}</span>
                    </>
                  )}

                  {dbInfo?.checked_in !== undefined && (
                    <>
                      <span className="text-muted-foreground">Available:</span>
                      <span>{dbInfo.checked_in}</span>
                    </>
                  )}
                </div>
              </div>
            }
          />

          {/* WhatsApp Web */}
          <StatusIndicator
            status={services?.evolution?.status}
            label="WhatsApp Web"
            latency={services?.evolution?.latency}
            isLoading={isLoading}
            icon={MessageSquare}
            tooltipContent={
              <div className="space-y-1.5 text-xs">
                <p className="font-semibold text-sm">WhatsApp Web API</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <span className="text-muted-foreground">Status:</span>
                  <span className={services?.evolution?.status === 'up' ? 'text-success' : 'text-destructive'}>
                    {services?.evolution?.status || 'unknown'}
                  </span>

                  <span className="text-muted-foreground">Latency:</span>
                  <span>{services?.evolution?.latency ?? '-'}ms</span>

                  {evolutionDetails?.version && (
                    <>
                      <span className="text-muted-foreground">Version:</span>
                      <span>{evolutionDetails.version}</span>
                    </>
                  )}

                  {evolutionDetails?.whatsappWebVersion && (
                    <>
                      <span className="text-muted-foreground">WhatsApp:</span>
                      <span className="truncate max-w-[100px]">{evolutionDetails.whatsappWebVersion}</span>
                    </>
                  )}

                  {evolutionDetails?.instances && (
                    <>
                      <span className="text-muted-foreground">Instances:</span>
                      <span>{evolutionDetails.instances.connected}/{evolutionDetails.instances.total} connected</span>
                    </>
                  )}

                  {evolutionDetails?.totals && (
                    <>
                      <span className="text-muted-foreground">Messages:</span>
                      <span>{formatCount(evolutionDetails.totals.messages)}</span>

                      <span className="text-muted-foreground">Contacts:</span>
                      <span>{formatCount(evolutionDetails.totals.contacts)}</span>

                      <span className="text-muted-foreground">Chats:</span>
                      <span>{formatCount(evolutionDetails.totals.chats)}</span>
                    </>
                  )}
                </div>
              </div>
            }
          />
        </div>

        <div className="flex items-center gap-4 text-muted-foreground">
          {health?.timestamp && (
            <span>
              {new Date(health.timestamp).toLocaleTimeString()}
            </span>
          )}
          <span>v{APP_VERSION}</span>
        </div>
      </footer>
    </TooltipProvider>
  );
}
