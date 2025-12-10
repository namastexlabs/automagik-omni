import { useEffect, useRef, useMemo, useState, memo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useLogStream } from '@/hooks/useLogStream';
import { api } from '@/lib/api';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Copy,
  RefreshCw,
  Terminal,
  AlertTriangle,
  Server,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LogEntry } from '@/lib';

// Startup phases for MCP server
type Phase = 'idle' | 'starting' | 'running' | 'ready' | 'error';

interface McpStartupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
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
        <span className="text-muted-foreground/60 flex-shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
        <span className={cn('break-all', getLogColor(log.level))}>{log.message}</span>
      </div>
    ))}
  </>
));

// Health check function
async function checkMcpHealth(timeoutMs: number = 3000): Promise<boolean> {
  try {
    const response = await fetch('/mcp', {
      method: 'GET',
      signal: AbortSignal.timeout(timeoutMs)
    });
    return response.ok || response.status === 405; // 405 is fine - endpoint exists
  } catch {
    return false;
  }
}

export function McpStartupModal({
  open,
  onOpenChange,
  onSuccess,
}: McpStartupModalProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [copiedLogs, setCopiedLogs] = useState(false);
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState<string | null>(null);
  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startedRef = useRef(false);

  const {
    logs,
    isConnected,
    isConnecting,
    error: connectionError,
    connect,
    clearLogs,
  } = useLogStream({
    services: ['gateway'],
    autoConnect: open,
    maxLogs: 200,
  });

  // Filter to MCP-relevant logs
  const relevantLogs = useMemo(() =>
    logs.filter((l) =>
      l.message.toLowerCase().includes('mcp') ||
      l.message.toLowerCase().includes('processmanager')
    ),
    [logs]
  );

  // Start MCP server when modal opens
  useEffect(() => {
    if (!open || startedRef.current) return;
    startedRef.current = true;

    const startServer = async () => {
      setPhase('starting');
      setError(null);

      try {
        const result = await api.mcp.startServer();

        if (!result.success) {
          setPhase('error');
          setError(result.message || 'Failed to start MCP server');
          return;
        }

        setPhase('running');

        // Poll for health check
        const startTime = Date.now();
        const timeout = 30000; // 30 seconds

        while (Date.now() - startTime < timeout) {
          if (await checkMcpHealth()) {
            setPhase('ready');
            return;
          }
          await new Promise(r => setTimeout(r, 1000));
        }

        // Timeout - but server might still be starting
        setPhase('error');
        setError('MCP server did not become healthy within 30 seconds');
      } catch (err) {
        setPhase('error');
        setError(err instanceof Error ? err.message : 'Failed to start MCP server');
      }
    };

    startServer();
  }, [open]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [relevantLogs]);

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

  // Reset when modal closes
  useEffect(() => {
    if (!open) {
      startedRef.current = false;
      setPhase('idle');
      setError(null);
    } else {
      clearLogs();
      connect();
    }
  }, [open, connect, clearLogs]);

  const handleCopyLogs = async () => {
    const logText = relevantLogs.map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`).join('\n');

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
    startedRef.current = false;
    setPhase('idle');
    setError(null);
    // Trigger restart by setting startedRef to false and re-opening effect
    setTimeout(() => {
      startedRef.current = false;
      setPhase('starting');

      const startServer = async () => {
        try {
          const result = await api.mcp.startServer();

          if (!result.success) {
            setPhase('error');
            setError(result.message || 'Failed to start MCP server');
            return;
          }

          setPhase('running');

          const startTime = Date.now();
          const timeout = 30000;

          while (Date.now() - startTime < timeout) {
            if (await checkMcpHealth()) {
              setPhase('ready');
              return;
            }
            await new Promise(r => setTimeout(r, 1000));
          }

          setPhase('error');
          setError('MCP server did not become healthy within 30 seconds');
        } catch (err) {
          setPhase('error');
          setError(err instanceof Error ? err.message : 'Failed to start MCP server');
        }
      };

      startServer();
    }, 100);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] max-h-[70vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {phase === 'ready' ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : phase === 'error' ? (
              <XCircle className="h-5 w-5 text-red-500" />
            ) : (
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
            )}
            {phase === 'ready'
              ? 'MCP Server Ready!'
              : phase === 'error'
                ? 'Startup Failed'
                : 'Starting MCP Server...'}
          </DialogTitle>
          <DialogDescription>
            {phase === 'ready'
              ? 'The MCP server is running and ready for connections.'
              : phase === 'error'
                ? 'Failed to start the MCP server. Check logs for details.'
                : 'Please wait while the MCP server starts up.'}
          </DialogDescription>
        </DialogHeader>

        {/* Phase indicator */}
        <div className="flex items-center justify-center py-4">
          <div className="flex items-center gap-4">
            <div className={cn(
              'h-12 w-12 rounded-full flex items-center justify-center transition-colors',
              phase === 'ready' ? 'bg-green-500 text-white' :
              phase === 'error' ? 'bg-red-500 text-white' :
              'bg-blue-500 text-white'
            )}>
              {phase === 'ready' ? (
                <CheckCircle2 className="h-6 w-6" />
              ) : phase === 'error' ? (
                <XCircle className="h-6 w-6" />
              ) : (
                <Server className="h-6 w-6 animate-pulse" />
              )}
            </div>
            <div>
              <p className="font-medium">
                {phase === 'starting' && 'Initializing...'}
                {phase === 'running' && 'Waiting for health check...'}
                {phase === 'ready' && 'Server is healthy!'}
                {phase === 'error' && 'Server failed to start'}
              </p>
              <p className="text-sm text-muted-foreground">
                {phase === 'starting' && 'Spawning MCP server process'}
                {phase === 'running' && 'Checking if server is responding'}
                {phase === 'ready' && 'Ready to accept connections'}
                {phase === 'error' && 'See logs below for details'}
              </p>
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-500">Error</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        )}

        {/* Success message */}
        {phase === 'ready' && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-500">MCP Server Running!</p>
              <p className="text-sm text-muted-foreground">
                Server is ready on port 28882. Closing this dialog...
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
          {connectionError && <span className="text-red-500">{connectionError}</span>}
        </div>

        {/* Log viewer */}
        <div
          ref={logContainerRef}
          className="flex-1 min-h-[150px] max-h-[200px] overflow-y-auto bg-muted/50 rounded-lg p-3 font-mono text-xs space-y-0.5"
        >
          {relevantLogs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Waiting for MCP logs...
            </div>
          ) : (
            <LogList logs={relevantLogs} />
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          <Button variant="outline" size="sm" onClick={handleCopyLogs} disabled={relevantLogs.length === 0}>
            <Copy className="h-4 w-4 mr-1" />
            {copiedLogs ? 'Copied!' : 'Copy Logs'}
          </Button>

          <div className="flex gap-2">
            {phase === 'error' && (
              <Button variant="default" size="sm" onClick={handleRetry} className="bg-blue-500 hover:bg-blue-600">
                <RefreshCw className="h-4 w-4 mr-1" />
                Retry
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
              {phase === 'ready' ? 'Close' : 'Cancel'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
