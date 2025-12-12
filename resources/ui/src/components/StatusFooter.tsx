import { useQuery } from '@tanstack/react-query';
import { api, cn } from '@/lib';
import { Circle, Loader2, Database, Server, MessageSquare, Cpu } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

// Discord icon as SVG component
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
  </svg>
);

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
        <Circle className={cn('h-2 w-2 fill-current', statusColor, status === 'up' && 'animate-pulse')} />
      )}
      {Icon && <Icon className={cn('h-3 w-3', isLoading ? 'text-muted-foreground' : statusColor)} />}
      <span className={cn('text-xs', isLoading ? 'text-muted-foreground' : statusColor)}>{label}</span>
      {latency !== undefined && status === 'up' && <span className="text-xs text-muted-foreground">({latency}ms)</span>}
    </div>
  );

  if (!tooltipContent || isLoading) {
    return indicator;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{indicator}</TooltipTrigger>
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
  const gatewayDetails = services?.gateway?.details as
    | {
        memory?: { heapUsed: number; heapTotal: number; rss: number };
        uptime?: number;
        nodeVersion?: string;
        pid?: number;
      }
    | undefined;

  // Python API details
  const pythonDetails = services?.python?.details as
    | {
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
          discord?: {
            status?: 'not_running' | 'running';
            message?: string;
          };
        };
      }
    | undefined;

  // Evolution details
  const evolutionDetails = services?.evolution?.details as
    | {
        version?: string;
        whatsappWebVersion?: string;
        clientName?: string;
        instances?: { total: number; connected: number; disconnected: number };
        totals?: { messages: number; contacts: number; chats: number };
      }
    | undefined;

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
                      <span>
                        {gatewayDetails.memory.heapUsed} / {gatewayDetails.memory.heapTotal} MB
                      </span>
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
                      <span>
                        {evolutionDetails.instances.connected}/{evolutionDetails.instances.total} connected
                      </span>
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

          {/* Discord */}
          <StatusIndicator
            status={pythonDetails?.services?.discord?.status === 'running' ? 'up' : 'down'}
            label="Discord"
            isLoading={isLoading}
            icon={DiscordIcon}
            tooltipContent={
              <div className="space-y-1.5 text-xs">
                <p className="font-semibold text-sm">Discord</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  <span className="text-muted-foreground">Status:</span>
                  <span
                    className={
                      pythonDetails?.services?.discord?.status === 'running' ? 'text-success' : 'text-destructive'
                    }
                  >
                    {pythonDetails?.services?.discord?.status || 'not_running'}
                  </span>
                  {pythonDetails?.services?.discord?.message && (
                    <>
                      <span className="text-muted-foreground">Message:</span>
                      <span className="truncate max-w-[150px]">{pythonDetails.services.discord.message}</span>
                    </>
                  )}
                </div>
              </div>
            }
          />
        </div>

        <div className="flex items-center gap-4 text-muted-foreground">
          {health?.timestamp && <span>{new Date(health.timestamp).toLocaleTimeString()}</span>}
          <span>v{APP_VERSION}</span>
        </div>
      </footer>
    </TooltipProvider>
  );
}
