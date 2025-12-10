/**
 * Log Tailing Module for Automagik Omni Gateway
 * Provides real-time log streaming via SSE from PM2 log files
 */

import { EventEmitter } from 'events';
import { existsSync } from 'fs';
import { open, readFile, stat } from 'fs/promises';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '../..');
const LOGS_DIR = join(ROOT_DIR, 'logs');

// Log service configuration
export const LOG_SERVICES = {
  api: {
    name: 'Python API',
    file: 'api-combined.log',
    color: '#3b82f6', // blue
  },
  discord: {
    name: 'Discord',
    file: 'discord-combined.log',
    color: '#8b5cf6', // purple
  },
  evolution: {
    name: 'Evolution',
    file: 'evolution-combined.log',
    color: '#22c55e', // green
  },
  gateway: {
    name: 'Gateway',
    file: 'gateway-combined.log',
    color: '#f59e0b', // amber
  },
} as const;

export type ServiceName = keyof typeof LOG_SERVICES;

export interface LogEntry {
  timestamp: string;
  service: ServiceName;
  level: 'debug' | 'info' | 'warn' | 'error' | 'unknown';
  message: string;
  raw: string;
}

// ANSI escape code regex
const ANSI_REGEX = /\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g;

/**
 * Strip ANSI escape codes from a string
 */
function stripAnsi(str: string): string {
  return str.replace(ANSI_REGEX, '');
}

/**
 * Parse log level from message content
 */
function parseLevel(message: string): LogEntry['level'] {
  const upperMsg = message.toUpperCase();
  if (upperMsg.includes('ERROR') || upperMsg.includes('❌')) return 'error';
  if (upperMsg.includes('WARN') || upperMsg.includes('⚠️')) return 'warn';
  if (upperMsg.includes('DEBUG')) return 'debug';
  if (upperMsg.includes('INFO') || upperMsg.includes('✓') || upperMsg.includes('✅')) return 'info';
  return 'unknown';
}

/**
 * Parse a log line into a structured LogEntry
 * Handles multiple formats:
 * - PM2: "2025-11-19T15:32:37: <content>"
 * - Python: "✓ 15:32:37 -03 - [36mlogger[0m - [92mINFO[0m - message"
 * - Evolution: "[Evolution API] 90522 - Wed Nov 19 2025 16:03:57 WARN [Service] message"
 */
function parseLogLine(line: string, service: ServiceName): LogEntry | null {
  if (!line.trim()) return null;

  // Strip ANSI codes first
  const cleanLine = stripAnsi(line);

  // Try to extract PM2 timestamp prefix (ISO format)
  const pm2Match = cleanLine.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}):\s*(.*)$/);

  let timestamp: string;
  let content: string;

  if (pm2Match) {
    timestamp = pm2Match[1];
    content = pm2Match[2];
  } else {
    // No PM2 timestamp, use current time
    timestamp = new Date().toISOString().slice(0, 19);
    content = cleanLine;
  }

  // Skip empty content after stripping
  if (!content.trim()) return null;

  // Detect level from content
  const level = parseLevel(content);

  return {
    timestamp,
    service,
    level,
    message: content.trim(),
    raw: line,
  };
}

/**
 * LogTailer class - watches log files and emits parsed entries
 */
export class LogTailer extends EventEmitter {
  private watchers = new Map<ServiceName, AbortController>();
  private positions = new Map<ServiceName, number>();
  private buffer: LogEntry[] = [];
  private maxBufferSize: number;
  private activeServices = new Set<ServiceName>();
  private listenerCounts = new Map<ServiceName, number>();

  constructor(maxBufferSize = 500) {
    super();
    // FIX 13: Increase max listeners to prevent warning during heavy SSE usage
    this.setMaxListeners(50);
    this.maxBufferSize = maxBufferSize;
  }

  /**
   * Increment listener count for a service (for SSE reference counting)
   */
  incrementListeners(service: ServiceName): void {
    this.listenerCounts.set(service, (this.listenerCounts.get(service) ?? 0) + 1);
  }

  /**
   * Decrement listener count and stop tailing if no listeners remain
   */
  decrementListeners(service: ServiceName): void {
    const count = (this.listenerCounts.get(service) ?? 1) - 1;
    if (count <= 0) {
      this.listenerCounts.delete(service);
      this.stopTailing(service);
    } else {
      this.listenerCounts.set(service, count);
    }
  }

  /**
   * Get current listener count for a service
   */
  getListenerCount(service: ServiceName): number {
    return this.listenerCounts.get(service) ?? 0;
  }

  /**
   * Get the path to a service's log file
   */
  private getLogPath(service: ServiceName): string {
    return join(LOGS_DIR, LOG_SERVICES[service].file);
  }

  /**
   * Read recent lines from a log file
   */
  async getRecentLogs(
    services: ServiceName[] = Object.keys(LOG_SERVICES) as ServiceName[],
    limit = 100,
  ): Promise<LogEntry[]> {
    const allEntries: LogEntry[] = [];

    await Promise.all(
      services.map(async (service) => {
        const logPath = this.getLogPath(service);
        if (!existsSync(logPath)) return;

        try {
          // Read last N lines efficiently
          const entries = await this.readLastLines(logPath, service, limit);
          allEntries.push(...entries);
        } catch (error) {
          console.warn(`[LogTailer] Failed to read ${service} logs:`, error);
        }
      }),
    );

    // Sort by timestamp and return limited results
    return allEntries.sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-limit);
  }

  /**
   * Read the last N lines from a file
   */
  private async readLastLines(filePath: string, service: ServiceName, limit: number): Promise<LogEntry[]> {
    const entries: LogEntry[] = [];

    try {
      const content = await readFile(filePath, 'utf-8');
      const lines = content.split('\n');
      const recentLines = lines.slice(-limit - 1); // +1 to account for potential empty last line

      for (const line of recentLines) {
        const entry = parseLogLine(line, service);
        if (entry) entries.push(entry);
      }
    } catch (error) {
      // File might not exist or be readable
    }

    return entries;
  }

  /**
   * Start tailing a log file
   */
  async startTailing(service: ServiceName): Promise<void> {
    if (this.watchers.has(service)) return;

    const logPath = this.getLogPath(service);

    // Get initial file position (end of file)
    try {
      const stats = await stat(logPath);
      this.positions.set(service, stats.size);
    } catch {
      this.positions.set(service, 0);
    }

    this.activeServices.add(service);

    // Start watching for changes
    const abortController = new AbortController();
    this.watchers.set(service, abortController);

    this.watchFile(service, logPath, abortController.signal);
  }

  /**
   * Watch a file for changes and emit new lines
   */
  private async watchFile(service: ServiceName, logPath: string, signal: AbortSignal): Promise<void> {
    // Use polling fallback for better reliability
    const pollInterval = 500; // ms

    const poll = async () => {
      if (signal.aborted) return;

      try {
        const stats = await stat(logPath);
        const currentPos = this.positions.get(service) ?? 0;

        if (stats.size > currentPos) {
          // File has grown - read new content
          await this.readNewContent(service, logPath, currentPos, stats.size);
          this.positions.set(service, stats.size);
        } else if (stats.size < currentPos) {
          // File was truncated/rotated - start from beginning
          this.positions.set(service, 0);
          await this.readNewContent(service, logPath, 0, stats.size);
          this.positions.set(service, stats.size);
        }
      } catch {
        // File doesn't exist or can't be read - reset position
        this.positions.set(service, 0);
      }

      if (!signal.aborted) {
        setTimeout(poll, pollInterval);
      }
    };

    // Start polling
    poll();
  }

  /**
   * Read new content from a file
   */
  private async readNewContent(service: ServiceName, logPath: string, start: number, end: number): Promise<void> {
    try {
      const fd = await open(logPath, 'r');
      const buffer = Buffer.alloc(end - start);
      await fd.read(buffer, 0, end - start, start);
      await fd.close();

      const content = buffer.toString('utf-8');
      const lines = content.split('\n');

      for (const line of lines) {
        const entry = parseLogLine(line, service);
        if (entry) {
          this.addToBuffer(entry);
          this.emit('log', entry);
        }
      }
    } catch (error) {
      console.warn(`[LogTailer] Error reading ${service}:`, error);
    }
  }

  /**
   * Add entry to internal buffer (for late joiners)
   */
  private addToBuffer(entry: LogEntry): void {
    this.buffer.push(entry);
    if (this.buffer.length > this.maxBufferSize) {
      this.buffer.shift();
    }
  }

  /**
   * Get buffered logs
   */
  getBuffer(): LogEntry[] {
    return [...this.buffer];
  }

  /**
   * Stop tailing a specific service
   */
  stopTailing(service: ServiceName): void {
    const controller = this.watchers.get(service);
    if (controller) {
      controller.abort();
      this.watchers.delete(service);
      this.activeServices.delete(service);
    }
  }

  /**
   * Stop tailing all services
   */
  stopAll(): void {
    for (const service of this.watchers.keys()) {
      this.stopTailing(service);
    }
  }

  /**
   * Get list of active services being tailed
   */
  getActiveServices(): ServiceName[] {
    return Array.from(this.activeServices);
  }

  /**
   * Check if a service is being tailed
   */
  isTailing(service: ServiceName): boolean {
    return this.activeServices.has(service);
  }
}

// Singleton instance for sharing across routes
let tailerInstance: LogTailer | null = null;

export function getLogTailer(): LogTailer {
  if (!tailerInstance) {
    tailerInstance = new LogTailer(500);
  }
  return tailerInstance;
}

/**
 * Get available log services
 */
export function getAvailableServices(): { id: ServiceName; name: string; color: string; available: boolean }[] {
  return (Object.keys(LOG_SERVICES) as ServiceName[]).map((id) => ({
    id,
    name: LOG_SERVICES[id].name,
    color: LOG_SERVICES[id].color,
    available: existsSync(join(LOGS_DIR, LOG_SERVICES[id].file)),
  }));
}

// PM2 process name mapping for restart functionality
const PM2_PROCESS_NAMES: Record<ServiceName, string[]> = {
  api: ['Omni Backend - API', 'omni-api'],
  discord: ['Omni Backend - Discord', 'omni-discord'],
  evolution: ['Evolution API', 'Omni-Evolution-API'],
  gateway: ['Omni Gateway', '8882: Omni-Gateway'],
};

/**
 * Restart a PM2 service by name
 * Uses execFile for safety (avoids shell command injection)
 */
export async function restartPm2Service(service: ServiceName): Promise<{ success: boolean; message: string }> {
  const processNames = PM2_PROCESS_NAMES[service];
  if (!processNames || processNames.length === 0) {
    return { success: false, message: `Unknown service: ${service}` };
  }

  const { execFile } = await import('child_process');
  const { promisify } = await import('util');
  const execFileAsync = promisify(execFile);

  // Try each possible PM2 process name
  for (const processName of processNames) {
    try {
      const { stdout, stderr } = await execFileAsync('pm2', ['restart', processName], { timeout: 30000 });
      const output = stdout || stderr;

      // Check if restart was successful
      if (output.includes('restarted') || output.includes('Applying action restartProcessId')) {
        return {
          success: true,
          message: `Successfully restarted ${LOG_SERVICES[service].name} (${processName})`,
        };
      }
    } catch (error) {
      // Process name not found, try next one
      continue;
    }
  }

  return {
    success: false,
    message: `Could not find PM2 process for ${LOG_SERVICES[service].name}. Tried: ${processNames.join(', ')}`,
  };
}

/**
 * Get PM2 process status for a service
 * Uses execFile for safety (avoids shell command injection)
 */
export async function getPm2Status(service: ServiceName): Promise<{
  online: boolean;
  pm2_id?: number;
  name?: string;
  pid?: number;
  uptime?: number;
  restarts?: number;
  memory?: number;
  cpu?: number;
} | null> {
  const processNames = PM2_PROCESS_NAMES[service];
  if (!processNames || processNames.length === 0) return null;

  const { execFile } = await import('child_process');
  const { promisify } = await import('util');
  const execFileAsync = promisify(execFile);

  try {
    const { stdout } = await execFileAsync('pm2', ['jlist']);
    const processes = JSON.parse(stdout) as Array<{
      pm_id: number;
      name: string;
      pid: number;
      pm2_env: {
        status: string;
        pm_uptime: number;
        restart_time: number;
      };
      monit: {
        memory: number;
        cpu: number;
      };
    }>;

    // Find matching process
    for (const proc of processes) {
      if (processNames.some((name) => proc.name.includes(name) || name.includes(proc.name))) {
        return {
          online: proc.pm2_env.status === 'online',
          pm2_id: proc.pm_id,
          name: proc.name,
          pid: proc.pid,
          uptime: proc.pm2_env.pm_uptime ? Math.floor((Date.now() - proc.pm2_env.pm_uptime) / 1000) : undefined,
          restarts: proc.pm2_env.restart_time,
          memory: proc.monit?.memory ? Math.round(proc.monit.memory / 1024 / 1024) : undefined,
          cpu: proc.monit?.cpu,
        };
      }
    }
  } catch {
    // PM2 not available or error
  }

  return null;
}
