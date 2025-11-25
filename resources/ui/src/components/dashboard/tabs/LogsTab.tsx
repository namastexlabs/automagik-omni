import { useEffect, useRef, useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useLogStream } from '@/hooks/useLogStream';
import { api, type LogEntry, type LogServiceName, type Pm2Status } from '@/lib/api';
import {
  ScrollText,
  Wifi,
  WifiOff,
  Pause,
  Play,
  Trash2,
  ArrowDown,
  RefreshCw,
  Filter,
  RotateCcw,
  Power,
  Loader2,
  Clock,
  MemoryStick,
  Cpu,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const SERVICE_COLORS: Record<LogServiceName, string> = {
  api: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  discord: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  evolution: 'bg-green-500/20 text-green-400 border-green-500/30',
  gateway: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
};

const LEVEL_COLORS: Record<string, string> = {
  error: 'bg-red-500/20 text-red-400',
  warn: 'bg-yellow-500/20 text-yellow-400',
  info: 'bg-blue-500/20 text-blue-400',
  debug: 'bg-gray-500/20 text-gray-400',
  unknown: 'bg-gray-500/20 text-gray-400',
};

interface LogLineProps {
  entry: LogEntry;
}

function LogLine({ entry }: LogLineProps) {
  const formattedTime = entry.timestamp.split('T')[1]?.slice(0, 8) || entry.timestamp;

  return (
    <div className="flex items-start gap-2 py-1 px-2 font-mono text-xs hover:bg-muted/50 rounded">
      <span className="text-muted-foreground shrink-0 w-16">{formattedTime}</span>
      <Badge
        variant="outline"
        className={cn('shrink-0 w-16 justify-center text-[10px] px-1', SERVICE_COLORS[entry.service])}
      >
        {entry.service}
      </Badge>
      <Badge
        variant="secondary"
        className={cn('shrink-0 w-12 justify-center text-[10px] px-1 uppercase', LEVEL_COLORS[entry.level])}
      >
        {entry.level}
      </Badge>
      <span className="flex-1 break-all whitespace-pre-wrap">{entry.message}</span>
    </div>
  );
}

function formatUptime(seconds?: number): string {
  if (!seconds || seconds < 0) return 'N/A';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const hours = Math.floor(seconds / 3600);
  if (hours < 24) return `${hours}h ${Math.floor((seconds % 3600) / 60)}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

interface ServiceStatusBadgeProps {
  service: LogServiceName;
  status?: Pm2Status;
  onRestart: () => void;
  isRestarting: boolean;
}

function ServiceStatusBadge({ service, status, onRestart, isRestarting }: ServiceStatusBadgeProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1">
            <Badge
              variant="outline"
              className={cn(
                'text-xs cursor-default',
                status?.online
                  ? 'bg-green-500/10 text-green-400 border-green-500/30'
                  : 'bg-red-500/10 text-red-400 border-red-500/30'
              )}
            >
              <Power className={cn('h-3 w-3 mr-1', status?.online ? 'text-green-400' : 'text-red-400')} />
              {status?.online ? 'Online' : 'Offline'}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={onRestart}
              disabled={isRestarting}
            >
              {isRestarting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RotateCcw className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <div className="space-y-1 text-xs">
            <div className="font-medium">{status?.name || service}</div>
            {status?.online && (
              <>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  Uptime: {formatUptime(status.uptime)}
                </div>
                {status.memory && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <MemoryStick className="h-3 w-3" />
                    Memory: {status.memory} MB
                  </div>
                )}
                {status.cpu !== undefined && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Cpu className="h-3 w-3" />
                    CPU: {status.cpu}%
                  </div>
                )}
                {status.restarts !== undefined && status.restarts > 0 && (
                  <div className="text-muted-foreground">
                    Restarts: {status.restarts}
                  </div>
                )}
                {status.pid && (
                  <div className="text-muted-foreground">
                    PID: {status.pid}
                  </div>
                )}
              </>
            )}
            <div className="pt-1 border-t text-muted-foreground">
              Click restart button to restart this service
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function LogsTab() {
  const queryClient = useQueryClient();
  const {
    logs,
    isConnected,
    isConnecting,
    error,
    services,
    selectedServices,
    setSelectedServices,
    connect,
    disconnect,
    clearLogs,
    isPaused,
    togglePause,
  } = useLogStream({ autoConnect: true });

  const [levelFilter, setLevelFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [restartingServices, setRestartingServices] = useState<Set<LogServiceName>>(new Set());
  const [restartMessage, setRestartMessage] = useState<{ success: boolean; message: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Fetch PM2 statuses
  const { data: pm2Statuses } = useQuery({
    queryKey: ['pm2Statuses'],
    queryFn: () => api.logs.getAllStatuses(),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Restart mutation
  const restartMutation = useMutation({
    mutationFn: (service: LogServiceName) => api.logs.restart(service),
    onMutate: (service) => {
      setRestartingServices(prev => new Set(prev).add(service));
      setRestartMessage(null);
    },
    onSuccess: (result, service) => {
      setRestartingServices(prev => {
        const next = new Set(prev);
        next.delete(service);
        return next;
      });
      setRestartMessage(result);
      // Refetch statuses after restart
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['pm2Statuses'] });
      }, 2000);
    },
    onError: (error, service) => {
      setRestartingServices(prev => {
        const next = new Set(prev);
        next.delete(service);
        return next;
      });
      setRestartMessage({
        success: false,
        message: error instanceof Error ? error.message : 'Restart failed',
      });
    },
  });

  // Clear restart message after 5 seconds
  useEffect(() => {
    if (restartMessage) {
      const timer = setTimeout(() => setRestartMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [restartMessage]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && bottomRef.current && !isPaused) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll, isPaused]);

  // Filter logs by level
  const filteredLogs = levelFilter === 'all'
    ? logs
    : logs.filter(log => log.level === levelFilter);

  const handleServiceToggle = (service: LogServiceName, checked: boolean) => {
    if (checked) {
      setSelectedServices([...selectedServices, service]);
    } else {
      setSelectedServices(selectedServices.filter(s => s !== service));
    }
  };

  const handleRestart = useCallback((service: LogServiceName) => {
    restartMutation.mutate(service);
  }, [restartMutation]);

  return (
    <div className="space-y-4 h-[calc(100vh-220px)]">
      {/* Controls */}
      <Card>
        <CardHeader className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base flex items-center gap-2">
                <ScrollText className="h-4 w-4" />
                Log Stream
              </CardTitle>
              {isConnected ? (
                <Badge variant="outline" className="bg-green-500/20 text-green-400 border-green-500/30">
                  <Wifi className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              ) : isConnecting ? (
                <Badge variant="outline" className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
                  <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  Connecting
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-red-500/20 text-red-400 border-red-500/30">
                  <WifiOff className="h-3 w-3 mr-1" />
                  Disconnected
                </Badge>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Pause/Resume */}
              <Button
                variant="outline"
                size="sm"
                onClick={togglePause}
                className={isPaused ? 'text-yellow-400' : ''}
              >
                {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              </Button>

              {/* Clear */}
              <Button variant="outline" size="sm" onClick={clearLogs}>
                <Trash2 className="h-4 w-4" />
              </Button>

              {/* Connect/Disconnect */}
              {isConnected ? (
                <Button variant="outline" size="sm" onClick={disconnect}>
                  Disconnect
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={connect} disabled={isConnecting}>
                  Connect
                </Button>
              )}
            </div>
          </div>

          {error && (
            <CardDescription className="text-destructive mt-2">
              {error}
            </CardDescription>
          )}

          {restartMessage && (
            <CardDescription className={cn('mt-2', restartMessage.success ? 'text-green-400' : 'text-destructive')}>
              {restartMessage.message}
            </CardDescription>
          )}
        </CardHeader>

        <CardContent className="py-3 border-t">
          <div className="flex flex-wrap items-center gap-4">
            {/* Service Filters with Status and Restart */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Filter className="h-3.5 w-3.5" />
                Services:
              </span>
              {services.map(service => (
                <div key={service.id} className="flex items-center gap-1.5">
                  <Checkbox
                    checked={selectedServices.includes(service.id)}
                    onCheckedChange={(checked) => handleServiceToggle(service.id, !!checked)}
                    disabled={!service.available}
                  />
                  <Badge
                    variant="outline"
                    className={cn(
                      'text-xs',
                      selectedServices.includes(service.id) ? SERVICE_COLORS[service.id] : 'opacity-50'
                    )}
                  >
                    {service.name}
                  </Badge>
                  <ServiceStatusBadge
                    service={service.id}
                    status={pm2Statuses?.[service.id]}
                    onRestart={() => handleRestart(service.id)}
                    isRestarting={restartingServices.has(service.id)}
                  />
                </div>
              ))}
            </div>

            {/* Level Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Level:</span>
              <Select value={levelFilter} onValueChange={setLevelFilter}>
                <SelectTrigger className="w-[100px] h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="warn">Warning</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="debug">Debug</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Auto-scroll Toggle */}
            <label className="flex items-center gap-2 cursor-pointer ml-auto">
              <Checkbox
                checked={autoScroll}
                onCheckedChange={(checked) => setAutoScroll(!!checked)}
              />
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <ArrowDown className="h-3.5 w-3.5" />
                Auto-scroll
              </span>
            </label>

            {/* Log count */}
            <Badge variant="secondary" className="text-xs">
              {filteredLogs.length} / {logs.length} logs
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Log Viewer */}
      <Card className="flex-1 min-h-0">
        <ScrollArea className="h-[calc(100vh-380px)]" ref={scrollRef}>
          <div className="p-2 space-y-0.5">
            {filteredLogs.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                {logs.length === 0 ? (
                  <>
                    <ScrollText className="h-12 w-12 mx-auto mb-4 opacity-30" />
                    <p>No logs yet</p>
                    <p className="text-xs mt-1">Logs will appear here in real-time</p>
                  </>
                ) : (
                  <>
                    <Filter className="h-12 w-12 mx-auto mb-4 opacity-30" />
                    <p>No logs match the current filter</p>
                  </>
                )}
              </div>
            ) : (
              filteredLogs.map((entry, index) => (
                <LogLine key={`${entry.timestamp}-${index}`} entry={entry} />
              ))
            )}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      </Card>

      {/* Paused Indicator */}
      {isPaused && (
        <div className="fixed bottom-4 right-4 z-50">
          <Badge className="bg-yellow-500/90 text-yellow-950 px-4 py-2 text-sm shadow-lg">
            <Pause className="h-4 w-4 mr-2" />
            Stream Paused
          </Badge>
        </div>
      )}
    </div>
  );
}
