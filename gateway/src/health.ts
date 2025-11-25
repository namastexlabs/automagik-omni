/**
 * Health Check Aggregator for Automagik Omni Gateway
 * Collects health status from all backend services
 */

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
    const [pythonHealth, evolutionHealth, uiHealth] = await Promise.all([
      this.checkService(this.config.pythonUrl),
      this.checkService(this.config.evolutionUrl),
      this.config.viteUrl ? this.checkService(this.config.viteUrl) : Promise.resolve(undefined),
    ]);

    // Gateway is up if we're running
    const gatewayHealth: ServiceHealth = {
      status: 'up',
      latency: 0,
    };

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
