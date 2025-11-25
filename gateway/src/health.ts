/**
 * Health Check Aggregator for Automagik Omni Gateway
 * Collects health status from all backend services
 */

export interface GatewayStats {
  memory: {
    heapUsed: number;  // MB
    heapTotal: number; // MB
    rss: number;       // MB
  };
  uptime: number;      // seconds
  nodeVersion: string;
  pid: number;
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

export interface AggregatedHealth {
  status: 'up' | 'down' | 'degraded';
  timestamp: string;
  services: {
    gateway: ServiceHealth;
    python: ServiceHealth;
    evolution: ServiceHealth;
    ui?: ServiceHealth;
  };
}

export interface HealthConfig {
  pythonUrl: string;
  evolutionUrl: string;
  viteUrl?: string;
  timeout: number;
}

export class HealthChecker {
  private config: HealthConfig;
  private evolutionApiKey: string;

  constructor(config: Partial<HealthConfig> = {}) {
    const pythonPort = process.env.PYTHON_API_PORT ?? '8881';
    const evolutionPort = process.env.EVOLUTION_PORT ?? '18082';
    const vitePort = process.env.VITE_PORT ?? '9882';

    this.config = {
      pythonUrl: config.pythonUrl ?? `http://127.0.0.1:${pythonPort}/health`,
      evolutionUrl: config.evolutionUrl ?? `http://127.0.0.1:${evolutionPort}/`,
      viteUrl: process.env.NODE_ENV === 'development'
        ? (config.viteUrl ?? `http://127.0.0.1:${vitePort}/`)
        : undefined,
      timeout: config.timeout ?? 5000,
    };

    this.evolutionApiKey = process.env.EVOLUTION_API_KEY ?? '';
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
    };
  }

  /**
   * Fetch Evolution instance statistics
   */
  private async getEvolutionInstances(): Promise<{
    instances: EvolutionInstanceStats;
    totals: EvolutionTotals;
    details: EvolutionInstanceDetail[];
  } | null> {
    const evolutionPort = process.env.EVOLUTION_PORT ?? '18082';
    const url = `http://127.0.0.1:${evolutionPort}/instance/fetchInstances`;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

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
   * Check health of a single service
   */
  private async checkService(url: string): Promise<ServiceHealth> {
    const start = Date.now();

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

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
    const [pythonHealth, evolutionHealth, uiHealth, evolutionInstances] = await Promise.all([
      this.checkService(this.config.pythonUrl),
      this.checkService(this.config.evolutionUrl),
      this.config.viteUrl ? this.checkService(this.config.viteUrl) : Promise.resolve(undefined),
      this.getEvolutionInstances(),
    ]);

    // Gateway stats
    const gatewayStats = this.getGatewayStats();
    const gatewayHealth: ServiceHealth = {
      status: 'up',
      latency: 0,
      details: gatewayStats,
    };

    // Enrich Evolution health with instance stats and details
    if (evolutionHealth.status === 'up' && evolutionInstances) {
      evolutionHealth.details = {
        ...evolutionHealth.details,
        instances: evolutionInstances.instances,
        totals: evolutionInstances.totals,
        instanceDetails: evolutionInstances.details,
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
