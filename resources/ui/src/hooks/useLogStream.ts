import { useState, useEffect, useCallback, useRef } from 'react';
import { api, type LogEntry, type LogServiceName, type LogService } from '@/lib';

interface UseLogStreamOptions {
  services?: LogServiceName[];
  maxLogs?: number;
  autoConnect?: boolean;
}

interface UseLogStreamReturn {
  logs: LogEntry[];
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  services: LogService[];
  selectedServices: LogServiceName[];
  setSelectedServices: (services: LogServiceName[]) => void;
  connect: () => void;
  disconnect: () => void;
  clearLogs: () => void;
  isPaused: boolean;
  togglePause: () => void;
}

export function useLogStream(options: UseLogStreamOptions = {}): UseLogStreamReturn {
  const { services: initialServices, maxLogs = 500, autoConnect = true } = options;

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [availableServices, setAvailableServices] = useState<LogService[]>([]);
  const [selectedServices, setSelectedServices] = useState<LogServiceName[]>(
    initialServices ?? ['api', 'discord', 'evolution', 'gateway'],
  );
  const [isPaused, setIsPaused] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pausedRef = useRef(false);

  // Keep pausedRef in sync
  useEffect(() => {
    pausedRef.current = isPaused;
  }, [isPaused]);

  // Fetch available services on mount
  useEffect(() => {
    api.logs.getServices().then(setAvailableServices);
  }, []);

  const addLog = useCallback(
    (entry: LogEntry) => {
      if (pausedRef.current) return;

      setLogs((prev) => {
        const newLogs = [...prev, entry];
        // Trim to max size
        if (newLogs.length > maxLogs) {
          return newLogs.slice(-maxLogs);
        }
        return newLogs;
      });
    },
    [maxLogs],
  );

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
    setIsConnecting(false);
  }, []);

  const connect = useCallback(async () => {
    // Disconnect any existing connection
    disconnect();

    setIsConnecting(true);
    setError(null);

    try {
      // First, load recent logs
      const recentLogs = await api.logs.getRecent({
        services: selectedServices,
        limit: 100,
      });
      setLogs(recentLogs);

      // Then establish SSE connection
      const eventSource = api.logs.createStream(selectedServices);
      eventSourceRef.current = eventSource;

      eventSource.addEventListener('connected', (event) => {
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        console.log('[LogStream] Connected:', JSON.parse(event.data));
      });

      eventSource.addEventListener('log', (event) => {
        try {
          const entry: LogEntry = JSON.parse(event.data);
          addLog(entry);
        } catch (e) {
          console.error('[LogStream] Failed to parse log entry:', e);
        }
      });

      eventSource.onerror = () => {
        setIsConnected(false);
        setIsConnecting(false);

        // Only reconnect if we haven't disconnected intentionally
        if (eventSourceRef.current) {
          setError('Connection lost. Reconnecting...');

          // Attempt reconnect after 3 seconds
          reconnectTimeoutRef.current = window.setTimeout(() => {
            if (eventSourceRef.current) {
              connect();
            }
          }, 3000);
        }
      };
    } catch (e) {
      setIsConnecting(false);
      setError(e instanceof Error ? e.message : 'Failed to connect');
    }
  }, [selectedServices, disconnect, addLog]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- connect/disconnect are stable via useCallback, only autoConnect should trigger
  }, [autoConnect]);

  // Reconnect when selected services change (if connected)
  useEffect(() => {
    if (isConnected || isConnecting) {
      connect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally only reconnect when selectedServices changes, connect is stable
  }, [selectedServices]);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  const togglePause = useCallback(() => {
    setIsPaused((prev) => !prev);
  }, []);

  return {
    logs,
    isConnected,
    isConnecting,
    error,
    services: availableServices,
    selectedServices,
    setSelectedServices,
    connect,
    disconnect,
    clearLogs,
    isPaused,
    togglePause,
  };
}
