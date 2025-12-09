/**
 * Health Check Aggregator for Automagik Omni Gateway
 * Collects health status from all backend services
 */

import { PortRegistry } from './port-registry.js';

export interface ProcessStats {
  memory: {
    heapUsed: number;  // MB
    heapTotal: number; // MB
    rss: number;       // MB
  };
  uptime: number;      // seconds
  nodeVersion: string;
  pid: number;
  cpu?: number;        // CPU percentage (if available)
}

export interface GatewayStats extends ProcessStats {}

export interface EvolutionProcessStats {
  pid?: number;
  memory_mb?: number;
  cpu_percent?: number;
  uptime?: number;
}

export interface EvolutionInstanceStats {
  total: number;
  connected: number;
  disconnected: number;
}

export interface EvolutionTotals {
  messages: number;
  contacts: number;
  chats: number;
}

export interface EvolutionInstanceDetail {
  name: string;
  connectionStatus: 'open' | 'close' | 'connecting' | string;
  profileName?: string;
  profilePicUrl?: string;
  ownerJid?: string;
  integration?: string;
  createdAt?: string;
  updatedAt?: string;
  evolution_key?: string;  // Per-instance Evolution API authentication key from Omni DB
  counts: {
    messages: number;
    contacts: number;
    chats: number;
  };
  settings?: {
    rejectCall?: boolean;
    groupsIgnore?: boolean;
    alwaysOnline?: boolean;
    readMessages?: boolean;
    readStatus?: boolean;
    syncFullHistory?: boolean;
  };
  integrations?: {
    chatwoot?: boolean;
    rabbitmq?: boolean;
    websocket?: boolean;
  };
}

export interface ServiceHealth {
  status: 'up' | 'down' | 'degraded';
  latency?: number;
  details?: Record<string, unknown>;
}

export interface ServerStats {
  memory: {
    total: number;       // GB
    used: number;        // GB
    free: number;        // GB
    usedPercent: number; // %
  };
  cpu: {
    cores: number;
    model: string;
    usagePercent: number; // % (average across cores)
  };
  disk: {
    total: number;       // GB
    used: number;        // GB
    free: number;        // GB
    usedPercent: number; // %
    mountPoint: string;  // "/"
  };
  loadAverage: [number, number, number]; // 1, 5, 15 min
  uptime: number;        // seconds
  platform: string;      // "linux", "darwin", etc.
  hostname: string;
}

export interface AggregatedHealth {
  status: 'up' | 'down' | 'degraded';
  timestamp: string;
  server?: ServerStats;
  services: {
    gateway: ServiceHealth;
    python: ServiceHealth;
    evolution: ServiceHealth;
    ui?: ServiceHealth;
  };
}

export interface HealthConfig {
  timeout: number;
}

export class HealthChecker {
  private portRegistry: PortRegistry;
  private timeout: number;
  private rootDir: string;
  private evolutionApiKey: string;
  private omniApiKey: string = '';
  private lastCpuUsage: { user: number; system: number; time: number } | null = null;

  constructor(portRegistry: PortRegistry, rootDir: string, timeout = 5000) {
    this.portRegistry = portRegistry;
    this.rootDir = rootDir;
    this.timeout = timeout;
    this.evolutionApiKey = process.env.EVOLUTION_API_KEY ?? '';
  }

  /**
   * Fetch API key from Python API's internal endpoint (PostgreSQL-only architecture)
   */
  private async getApiKey(): Promise<string> {
    if (this.omniApiKey) return this.omniApiKey;

    const pythonPort = this.portRegistry.getPort('python');
    if (!pythonPort) return this.omniApiKey;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      const response = await fetch(`http://127.0.0.1:${pythonPort}/api/v1/_internal/evolution-key`, {
        method: 'GET',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json() as { key?: string };
        if (data.key) {
          this.omniApiKey = data.key;
        }
      }
    } catch {
      // Silent failure - will retry next time or fail auth
    }

    return this.omniApiKey;
  }

  /**
   * Calculate Gateway CPU usage percentage using process.cpuUsage()
   */
  private getGatewayCpuPercent(): number {
    const cpu = process.cpuUsage();
    const now = Date.now();

    if (!this.lastCpuUsage) {
      this.lastCpuUsage = { user: cpu.user, system: cpu.system, time: now };
      return 0;
    }

    const elapsedMs = now - this.lastCpuUsage.time;
    if (elapsedMs < 100) return 0; // Avoid division issues on rapid calls

    // cpuUsage returns microseconds, convert to milliseconds
    const userDelta = (cpu.user - this.lastCpuUsage.user) / 1000;
    const systemDelta = (cpu.system - this.lastCpuUsage.system) / 1000;
    const totalDelta = userDelta + systemDelta;

    // Update stored values
    this.lastCpuUsage = { user: cpu.user, system: cpu.system, time: now };

    // Calculate percentage (total CPU time / elapsed wall time)
    return Math.round((totalDelta / elapsedMs) * 100 * 10) / 10;
  }

  /**
   * Get the Python API health check URL
   */
  private getPythonUrl(): string | undefined {
    const port = this.portRegistry.getPort('python');
    return port ? `http://127.0.0.1:${port}/health` : undefined;
  }

  /**
   * Get the Evolution API URL
   */
  private getEvolutionUrl(): string | undefined {
    const port = this.portRegistry.getPort('evolution');
    return port ? `http://127.0.0.1:${port}/` : undefined;
  }

  /**
   * Get the Evolution API port
   */
  private getEvolutionPort(): number | undefined {
    return this.portRegistry.getPort('evolution');
  }

  /**
   * Get the Vite dev server URL
   */
  private getViteUrl(): string | undefined {
    const port = this.portRegistry.getPort('vite');
    return port ? `http://127.0.0.1:${port}/` : undefined;
  }

  /**
   * Get gateway process stats
   */
  private getGatewayStats(): GatewayStats {
    const mem = process.memoryUsage();
    return {
      memory: {
        heapUsed: Math.round(mem.heapUsed / 1024 / 1024 * 10) / 10,
        heapTotal: Math.round(mem.heapTotal / 1024 / 1024 * 10) / 10,
        rss: Math.round(mem.rss / 1024 / 1024 * 10) / 10,
      },
      uptime: Math.round(process.uptime()),
      nodeVersion: process.version,
      pid: process.pid,
      cpu: this.getGatewayCpuPercent(),
    };
  }

  /**
   * Get server-wide system stats
   */
  private async getServerStats(): Promise<ServerStats> {
    const os = await import('os');

    // Memory stats (convert bytes to GB)
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;

    // CPU info
    const cpus = os.cpus();
    const cpuModel = cpus[0]?.model || 'Unknown';

    // Calculate CPU usage from cpus() (average idle percentage)
    let totalIdle = 0;
    let totalTick = 0;
    for (const cpu of cpus) {
      for (const type in cpu.times) {
        totalTick += cpu.times[type as keyof typeof cpu.times];
      }
      totalIdle += cpu.times.idle;
    }
    const cpuUsage = totalTick > 0 ? 100 - (100 * totalIdle / totalTick) : 0;

    // Disk stats via df command (root partition only)
    let diskStats = { total: 0, used: 0, free: 0, usedPercent: 0, mountPoint: '/' };
    try {
      const proc = Bun.spawnSync(['sh', '-c', 'df -B1 / 2>/dev/null | tail -1'], {
        stdout: 'pipe',
        stderr: 'pipe',
      });
      const stdout = proc.stdout.toString();
      const parts = stdout.trim().split(/\s+/);
      // Format: Filesystem 1B-blocks Used Available Use% Mounted
      if (parts.length >= 4) {
        const total = parseInt(parts[1], 10);
        const used = parseInt(parts[2], 10);
        const free = parseInt(parts[3], 10);
        diskStats = {
          total: Math.round(total / 1024 / 1024 / 1024 * 10) / 10,
          used: Math.round(used / 1024 / 1024 / 1024 * 10) / 10,
          free: Math.round(free / 1024 / 1024 / 1024 * 10) / 10,
          usedPercent: total > 0 ? Math.round((used / total) * 100) : 0,
          mountPoint: '/',
        };
      }
    } catch {
      // Disk stats unavailable on this platform
    }

    return {
      memory: {
        total: Math.round(totalMem / 1024 / 1024 / 1024 * 10) / 10,
        used: Math.round(usedMem / 1024 / 1024 / 1024 * 10) / 10,
        free: Math.round(freeMem / 1024 / 1024 / 1024 * 10) / 10,
        usedPercent: totalMem > 0 ? Math.round((usedMem / totalMem) * 100) : 0,
      },
      cpu: {
        cores: cpus.length,
        model: cpuModel,
        usagePercent: Math.round(cpuUsage * 10) / 10,
      },
      disk: diskStats,
      loadAverage: os.loadavg().map(l => Math.round(l * 100) / 100) as [number, number, number],
      uptime: Math.round(os.uptime()),
      platform: os.platform(),
      hostname: os.hostname(),
    };
  }

  /**
   * Execute a shell command and return stdout
   */
  private async execCommand(command: string): Promise<string> {
    try {
      const proc = Bun.spawn(['sh', '-c', command], {
        stdout: 'pipe',
        stderr: 'pipe',
      });
      
      const text = await new Response(proc.stdout).text();
      await proc.exited;
      return text;
    } catch (error) {
      return '';
    }
  }

  /**
   * Get Evolution process stats by finding its PID and reading from /proc
   */
  private async getEvolutionProcessStats(): Promise<EvolutionProcessStats | null> {
    const evolutionPort = this.getEvolutionPort();
    if (!evolutionPort) return null;

    try {
      // Find Evolution process by looking for the port listener using Bun.spawnSync
      let pid: number | undefined;
      try {
        const proc = Bun.spawnSync(['sh', '-c', `ss -tlnp 2>/dev/null | grep ':${evolutionPort}' | grep -oP 'pid=\\K[0-9]+'`], {
          stdout: 'pipe',
          stderr: 'pipe',
        });
        pid = parseInt(proc.stdout.toString().trim(), 10);
      } catch {
        // Try alternative method with lsof
        try {
          const proc = Bun.spawnSync(['sh', '-c', `lsof -ti :${evolutionPort} 2>/dev/null | head -1`], {
            stdout: 'pipe',
            stderr: 'pipe',
          });
          pid = parseInt(proc.stdout.toString().trim(), 10);
        } catch {
          return null;
        }
      }

      if (!pid || isNaN(pid)) {
        return null;
      }

      // Read process stats from /proc
      const fs = await import('fs/promises');

      // Get memory from /proc/[pid]/status
      let memoryMb = 0;
      try {
        const status = await fs.readFile(`/proc/${pid}/status`, 'utf-8');
        const vmRssMatch = status.match(/VmRSS:\s*(\d+)\s*kB/);
        if (vmRssMatch) {
          memoryMb = Math.round(parseInt(vmRssMatch[1], 10) / 1024 * 10) / 10;
        }
      } catch {
        // Ignore read errors
      }

      // Get uptime by calculating from process start time
      let uptime = 0;
      try {
        // Get process start time in a parseable format
        const stdout = await this.execCommand(`ps -p ${pid} -o lstart= 2>/dev/null`);
        const startTime = new Date(stdout.trim());
        if (!isNaN(startTime.getTime())) {
          uptime = Math.round((Date.now() - startTime.getTime()) / 1000);
        }
      } catch {
        // Ignore errors
      }

      // Get CPU from /proc/[pid]/stat (simplified - instantaneous is tricky)
      let cpuPercent = 0;
      try {
        const stdout = await this.execCommand(`ps -p ${pid} -o %cpu --no-headers 2>/dev/null`);
        cpuPercent = parseFloat(stdout.trim()) || 0;
      } catch {
        // Ignore errors
      }

      return {
        pid,
        memory_mb: memoryMb,
        cpu_percent: Math.round(cpuPercent * 10) / 10,
        uptime,
      };
    } catch {
      return null;
    }
  }

  /**
   * Fetch Evolution instance statistics
   */
  private async getEvolutionInstances(): Promise<{
    instances: EvolutionInstanceStats;
    totals: EvolutionTotals;
    details: EvolutionInstanceDetail[];
  } | null> {
    const evolutionPort = this.getEvolutionPort();
    if (!evolutionPort) return null;
    const url = `http://127.0.0.1:${evolutionPort}/instance/fetchInstances`;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (this.evolutionApiKey) {
        headers['apikey'] = this.evolutionApiKey;
      }

      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return null;
      }

      interface EvolutionApiInstance {
        name?: string;
        connectionStatus?: string;
        profileName?: string;
        profilePicUrl?: string;
        ownerJid?: string;
        integration?: string;
        createdAt?: string;
        updatedAt?: string;
        _count?: {
          Message?: number;
          Contact?: number;
          Chat?: number;
        };
        Setting?: {
          rejectCall?: boolean;
          groupsIgnore?: boolean;
          alwaysOnline?: boolean;
          readMessages?: boolean;
          readStatus?: boolean;
          syncFullHistory?: boolean;
        };
        Chatwoot?: unknown;
        Rabbitmq?: unknown;
        Websocket?: unknown;
      }

      const data = await response.json() as EvolutionApiInstance[];

      if (!Array.isArray(data)) {
        return null;
      }

      const connected = data.filter(i => i.connectionStatus === 'open').length;
      const totals = data.reduce(
        (acc, instance) => {
          acc.messages += instance._count?.Message ?? 0;
          acc.contacts += instance._count?.Contact ?? 0;
          acc.chats += instance._count?.Chat ?? 0;
          return acc;
        },
        { messages: 0, contacts: 0, chats: 0 }
      );

      // Build detailed per-instance data
      const details: EvolutionInstanceDetail[] = data.map(instance => ({
        name: instance.name ?? 'unknown',
        connectionStatus: instance.connectionStatus ?? 'unknown',
        profileName: instance.profileName,
        profilePicUrl: instance.profilePicUrl,
        ownerJid: instance.ownerJid,
        integration: instance.integration,
        createdAt: instance.createdAt,
        updatedAt: instance.updatedAt,
        counts: {
          messages: instance._count?.Message ?? 0,
          contacts: instance._count?.Contact ?? 0,
          chats: instance._count?.Chat ?? 0,
        },
        settings: instance.Setting ? {
          rejectCall: instance.Setting.rejectCall,
          groupsIgnore: instance.Setting.groupsIgnore,
          alwaysOnline: instance.Setting.alwaysOnline,
          readMessages: instance.Setting.readMessages,
          readStatus: instance.Setting.readStatus,
          syncFullHistory: instance.Setting.syncFullHistory,
        } : undefined,
        integrations: {
          chatwoot: instance.Chatwoot != null,
          rabbitmq: instance.Rabbitmq != null,
          websocket: instance.Websocket != null,
        },
      }));

      return {
        instances: {
          total: data.length,
          connected,
          disconnected: data.length - connected,
        },
        totals,
        details,
      };
    } catch {
      return null;
    }
  }

  /**
   * Fetch instance evolution_key values from Omni Python API
   */
  private async getOmniInstanceKeys(): Promise<Map<string, string>> {
    const pythonPort = this.portRegistry.getPort('python');
    if (!pythonPort) return new Map();

    const apiKey = await this.getApiKey();
    if (!apiKey) return new Map();

    const url = `http://127.0.0.1:${pythonPort}/api/v1/instances`;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'x-api-key': apiKey,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return new Map();
      }

      interface OmniInstance {
        name: string;
        evolution_key?: string;
      }

      const instances = await response.json() as OmniInstance[];
      const keyMap = new Map<string, string>();

      for (const instance of instances) {
        if (instance.name && instance.evolution_key) {
          keyMap.set(instance.name, instance.evolution_key);
        }
      }

      return keyMap;
    } catch {
      return new Map();
    }
  }

  /**
   * Check health of a single service
   */
  private async checkService(url: string): Promise<ServiceHealth> {
    const start = Date.now();

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        method: 'GET',
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const latency = Date.now() - start;

      if (response.ok) {
        let details: Record<string, unknown> | undefined;
        try {
          const contentType = response.headers.get('content-type');
          if (contentType?.includes('application/json')) {
            details = await response.json() as Record<string, unknown>;
          }
        } catch {
          // Ignore JSON parse errors
        }

        return {
          status: 'up',
          latency,
          details,
        };
      }

      return {
        status: 'degraded',
        latency,
        details: { statusCode: response.status },
      };
    } catch (error) {
      return {
        status: 'down',
        latency: Date.now() - start,
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
      };
    }
  }

  /**
   * Get aggregated health status from all services
   */
  async getHealth(): Promise<AggregatedHealth> {
    const pythonUrl = this.getPythonUrl();
    const evolutionUrl = this.getEvolutionUrl();
    const viteUrl = this.getViteUrl();

    const [pythonHealth, evolutionHealth, uiHealth, evolutionInstances, evolutionProcess, serverStats, omniInstanceKeys] = await Promise.all([
      pythonUrl ? this.checkService(pythonUrl) : Promise.resolve({ status: 'down' as const, details: { error: 'Port not allocated' } }),
      evolutionUrl ? this.checkService(evolutionUrl) : Promise.resolve({ status: 'down' as const, details: { error: 'Port not allocated' } }),
      viteUrl ? this.checkService(viteUrl) : Promise.resolve(undefined),
      this.getEvolutionInstances(),
      this.getEvolutionProcessStats(),
      this.getServerStats(),
      this.getOmniInstanceKeys(),
    ]);

    // Gateway stats
    const gatewayStats = this.getGatewayStats();
    const gatewayHealth: ServiceHealth = {
      status: 'up',
      latency: 0,
      details: gatewayStats as unknown as Record<string, unknown>,
    };

    // Merge evolution_key from Omni API into Evolution instance details
    if (evolutionInstances && omniInstanceKeys.size > 0) {
      for (const detail of evolutionInstances.details) {
        const evolutionKey = omniInstanceKeys.get(detail.name);
        if (evolutionKey) {
          detail.evolution_key = evolutionKey;
        }
      }
    }

    // Enrich Evolution health with instance stats, details, and process stats
    if (evolutionHealth.status === 'up') {
      evolutionHealth.details = {
        ...evolutionHealth.details,
        ...(evolutionInstances ? {
          instances: evolutionInstances.instances,
          totals: evolutionInstances.totals,
          instanceDetails: evolutionInstances.details,
        } : {}),
        ...(evolutionProcess ? {
          process: evolutionProcess,
        } : {}),
      };
    }

    // Overall status: down if critical services are down, degraded if any non-critical is down
    let overallStatus: 'up' | 'down' | 'degraded' = 'up';

    // Python API is critical
    if (pythonHealth.status === 'down') {
      overallStatus = 'degraded';
    }

    // Evolution being down is okay for basic functionality
    if (evolutionHealth.status === 'down' && overallStatus === 'up') {
      overallStatus = 'up'; // Evolution is optional
    }

    const health: AggregatedHealth = {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      server: serverStats,
      services: {
        gateway: gatewayHealth,
        python: pythonHealth,
        evolution: evolutionHealth,
      },
    };

    if (uiHealth) {
      health.services.ui = uiHealth;
    }

    return health;
  }
}
