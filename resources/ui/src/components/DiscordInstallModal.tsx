import { useEffect, useRef, useState, useCallback, memo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Copy,
  RefreshCw,
  Terminal,
  AlertTriangle,
  Bot,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Installation phases
type Phase = 'init' | 'installing' | 'verifying' | 'ready' | 'error';

interface PhaseInfo {
  label: string;
  description: string;
}

const PHASES: Record<Phase, PhaseInfo> = {
  init: { label: 'Init', description: 'Preparing installation' },
  installing: { label: 'Install', description: 'Installing dependencies' },
  verifying: { label: 'Verify', description: 'Verifying installation' },
  ready: { label: 'Ready', description: 'Discord ready' },
  error: { label: 'Error', description: 'Installation failed' },
};

const PHASE_ORDER: Phase[] = ['init', 'installing', 'verifying', 'ready'];

interface LogEntry {
  timestamp: string;
  message: string;
}

interface DiscordInstallModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onRetry?: () => void;
}

// Memoized log list component
const LogList = memo(({ logs }: { logs: LogEntry[] }) => (
  <>
    {logs.map((log, i) => (
      <div key={`${log.timestamp}-${i}`} className="flex gap-2">
        <span className="text-muted-foreground/60 flex-shrink-0">
          [{new Date(log.timestamp).toLocaleTimeString()}]
        </span>
        <span className="break-all text-foreground">
          {log.message}
        </span>
      </div>
    ))}
  </>
));

export function DiscordInstallModal({
  open,
  onOpenChange,
  onSuccess,
  onRetry,
}: DiscordInstallModalProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [copiedLogs, setCopiedLogs] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [phase, setPhase] = useState<Phase>('init');
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Start installation
  const startInstallation = useCallback(() => {
    setLogs([]);
    setPhase('init');
    setError(null);
    setIsConnected(false);

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setLogs(prev => [...prev, { timestamp: new Date().toISOString(), message: 'Starting Discord installation...' }]);
    setPhase('installing');

    // Create EventSource for SSE
    const eventSource = new EventSource('/api/gateway/install-discord', {
      withCredentials: false,
    });
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.addEventListener('status', (event) => {
      const data = JSON.parse(event.data);
      setLogs(prev => [...prev, { timestamp: new Date().toISOString(), message: `[STATUS] ${data.message}` }]);

      if (data.phase === 'complete') {
        setPhase('verifying');
        if (data.version) {
          setLogs(prev => [...prev, { timestamp: new Date().toISOString(), message: `Discord.py version: ${data.version}` }]);
        }
      }
    });

    eventSource.addEventListener('log', (event) => {
      const data = JSON.parse(event.data);
      setLogs(prev => [...prev, { timestamp: data.timestamp, message: data.message }]);
    });

    eventSource.addEventListener('error', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data);
        setError(data.message || 'Installation failed');
        setPhase('error');
      } catch {
        // SSE connection error
      }
    });

    eventSource.addEventListener('done', (event) => {
      const data = JSON.parse(event.data);
      eventSource.close();
      setIsConnected(false);

      if (data.success) {
        setPhase('ready');
      } else {
        setPhase('error');
        if (!error) {
          setError('Installation failed');
        }
      }
    });

    eventSource.onerror = () => {
      // Only set error if we haven't received a done event
      if (phase !== 'ready' && phase !== 'error') {
        setError('Connection to installation service failed');
        setPhase('error');
      }
      eventSource.close();
      setIsConnected(false);
    };
  }, [phase, error]);

  // Start installation when modal opens
  useEffect(() => {
    if (open) {
      startInstallation();
    } else {
      // Cleanup on close
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [open, startInstallation]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Handle success state
  useEffect(() => {
    if (phase === 'ready' && onSuccess) {
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
  }, [phase, onSuccess]);

  // Copy logs to clipboard
  const handleCopyLogs = async () => {
    const logText = logs
      .map(l => `[${l.timestamp}] ${l.message}`)
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
    startInstallation();
    onRetry?.();
  };

  // Get phase index for progress
  const currentPhaseIndex = phase === 'error' ? -1 : PHASE_ORDER.indexOf(phase);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {phase === 'ready' ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : phase === 'error' ? (
              <XCircle className="h-5 w-5 text-red-500" />
            ) : (
              <Loader2 className="h-5 w-5 animate-spin text-[#5865F2]" />
            )}
            {phase === 'ready'
              ? 'Discord Ready!'
              : phase === 'error'
                ? 'Installation Failed'
                : 'Installing Discord Support...'}
          </DialogTitle>
        </DialogHeader>

        {/* Phase Progress */}
        <div className="flex items-center justify-between px-2 py-3">
          {PHASE_ORDER.map((p, index) => {
            const isComplete = currentPhaseIndex > index;
            const isCurrent = phase === p;
            const isError = phase === 'error';

            return (
              <div key={p} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={cn(
                      'h-8 w-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors',
                      isComplete
                        ? 'bg-green-500 text-white'
                        : isCurrent && !isError
                          ? 'bg-[#5865F2] text-white'
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
                    {PHASES[p].label}
                  </span>
                </div>

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

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-500">Installation Failed</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        )}

        {/* Success message */}
        {phase === 'ready' && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-500">Discord Ready!</p>
              <p className="text-sm text-muted-foreground">
                Discord dependencies installed successfully. You can now configure your bot.
              </p>
            </div>
          </div>
        )}

        {/* Connection status */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Terminal className="h-3 w-3" />
          <span>Installation Log</span>
          <Badge variant={isConnected ? 'default' : 'secondary'} className="text-xs h-5">
            {isConnected ? 'Installing...' : phase === 'ready' ? 'Complete' : 'Waiting'}
          </Badge>
        </div>

        {/* Log viewer */}
        <div
          ref={logContainerRef}
          className="flex-1 min-h-[200px] max-h-[300px] overflow-y-auto bg-muted/50 rounded-lg p-3 font-mono text-xs space-y-0.5"
        >
          {logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Preparing installation...
            </div>
          ) : (
            <LogList logs={logs} />
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyLogs}
            disabled={logs.length === 0}
          >
            <Copy className="h-4 w-4 mr-1" />
            {copiedLogs ? 'Copied!' : 'Copy Logs'}
          </Button>

          <div className="flex gap-2">
            {phase === 'error' && (
              <Button
                variant="default"
                size="sm"
                onClick={handleRetry}
                className="bg-[#5865F2] hover:bg-[#4752C4]"
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
              {phase === 'ready' ? 'Continue' : 'Cancel'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
