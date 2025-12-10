import { useEffect, useRef, useMemo, useState, useCallback, memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
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
  MessageCircle,
  Play,
  QrCode,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LogEntry } from '@/lib';

// Configuration phases
type Phase = 'checking' | 'stopped' | 'starting' | 'ready' | 'qr' | 'connected' | 'error';

interface PhaseInfo {
  label: string;
  description: string;
}

const PHASES: Record<Phase, PhaseInfo> = {
  checking: { label: 'Checking', description: 'Checking service status' },
  stopped: { label: 'Stopped', description: 'Service not running' },
  starting: { label: 'Starting', description: 'Starting service' },
  ready: { label: 'Ready', description: 'Service ready' },
  qr: { label: 'QR Code', description: 'Scan QR code' },
  connected: { label: 'Connected', description: 'WhatsApp connected' },
  error: { label: 'Error', description: 'Configuration failed' },
};

const PHASE_ORDER: Phase[] = ['checking', 'starting', 'ready', 'qr', 'connected'];

interface WhatsAppConfigModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instanceName: string;
  onSuccess?: () => void;
  onInstanceCreated?: (instanceName: string) => void;
}

// Detect current phase from log messages
function detectPhase(logs: LogEntry[]): 'starting' | 'ready' | 'error' | null {
  if (logs.length === 0) return null;

  const recentLogs = logs.slice(-10);

  for (let i = recentLogs.length - 1; i >= 0; i--) {
    const msg = recentLogs[i].message.toLowerCase();
    const level = recentLogs[i].level;

    if (level === 'error' || msg.includes('error') || msg.includes('failed') || msg.includes('econnrefused')) {
      return 'error';
    }

    if (
      msg.includes('ready') ||
      msg.includes('running on port') ||
      msg.includes('started successfully') ||
      msg.includes('listening on')
    ) {
      return 'ready';
    }
  }

  return 'starting';
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

export function WhatsAppConfigModal({
  open,
  onOpenChange,
  instanceName,
  onSuccess,
  onInstanceCreated,
}: WhatsAppConfigModalProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [copiedLogs, setCopiedLogs] = useState(false);
  const [phase, setPhase] = useState<Phase>('checking');
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isCreatingInstance, setIsCreatingInstance] = useState(false);
  const [instanceCreated, setInstanceCreated] = useState(false);
  const [qrCodeFromConfig, setQrCodeFromConfig] = useState<string | null>(null);
  const [qrPollReady, setQrPollReady] = useState(false);
  const [instanceReady, setInstanceReady] = useState(false);
  const statusProbeCancelRef = useRef<{ cancelled: boolean } | null>(null);
  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const {
    logs,
    isConnected: logsConnected,
    connect: connectLogs,
    clearLogs,
  } = useLogStream({
    services: ['evolution'],
    autoConnect: false,
    maxLogs: 200,
  });

  const evolutionLogs = useMemo(() => logs.filter((l) => l.service === 'evolution'), [logs]);

  // Check Evolution service status
  const { data: gatewayStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['gateway-status-modal'],
    queryFn: () => api.gateway.getStatus(),
    enabled: open,
    refetchInterval: phase === 'starting' ? 2000 : false,
  });

  // Check QR code when instance exists (only after instance is created)
  const { data: qrData, refetch: refetchQR } = useQuery({
    queryKey: ['qr-code-modal', instanceName],
    queryFn: async () => {
      try {
        return await api.instances.getQR(instanceName);
      } catch (err) {
        // 404 during startup is expected; swallow to let retry/backoff continue
        return null;
      }
    },
    enabled:
      open &&
      instanceCreated &&
      instanceReady &&
      phase === 'qr' &&
      qrPollReady &&
      gatewayStatus?.processes?.evolution?.healthy &&
      !(connectionState?.connected || connectionState?.status?.toLowerCase() === 'connected'),
    refetchInterval: phase === 'qr' ? 5000 : false,
    retry: 5,
    retryDelay: 1500,
  });

  // Check connection status (only after instance is created)
  const { data: connectionState } = useQuery({
    queryKey: ['connection-state-modal', instanceName],
    queryFn: () => api.instances.getStatus(instanceName),
    enabled: open && instanceCreated && instanceReady && phase === 'qr' && gatewayStatus?.processes?.evolution?.healthy,
    refetchInterval: phase === 'qr' ? 2000 : false,
    retry: 5,
    retryDelay: 1500,
  });

  // Create instance after service is ready
  const createInstance = useCallback(async () => {
    if (instanceCreated || isCreatingInstance) return;

    setIsCreatingInstance(true);
    try {
      const result = await api.setup.configureChannels({
        whatsapp_enabled: true,
        discord_enabled: false,
        whatsapp_instance_name: instanceName,
      });

      if (result.whatsapp_qr_code) {
        setQrCodeFromConfig(result.whatsapp_qr_code);
        setInstanceCreated(true);
        setInstanceReady(false);
        setQrPollReady(false);
        setTimeout(() => {
          setInstanceReady(true);
          setQrPollReady(true);
        }, 3000);
        setPhase('qr');
        onInstanceCreated?.(instanceName);
      } else if (result.whatsapp_instance_name) {
        // Instance created but no QR (maybe already connected)
        setInstanceCreated(true);
        setInstanceReady(false);
        setQrPollReady(false);
        setTimeout(() => {
          setInstanceReady(true);
          setQrPollReady(true);
        }, 3000);
        setPhase('qr');
        onInstanceCreated?.(instanceName);
      } else {
        throw new Error('Failed to create WhatsApp instance');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create instance');
      setPhase('error');
    } finally {
      setIsCreatingInstance(false);
    }
  }, [instanceCreated, isCreatingInstance, instanceName, onInstanceCreated]);

  // Update phase based on service status
  useEffect(() => {
    if (!open) return;

    const evolutionProc = gatewayStatus?.processes?.evolution;

    if (phase === 'checking') {
      if (evolutionProc?.healthy) {
        // Service is ready, create instance
        setPhase('ready');
      } else {
        setPhase('stopped');
      }
    } else if (phase === 'starting' && evolutionProc?.healthy) {
      // Service started, create instance
      setPhase('ready');
    }
  }, [gatewayStatus, phase, open]);

  // When phase becomes 'ready', create instance automatically
  useEffect(() => {
    if (phase === 'ready' && !instanceCreated && !isCreatingInstance) {
      createInstance();
    }
  }, [phase, instanceCreated, isCreatingInstance, createInstance]);

  // Check for connection success
  useEffect(() => {
    const logIndicatesConnected = evolutionLogs.some((log) => /connected to whatsapp/i.test(log.message ?? ''));

    const isConnected =
      logIndicatesConnected ||
      connectionState?.connected === true ||
      connectionState?.status?.toLowerCase() === 'connected' ||
      connectionState?.state?.toLowerCase() === 'open';

    if (phase === 'qr' && isConnected) {
      setPhase('connected');
    }
  }, [phase, connectionState, evolutionLogs]);
  // Arm QR polling only after the instance status endpoint responds (prevents early 404s)
  useEffect(() => {
    if (open && instanceCreated && instanceReady && phase === 'qr' && gatewayStatus?.processes?.evolution?.healthy) {
      // Cancel any in-flight probe
      if (statusProbeCancelRef.current) {
        statusProbeCancelRef.current.cancelled = true;
      }

      const cancelRef = { cancelled: false };
      statusProbeCancelRef.current = cancelRef;
      setQrPollReady(false);

      const probe = async () => {
        for (let attempt = 0; attempt < 10; attempt++) {
          if (cancelRef.cancelled) return;
          try {
            await api.instances.getStatus(instanceName);
            if (!cancelRef.cancelled) {
              setQrPollReady(true);
            }
            return;
          } catch {
            await new Promise((r) => setTimeout(r, 800));
          }
        }
        // Fallback: allow polling even if status never responded, to avoid a stuck button
        if (!cancelRef.cancelled) {
          setQrPollReady(true);
        }
      };

      probe();

      return () => {
        cancelRef.cancelled = true;
      };
    }

    // If prerequisites are not satisfied, ensure polling stays disabled
    setQrPollReady(false);
    if (statusProbeCancelRef.current) {
      statusProbeCancelRef.current.cancelled = true;
    }
  }, [open, instanceCreated, instanceReady, phase, gatewayStatus?.processes?.evolution?.healthy, instanceName]);

  // Detect phase from logs during startup
  useEffect(() => {
    if (phase !== 'starting') return;

    const detectedPhase = detectPhase(evolutionLogs);
    if (detectedPhase === 'error') {
      setPhase('error');
      setError('Service startup failed. Check logs for details.');
    }
  }, [evolutionLogs, phase]);

  // Handle success state
  useEffect(() => {
    if (phase === 'connected' && onSuccess) {
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

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [evolutionLogs]);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setPhase('checking');
      setError(null);
      setIsStarting(false);
      setIsCreatingInstance(false);
      setInstanceCreated(false);
      setInstanceReady(false);
      setQrPollReady(false);
      setQrCodeFromConfig(null);
      clearLogs();
      refetchStatus();
    }
  }, [open, clearLogs, refetchStatus]);

  // Start Evolution service
  const handleStartService = useCallback(async () => {
    setIsStarting(true);
    setPhase('starting');
    setError(null);
    clearLogs();
    connectLogs();

    try {
      await api.gateway.startChannel('evolution');

      // Wait for service to be ready (up to 120 seconds)
      const ready = await api.gateway.waitForChannel('evolution', 120000);

      if (!ready) {
        throw new Error('Service failed to start within timeout');
      }

      // Wait for API to be responsive
      let apiReady = false;
      try {
        const { api_key } = await api.setup.getApiKey();
        for (let i = 0; i < 30; i++) {
          try {
            const res = await fetch('/evolution/instance/fetchInstances', {
              headers: { apikey: api_key },
            });
            if (res.status !== 502 && res.status !== 503 && res.status !== 504) {
              apiReady = true;
              break;
            }
          } catch {
            // ignore connection errors
          }
          await new Promise((r) => setTimeout(r, 1000));
        }
      } catch {
        apiReady = true; // optimistic fallthrough
      }

      if (!apiReady) {
        throw new Error('Service started but API is not responding');
      }

      setPhase('ready');
      refetchQR();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start service');
      setPhase('error');
    } finally {
      setIsStarting(false);
    }
  }, [clearLogs, connectLogs, refetchQR]);

  // Copy logs to clipboard
  const handleCopyLogs = async () => {
    const logText = evolutionLogs.map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`).join('\n');

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
    setPhase('checking');
    setError(null);
    clearLogs();
    refetchStatus();
  };

  // Get phase index for progress
  const getPhaseIndex = () => {
    if (phase === 'error') return -1;
    if (phase === 'stopped') return 0;
    return PHASE_ORDER.indexOf(phase);
  };

  const currentPhaseIndex = getPhaseIndex();

  // Determine what content to show
  const showLogs = phase === 'starting' || phase === 'error';
  const showCreatingInstance = phase === 'ready' && isCreatingInstance;
  // Use QR from configureChannels first, then fall back to query result
  const currentQrCode = qrCodeFromConfig || qrData?.qr_code;
  const showQR = phase === 'qr' && currentQrCode;
  const showStartPrompt = phase === 'stopped';
  const showChecking = phase === 'checking';
  const showConnected = phase === 'connected';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {phase === 'connected' ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : phase === 'error' ? (
              <XCircle className="h-5 w-5 text-red-500" />
            ) : phase === 'qr' ? (
              <QrCode className="h-5 w-5 text-[#25D366]" />
            ) : (
              <MessageCircle className="h-5 w-5 text-[#25D366]" />
            )}
            {phase === 'connected'
              ? 'WhatsApp Connected!'
              : phase === 'error'
                ? 'Configuration Failed'
                : phase === 'qr'
                  ? 'Scan QR Code'
                  : phase === 'starting'
                    ? 'Starting WhatsApp Service...'
                    : phase === 'stopped'
                      ? 'WhatsApp Setup'
                      : 'Checking WhatsApp Service...'}
          </DialogTitle>
        </DialogHeader>

        {/* Phase Progress - show during active phases */}
        {!showChecking && !showStartPrompt && (
          <div className="flex items-center justify-between px-2 py-3">
            {PHASE_ORDER.slice(1).map((p, index) => {
              const adjustedIndex = index + 1;
              const isComplete = currentPhaseIndex > adjustedIndex;
              const isCurrent = phase === p || (phase === 'stopped' && p === 'starting');
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
                            ? 'bg-[#25D366] text-white'
                            : isError && adjustedIndex <= 1
                              ? 'bg-red-500 text-white'
                              : 'bg-muted text-muted-foreground',
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
                    <span className="text-xs mt-1 text-muted-foreground">{PHASES[p].label}</span>
                  </div>

                  {index < PHASE_ORDER.length - 2 && (
                    <div className={cn('h-0.5 w-8 mx-1 transition-colors', isComplete ? 'bg-green-500' : 'bg-muted')} />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-500">Configuration Failed</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        )}

        {/* Success message */}
        {showConnected && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-500">WhatsApp Connected!</p>
              <p className="text-sm text-muted-foreground">Your WhatsApp is now connected and ready to use.</p>
            </div>
          </div>
        )}

        {/* Checking state */}
        {showChecking && (
          <div className="flex-1 min-h-[200px] flex flex-col items-center justify-center bg-muted/50 rounded-lg p-6 space-y-4">
            <Loader2 className="h-12 w-12 text-[#25D366] animate-spin" />
            <div className="text-center space-y-2">
              <h3 className="font-medium">Checking WhatsApp Service</h3>
              <p className="text-sm text-muted-foreground">Please wait while we check the service status...</p>
            </div>
          </div>
        )}

        {/* Start prompt */}
        {showStartPrompt && (
          <div className="flex-1 min-h-[200px] flex flex-col items-center justify-center bg-muted/50 rounded-lg p-6 space-y-4">
            <MessageCircle className="h-12 w-12 text-[#25D366]" />
            <div className="text-center space-y-2">
              <h3 className="font-medium">Start WhatsApp Service</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                The WhatsApp service needs to be started before you can connect. Click the button below to start the
                service.
              </p>
            </div>
            <Button onClick={handleStartService} disabled={isStarting} className="bg-[#25D366] hover:bg-[#1da851]">
              {isStarting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start WhatsApp Service
                </>
              )}
            </Button>
          </div>
        )}

        {/* Creating instance state */}
        {showCreatingInstance && (
          <div className="flex-1 min-h-[200px] flex flex-col items-center justify-center bg-muted/50 rounded-lg p-6 space-y-4">
            <Loader2 className="h-12 w-12 text-[#25D366] animate-spin" />
            <div className="text-center space-y-2">
              <h3 className="font-medium">Creating WhatsApp Instance</h3>
              <p className="text-sm text-muted-foreground">Setting up your WhatsApp connection...</p>
            </div>
          </div>
        )}

        {/* QR Code display */}
        {showQR && (
          <div className="flex flex-col items-center gap-4 p-4 bg-muted/50 rounded-lg">
            <img src={currentQrCode} alt="QR Code" className="w-48 h-48 rounded-lg border bg-white" />
            <p className="text-sm text-muted-foreground text-center max-w-sm">
              Open WhatsApp on your phone, go to <strong>Settings → Linked Devices → Link a Device</strong> and scan
              this QR code.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  // Force Evolution to restart instance to issue a fresh QR quickly
                  await api.instances.restart(instanceName);
                } catch (err) {
                  // Ignore restart errors; still try to refetch QR
                } finally {
                  setQrCodeFromConfig(null);
                  setQrPollReady(false);
                  // Give Evolution a moment to re-emit a QR
                  setTimeout(() => {
                    refetchQR();
                    setQrPollReady(true);
                  }, 1500);
                }
              }}
              disabled={!qrPollReady || !instanceReady}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh QR Code
            </Button>
          </div>
        )}

        {/* Log viewer - show during startup or error */}
        {showLogs && (
          <>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Terminal className="h-3 w-3" />
              <span>Live Logs</span>
              <Badge variant={logsConnected ? 'default' : 'secondary'} className="text-xs h-5">
                {logsConnected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>

            <div
              ref={logContainerRef}
              className="flex-1 min-h-[150px] max-h-[200px] overflow-y-auto bg-muted/50 rounded-lg p-3 font-mono text-xs space-y-0.5"
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
          </>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-2">
          {showLogs ? (
            <Button variant="outline" size="sm" onClick={handleCopyLogs} disabled={evolutionLogs.length === 0}>
              <Copy className="h-4 w-4 mr-1" />
              {copiedLogs ? 'Copied!' : 'Copy Logs'}
            </Button>
          ) : (
            <div />
          )}

          <div className="flex gap-2">
            {phase === 'error' && (
              <Button variant="default" size="sm" onClick={handleRetry} className="bg-[#25D366] hover:bg-[#1da851]">
                <RefreshCw className="h-4 w-4 mr-1" />
                Retry
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
              {phase === 'connected' ? 'Continue' : 'Cancel'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
