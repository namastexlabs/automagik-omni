import { useEffect, useRef, useMemo, useState, memo } from 'react';
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
  Database,
  Server,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LogEntry } from '@/lib';

// Startup phases for database initialization
type Phase = 'init' | 'pgserve' | 'python' | 'ready' | 'error';

interface PhaseInfo {
  label: string;
  description: string;
  icon: typeof Database;
}

const PHASES: Record<Phase, PhaseInfo> = {
  init: { label: 'Init', description: 'Initializing', icon: Loader2 },
  pgserve: { label: 'PostgreSQL', description: 'Starting database', icon: Database },
  python: { label: 'API Server', description: 'Starting API', icon: Server },
  ready: { label: 'Ready', description: 'Services ready', icon: CheckCircle2 },
  error: { label: 'Error', description: 'Startup failed', icon: XCircle },
};

const PHASE_ORDER: Phase[] = ['init', 'pgserve', 'python', 'ready'];

interface DatabaseStartupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onRetry?: () => void;
  externalError?: string | null;
  currentPhase?: 'idle' | 'pgserve' | 'python' | 'saving' | 'done' | 'error';
}

// Detect current phase from log messages
function detectPhase(logs: LogEntry[], externalPhase?: string): Phase {
  // If external phase indicates ready/done, return ready
  if (externalPhase === 'done') return 'ready';
  if (externalPhase === 'error') return 'error';

  if (logs.length === 0) {
    // Map external phase to internal if no logs yet
    if (externalPhase === 'pgserve') return 'pgserve';
    if (externalPhase === 'python' || externalPhase === 'saving') return 'python';
    return 'init';
  }

  // Check recent logs for phase indicators
  const recentLogs = logs.slice(-15);

  for (let i = recentLogs.length - 1; i >= 0; i--) {
    const msg = recentLogs[i].message.toLowerCase();
    const level = recentLogs[i].level;

    // Error detection
    if (level === 'error' && (msg.includes('failed') || msg.includes('error') || msg.includes('crash'))) {
      return 'error';
    }

    // Ready state - Python API is up
    if (msg.includes('api ready') || msg.includes('started on port') ||
        msg.includes('python is healthy') || msg.includes('api host:')) {
      return 'ready';
    }

    // Python phase
    if (msg.includes('[python]') || msg.includes('[processmanager] starting python') ||
        msg.includes('python api') || msg.includes('uvicorn')) {
      return 'python';
    }

    // pgserve phase
    if (msg.includes('pgserve') || msg.includes('[pgservemanager]') ||
        msg.includes('postgresql') || msg.includes('postgres')) {
      return 'pgserve';
    }
  }

  // Default based on external phase
  if (externalPhase === 'pgserve') return 'pgserve';
  if (externalPhase === 'python' || externalPhase === 'saving') return 'python';

  return 'init';
}

// Get user-friendly error message
function getErrorMessage(logs: LogEntry[]): string | null {
  const errorLogs = logs.filter(l => l.level === 'error');
  if (errorLogs.length === 0) return null;

  const lastError = errorLogs[errorLogs.length - 1].message.toLowerCase();

  if (lastError.includes('port') && lastError.includes('in use')) {
    return 'Database port is already in use. Stop other PostgreSQL instances.';
  }
  if (lastError.includes('permission') || lastError.includes('access denied')) {
    return 'Permission denied. Check data directory permissions.';
  }
  if (lastError.includes('disk') || lastError.includes('space')) {
    return 'Insufficient disk space for database.';
  }
  if (lastError.includes('corrupt') || lastError.includes('invalid')) {
    return 'Database files may be corrupted. Try deleting data/postgres directory.';
  }
  if (lastError.includes('timeout') || lastError.includes('timed out')) {
    return 'Service startup timed out. System may be under heavy load.';
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

// Memoized log list component
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

export function DatabaseStartupModal({
  open,
  onOpenChange,
  onSuccess,
  onRetry,
  externalError,
  currentPhase: externalPhase,
}: DatabaseStartupModalProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [copiedLogs, setCopiedLogs] = useState(false);
  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [stickyPhase, setStickyPhase] = useState<Phase>('init');

  const {
    logs,
    isConnected,
    isConnecting,
    error: connectionError,
    connect,
    clearLogs,
  } = useLogStream({
    services: ['gateway', 'api'],
    autoConnect: open,
    maxLogs: 300,
  });

  // Filter to relevant logs (gateway for pgserve, api for python)
  const relevantLogs = useMemo(
    () => logs.filter(l =>
      l.service === 'gateway' || l.service === 'api'
    ),
    [logs]
  );

  // Calculate current phase based on logs and external phase
  const detectedPhase = useMemo(
    () => detectPhase(relevantLogs, externalPhase),
    [relevantLogs, externalPhase]
  );

  // Update sticky phase - only move forward or to error
  useEffect(() => {
    if (stickyPhase === 'error') return;

    if (detectedPhase === 'error' || externalPhase === 'error') {
      setStickyPhase('error');
      return;
    }

    if (detectedPhase === 'ready' || externalPhase === 'done') {
      setStickyPhase('ready');
      return;
    }

    const currentIndex = PHASE_ORDER.indexOf(stickyPhase);
    const newIndex = PHASE_ORDER.indexOf(detectedPhase);

    if (newIndex > currentIndex) {
      setStickyPhase(detectedPhase);
    }
  }, [detectedPhase, stickyPhase, externalPhase]);

  const currentPhase = stickyPhase;

  const errorMessage = useMemo(
    () => (currentPhase === 'error' ? getErrorMessage(relevantLogs) : null),
    [currentPhase, relevantLogs]
  );

  // Auto-scroll to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [relevantLogs]);

  // Handle success state
  useEffect(() => {
    if (currentPhase === 'ready' && onSuccess) {
      if (successTimeoutRef.current) {
        clearTimeout(successTimeoutRef.current);
      }
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

  // Reset when modal opens
  useEffect(() => {
    if (open) {
      clearLogs();
      setStickyPhase('init');
      connect();
    }
  }, [open, connect, clearLogs]);

  const handleCopyLogs = async () => {
    const logText = relevantLogs
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

  const handleRetry = () => {
    clearLogs();
    setStickyPhase('init');
    onRetry?.();
  };

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
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            )}
            {currentPhase === 'ready'
              ? 'Services Ready!'
              : currentPhase === 'error'
                ? 'Startup Failed'
                : 'Initializing Services...'}
          </DialogTitle>
        </DialogHeader>

        {/* Phase Progress */}
        <div className="flex items-center justify-between px-2 py-3">
          {PHASE_ORDER.slice(1).map((phase, index) => {
            const actualIndex = index + 1; // Skip 'init' in display
            const isComplete = currentPhaseIndex > actualIndex;
            const isCurrent = currentPhase === phase;
            const isError = currentPhase === 'error';
            const PhaseIcon = PHASES[phase].icon;

            return (
              <div key={phase} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      'h-10 w-10 rounded-full flex items-center justify-center transition-colors',
                      isComplete
                        ? 'bg-green-500 text-white'
                        : isCurrent && !isError
                          ? 'bg-blue-500 text-white'
                          : isError && actualIndex <= 1
                            ? 'bg-red-500 text-white'
                            : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : isCurrent && !isError ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <PhaseIcon className="h-5 w-5" />
                    )}
                  </div>
                  <span className="text-xs mt-1 text-muted-foreground font-medium">
                    {PHASES[phase].label}
                  </span>
                </div>

                {index < PHASE_ORDER.length - 2 && (
                  <div
                    className={cn(
                      'h-0.5 w-12 mx-2 transition-colors',
                      isComplete ? 'bg-green-500' : 'bg-muted'
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* External error */}
        {externalError && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-500">Startup Failed</p>
              <p className="text-sm text-muted-foreground">{externalError}</p>
            </div>
          </div>
        )}

        {/* Log-detected error */}
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
              <p className="text-sm font-medium text-green-500">Services Ready!</p>
              <p className="text-sm text-muted-foreground">
                PostgreSQL and API server are running. Proceeding to next step...
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
          {relevantLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Waiting for logs...
            </div>
          ) : (
            <LogList logs={relevantLogs} />
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyLogs}
            disabled={relevantLogs.length === 0}
          >
            <Copy className="h-4 w-4 mr-1" />
            {copiedLogs ? 'Copied!' : 'Copy Logs'}
          </Button>

          <div className="flex gap-2">
            {(currentPhase === 'error' || externalError) && onRetry && (
              <Button
                variant="default"
                size="sm"
                onClick={handleRetry}
                className="bg-blue-500 hover:bg-blue-600"
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
