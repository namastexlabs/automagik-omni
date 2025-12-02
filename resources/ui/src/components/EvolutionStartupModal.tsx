import { useEffect, useRef, useMemo, useState, useCallback, memo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useLogStream } from '@/hooks/useLogStream';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Copy,
  RefreshCw,
  Terminal,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LogEntry } from '@/lib';

// Startup phases
type Phase = 'init' | 'config' | 'spawn' | 'health' | 'ready' | 'error';

interface PhaseInfo {
  label: string;
  description: string;
}

const PHASES: Record<Phase, PhaseInfo> = {
  init: { label: 'Init', description: 'Initializing service' },
  config: { label: 'Config', description: 'Loading configuration' },
  spawn: { label: 'Spawn', description: 'Starting process' },
  health: { label: 'Health', description: 'Health check' },
  ready: { label: 'Ready', description: 'Service ready' },
  error: { label: 'Error', description: 'Startup failed' },
};

const PHASE_ORDER: Phase[] = ['init', 'config', 'spawn', 'health', 'ready'];

interface EvolutionStartupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onRetry?: () => void;
  externalError?: string | null; // Error passed from parent component
}

// Detect current phase from log messages
function detectPhase(logs: LogEntry[]): Phase {
  if (logs.length === 0) return 'init';

  // Check recent logs (last 10) for phase indicators
  const recentLogs = logs.slice(-10);

  for (let i = recentLogs.length - 1; i >= 0; i--) {
    const msg = recentLogs[i].message.toLowerCase();
    const level = recentLogs[i].level;

    // Error detection first
    if (level === 'error' || msg.includes('error') || msg.includes('failed') || msg.includes('econnrefused')) {
      return 'error';
    }

    // Ready state
    if (msg.includes('ready') || msg.includes('running on port') || msg.includes('started successfully') || msg.includes('listening on')) {
      return 'ready';
    }

    // Health check phase
    if (msg.includes('health') || msg.includes('checking') || msg.includes('waiting for')) {
      return 'health';
    }

    // Spawn phase
    if (msg.includes('prisma') || msg.includes('migration') || msg.includes('spawn') || msg.includes('starting evolution') || msg.includes('process')) {
      return 'spawn';
    }

    // Config phase
    if (msg.includes('config') || msg.includes('loading') || msg.includes('database')) {
      return 'config';
    }
  }

  return 'init';
}

// Get user-friendly error message
function getErrorMessage(logs: LogEntry[]): string | null {
  const errorLogs = logs.filter(l => l.level === 'error');
  if (errorLogs.length === 0) return null;

  const lastError = errorLogs[errorLogs.length - 1].message.toLowerCase();

  if (lastError.includes('database not configured') || lastError.includes('db_')) {
    return 'Database not configured. Complete database setup first.';
  }
  if (lastError.includes('econnrefused') && lastError.includes('5432')) {
    return 'Cannot connect to PostgreSQL. Is the database running?';
  }
  if (lastError.includes('prisma') || lastError.includes('migration')) {
    return 'Database migration failed. Check database permissions.';
  }
  if (lastError.includes('health check') || lastError.includes('timeout')) {
    return 'Service health check timed out. Evolution may be slow to start.';
  }
  if (lastError.includes('circuit breaker')) {
    return 'Service crashed repeatedly. Check logs for details.';
  }

  return 'Service startup failed. Check logs for details.';
}

// Get log line color based on level
function getLogColor(level: LogEntry['level']): string {
  switch (level) {
    case 'error':
      return 'text-red-500';
    case 'warn':
      return 'text-yellow-500';
    case 'info':
      return 'text-foreground';
    case 'debug':
      return 'text-muted-foreground';
    default:
      return 'text-muted-foreground';
  }
}

// Memoized log list component to prevent re-renders of all items
const LogList = memo(({ logs }: { logs: LogEntry[] }) => (
  <>
    {logs.map((log, i) => (
      <div key={`${log.timestamp}-${i}`} className="flex gap-2">
        <span className="text-muted-foreground/60 flex-shrink-0">
          [{new Date(log.timestamp).toLocaleTimeString()}]
        </span>
        <span className={cn('break-all', getLogColor(log.level))}>
          {log.message}
        </span>
      </div>
    ))}
  </>
));

export function EvolutionStartupModal({
  open,
  onOpenChange,
  onSuccess,
  onRetry,
  externalError,
}: EvolutionStartupModalProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [copiedLogs, setCopiedLogs] = useState(false);
  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Sticky phase state
  const [stickyPhase, setStickyPhase] = useState<Phase>('init');

  const {
    logs,
    isConnected,
    isConnecting,
    error: connectionError,
    connect,
    clearLogs,
  } = useLogStream({
    services: ['evolution'],
    autoConnect: open,
    maxLogs: 200,
  });

  // Filter to only evolution logs
  const evolutionLogs = useMemo(
    () => logs.filter(l => l.service === 'evolution'),
    [logs]
  );

  // Calculate current phase based on logs
  const detectedPhase = useMemo(() => detectPhase(evolutionLogs), [evolutionLogs]);

  // Update sticky phase - only move forward or to error
  useEffect(() => {
    // If currently error, stay error until retry (which resets state)
    if (stickyPhase === 'error') return;

    // If detected 'error', switch to error
    if (detectedPhase === 'error') {
      setStickyPhase('error');
      return;
    }

    // If detected 'ready', switch to ready
    if (detectedPhase === 'ready') {
      setStickyPhase('ready');
      return;
    }

    // For other phases, only advance forward
    const currentIndex = PHASE_ORDER.indexOf(stickyPhase);
    const newIndex = PHASE_ORDER.indexOf(detectedPhase);

    if (newIndex > currentIndex) {
      setStickyPhase(detectedPhase);
    }
  }, [detectedPhase, stickyPhase]);

  const currentPhase = stickyPhase;

  const errorMessage = useMemo(
    () => (currentPhase === 'error' ? getErrorMessage(evolutionLogs) : null),
    [currentPhase, evolutionLogs]
  );

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [evolutionLogs]);

  // Handle success state
  useEffect(() => {
    if (currentPhase === 'ready' && onSuccess) {
      // Clear any existing timeout
      if (successTimeoutRef.current) {
        clearTimeout(successTimeoutRef.current);
      }
      // Wait a moment to show success, then callback
      successTimeoutRef.current = setTimeout(() => {
        onSuccess();
      }, 1500);
    }

    return () => {
      if (successTimeoutRef.current) {
        clearTimeout(successTimeoutRef.current);
      }
    };
  }, [currentPhase, onSuccess]);

  // Reconnect and reset when modal opens
  useEffect(() => {
    if (open) {
      clearLogs();
      setStickyPhase('init'); // Reset phase on new open
      connect();
    }
  }, [open, connect, clearLogs]);

  // Copy logs to clipboard
  const handleCopyLogs = async () => {
    const logText = evolutionLogs
      .map(l => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`)
      .join('\n');

    try {
      await navigator.clipboard.writeText(logText);
      setCopiedLogs(true);
      setTimeout(() => setCopiedLogs(false), 2000);
    } catch {
      console.error('Failed to copy logs');
    }
  };

  // Handle retry
  const handleRetry = () => {
    clearLogs();
    setStickyPhase('init'); // Reset phase on retry
    onRetry?.();
  };

  // Get phase index for progress
  const currentPhaseIndex = currentPhase === 'error' ? -1 : PHASE_ORDER.indexOf(currentPhase);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {currentPhase === 'ready' ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : currentPhase === 'error' ? (
              <XCircle className="h-5 w-5 text-red-500" />
            ) : (
              <Loader2 className="h-5 w-5 animate-spin text-[#25D366]" />
            )}
            {currentPhase === 'ready'
              ? 'WhatsApp Service Ready!'
              : currentPhase === 'error'
                ? 'Startup Failed'
                : 'Starting WhatsApp Service...'}
          </DialogTitle>
        </DialogHeader>

        {/* Phase Progress */}
        <div className="flex items-center justify-between px-2 py-3">
          {PHASE_ORDER.map((phase, index) => {
            const isComplete = currentPhaseIndex > index;
            const isCurrent = currentPhase === phase;
            const isError = currentPhase === 'error';

            return (
              <div key={phase} className="flex items-center">
                {/* Phase indicator */}
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      'h-8 w-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors',
                      isComplete
                        ? 'bg-green-500 text-white'
                        : isCurrent && !isError
                          ? 'bg-[#25D366] text-white'
                          : isError && index <= 0
                            ? 'bg-red-500 text-white'
                            : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : isCurrent && !isError ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span className="text-xs mt-1 text-muted-foreground">
                    {PHASES[phase].label}
                  </span>
                </div>

                {/* Connector line */}
                {index < PHASE_ORDER.length - 1 && (
                  <div
                    className={cn(
                      'h-0.5 w-8 mx-1 transition-colors',
                      isComplete ? 'bg-green-500' : 'bg-muted'
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* External error from parent - shown prominently */}
        {externalError && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-500">Startup Failed</p>
              <p className="text-sm text-muted-foreground">{externalError}</p>
            </div>
          </div>
        )}

        {/* Log-detected error message (only show if no external error) */}
        {errorMessage && !externalError && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-500">Startup Failed</p>
              <p className="text-sm text-muted-foreground">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Success message */}
        {currentPhase === 'ready' && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-500">Service Ready!</p>
              <p className="text-sm text-muted-foreground">
                WhatsApp service is now running and ready to accept connections.
              </p>
            </div>
          </div>
        )}

        {/* Connection status */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Terminal className="h-3 w-3" />
          <span>Live Logs</span>
          <Badge variant={isConnected ? 'default' : 'secondary'} className="text-xs h-5">
            {isConnecting ? 'Connecting...' : isConnected ? 'Connected' : 'Disconnected'}
          </Badge>
          {connectionError && (
            <span className="text-red-500">{connectionError}</span>
          )}
        </div>

        {/* Log viewer */}
        <div
          ref={logContainerRef}
          className="flex-1 min-h-[200px] max-h-[300px] overflow-y-auto bg-muted/50 rounded-lg p-3 font-mono text-xs space-y-0.5"
        >
          {evolutionLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Waiting for logs...
            </div>
          ) : (
            <LogList logs={evolutionLogs} />
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyLogs}
            disabled={evolutionLogs.length === 0}
          >
            <Copy className="h-4 w-4 mr-1" />
            {copiedLogs ? 'Copied!' : 'Copy Logs'}
          </Button>

          <div className="flex gap-2">
            {/* Show Retry when there's any error (external or log-detected) */}
            {(currentPhase === 'error' || externalError) && onRetry && (
              <Button
                variant="default"
                size="sm"
                onClick={handleRetry}
                className="bg-[#25D366] hover:bg-[#1da851]"
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                Retry
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
            >
              {currentPhase === 'ready' ? 'Close' : 'Cancel'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
