/**
 * PgserveManager - Embedded PostgreSQL Manager for Automagik Omni Gateway
 *
 * Manages the embedded PostgreSQL instance using pgserve.
 * Features:
 * - Start/stop embedded PostgreSQL
 * - Health checks (process alive, accepts connections)
 * - Crash recovery with circuit breaker
 * - Disk usage monitoring
 * - Graceful shutdown
 */

import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync, statSync, mkdirSync } from 'node:fs';
import { homedir } from 'node:os';

// Import pgserve (ESM)
// @ts-expect-error - pgserve has no TypeScript definitions yet
import { startMultiTenantServer, type MultiTenantRouter } from 'pgserve';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '../..');

/**
 * Default data directory for persistent PostgreSQL storage
 */
function getDefaultDataDir(): string {
  // Check for explicit env var first
  if (process.env.PGSERVE_DATA_DIR) {
    return process.env.PGSERVE_DATA_DIR;
  }

  // Default: ./data/postgres relative to project root
  return join(ROOT_DIR, 'data', 'postgres');
}

/**
 * Configuration options for PgserveManager
 */
export interface PgserveConfig {
  /** Data directory for persistent storage (null = memory mode) */
  dataDir: string | null;
  /** TCP port for PostgreSQL connections (default: 5432) */
  port: number;
  /** Enable memory mode (ephemeral, no persistence) */
  memoryMode: boolean;
  /** Log level */
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  /** Replication target URL (optional, for async sync) */
  replicationUrl?: string;
  /** Database patterns to replicate (comma-separated) */
  replicationDatabases?: string;
}

/**
 * Health status for pgserve
 */
export interface PgserveHealth {
  status: 'starting' | 'healthy' | 'unhealthy' | 'stopped';
  port: number;
  dataDir: string | null;
  memoryMode: boolean;
  diskUsageMb: number;
  uptime: number;
  databases: string[];
  replication?: {
    enabled: boolean;
    targetUrl?: string;
  };
}

/**
 * Disk usage thresholds (in MB)
 */
const DISK_WARN_THRESHOLD_MB = 500;
const DISK_ERROR_THRESHOLD_MB = 1000;

/**
 * PgserveManager - Manages embedded PostgreSQL lifecycle
 */
export class PgserveManager {
  private router: MultiTenantRouter | null = null;
  private config: PgserveConfig;
  private startTime: number = 0;
  private healthy: boolean = false;
  private shuttingDown: boolean = false;
  private healthCheckInterval: NodeJS.Timeout | null = null;

  // Circuit breaker state
  private restartCount: number = 0;
  private lastRestartTime: number = 0;
  private static readonly MAX_RESTARTS = 5;
  private static readonly RESTART_RESET_MS = 30000; // 30s stable = reset counter

  constructor(config: Partial<PgserveConfig> = {}) {
    // Determine memory mode based on environment
    const memoryMode = config.memoryMode ??
      process.env.PGSERVE_MEMORY_MODE === 'true' ??
      false;

    this.config = {
      dataDir: memoryMode ? null : (config.dataDir ?? getDefaultDataDir()),
      port: config.port ?? parseInt(process.env.PGSERVE_PORT ?? '5432', 10),
      memoryMode,
      logLevel: config.logLevel ?? (process.env.NODE_ENV === 'development' ? 'debug' : 'info'),
      replicationUrl: config.replicationUrl ?? process.env.PGSERVE_REPLICATION_URL,
      replicationDatabases: config.replicationDatabases ?? process.env.PGSERVE_REPLICATION_DATABASES,
    };

    // Ensure data directory exists if not in memory mode
    if (this.config.dataDir && !existsSync(this.config.dataDir)) {
      console.log(`[PgserveManager] Creating data directory: ${this.config.dataDir}`);
      mkdirSync(this.config.dataDir, { recursive: true });
    }
  }

  /**
   * Start the embedded PostgreSQL server
   */
  async start(): Promise<void> {
    if (this.router) {
      console.log('[PgserveManager] Already running, skipping start');
      return;
    }

    console.log(`[PgserveManager] Starting embedded PostgreSQL...`);
    console.log(`[PgserveManager] Data directory: ${this.config.dataDir ?? '(in-memory)'}`);
    console.log(`[PgserveManager] Port: ${this.config.port}`);

    if (this.config.replicationUrl) {
      console.log(`[PgserveManager] Replication target: ${this.config.replicationUrl}`);
    }

    try {
      this.router = await startMultiTenantServer({
        port: this.config.port,
        host: '127.0.0.1',
        baseDir: this.config.dataDir,
        autoProvision: true,
        logLevel: this.config.logLevel,
        // Replication options
        syncTo: this.config.replicationUrl,
        syncDatabases: this.config.replicationDatabases,
      });

      this.startTime = Date.now();
      this.healthy = true;

      console.log(`[PgserveManager] PostgreSQL ready on port ${this.config.port}`);

      // Start health monitoring
      this.startHealthMonitoring();

      // Reset restart counter after stable period
      setTimeout(() => {
        if (this.healthy) {
          this.restartCount = 0;
          console.log('[PgserveManager] Running stable, reset restart counter');
        }
      }, PgserveManager.RESTART_RESET_MS);

    } catch (error) {
      console.error('[PgserveManager] Failed to start:', error);
      this.healthy = false;

      // Apply circuit breaker
      if (this.restartCount < PgserveManager.MAX_RESTARTS) {
        const delay = Math.min(2000 * Math.pow(2, this.restartCount), 60000);
        this.restartCount++;
        this.lastRestartTime = Date.now();

        console.error(`[PgserveManager] Restarting in ${delay}ms (attempt ${this.restartCount}/${PgserveManager.MAX_RESTARTS})`);
        setTimeout(() => this.start(), delay);
      } else {
        console.error('[PgserveManager] Circuit breaker: Max restarts reached, giving up');
        throw error;
      }
    }
  }

  /**
   * Stop the embedded PostgreSQL server
   */
  async stop(): Promise<void> {
    if (this.shuttingDown) return;
    this.shuttingDown = true;

    console.log('[PgserveManager] Stopping embedded PostgreSQL...');

    // Stop health monitoring
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }

    if (this.router) {
      try {
        await this.router.stop();
        console.log('[PgserveManager] PostgreSQL stopped gracefully');
      } catch (error) {
        console.warn('[PgserveManager] Error during shutdown:', error);
      }
      this.router = null;
    }

    this.healthy = false;
    this.shuttingDown = false;
  }

  /**
   * Start active health monitoring
   */
  private startHealthMonitoring(): void {
    // Check every 10 seconds
    this.healthCheckInterval = setInterval(async () => {
      if (this.shuttingDown) return;

      try {
        const health = await this.getHealth();

        // Check disk usage thresholds
        if (health.diskUsageMb >= DISK_ERROR_THRESHOLD_MB) {
          console.error(`[PgserveManager] CRITICAL: Disk usage ${health.diskUsageMb}MB exceeds ${DISK_ERROR_THRESHOLD_MB}MB threshold`);
        } else if (health.diskUsageMb >= DISK_WARN_THRESHOLD_MB) {
          console.warn(`[PgserveManager] WARNING: Disk usage ${health.diskUsageMb}MB exceeds ${DISK_WARN_THRESHOLD_MB}MB threshold`);
        }

        // Log health state changes
        if (health.status === 'unhealthy' && this.healthy) {
          console.warn('[PgserveManager] PostgreSQL became unhealthy');
          this.healthy = false;
        } else if (health.status === 'healthy' && !this.healthy) {
          console.log('[PgserveManager] PostgreSQL recovered to healthy state');
          this.healthy = true;
        }
      } catch (error) {
        if (this.healthy) {
          console.warn('[PgserveManager] Health check failed:', error);
          this.healthy = false;
        }
      }
    }, 10000);
  }

  /**
   * Get disk usage of data directory in MB
   */
  private getDiskUsageMb(): number {
    if (!this.config.dataDir || !existsSync(this.config.dataDir)) {
      return 0;
    }

    try {
      // Get size of data directory (recursive)
      const { execSync } = require('child_process');
      const result = execSync(`du -sm "${this.config.dataDir}" 2>/dev/null || echo "0"`, {
        encoding: 'utf8',
        timeout: 5000,
      });
      const match = result.match(/^(\d+)/);
      return match ? parseInt(match[1], 10) : 0;
    } catch {
      // Fallback: just check if directory exists
      return 0;
    }
  }

  /**
   * Get comprehensive health status
   */
  async getHealth(): Promise<PgserveHealth> {
    const uptime = this.startTime > 0 ? (Date.now() - this.startTime) / 1000 : 0;

    if (!this.router) {
      return {
        status: 'stopped',
        port: this.config.port,
        dataDir: this.config.dataDir,
        memoryMode: this.config.memoryMode,
        diskUsageMb: 0,
        uptime: 0,
        databases: [],
      };
    }

    try {
      const stats = this.router.getStats();
      const diskUsageMb = this.getDiskUsageMb();

      return {
        status: 'healthy',
        port: this.config.port,
        dataDir: this.config.dataDir,
        memoryMode: this.config.memoryMode,
        diskUsageMb,
        uptime,
        databases: stats.postgres?.databases ?? [],
        replication: this.config.replicationUrl ? {
          enabled: true,
          targetUrl: this.config.replicationUrl,
        } : { enabled: false },
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        port: this.config.port,
        dataDir: this.config.dataDir,
        memoryMode: this.config.memoryMode,
        diskUsageMb: this.getDiskUsageMb(),
        uptime,
        databases: [],
      };
    }
  }

  /**
   * Check if PostgreSQL is healthy
   */
  isHealthy(): boolean {
    return this.healthy;
  }

  /**
   * Get PostgreSQL connection URL for a database
   */
  getConnectionUrl(database: string = 'omni'): string {
    return `postgresql://postgres:postgres@127.0.0.1:${this.config.port}/${database}`;
  }

  /**
   * Get the port PostgreSQL is running on
   */
  getPort(): number {
    return this.config.port;
  }

  /**
   * Get data directory path
   */
  getDataDir(): string | null {
    return this.config.dataDir;
  }

  /**
   * Check if running in memory mode
   */
  isMemoryMode(): boolean {
    return this.config.memoryMode;
  }
}

/**
 * Default singleton instance
 */
let defaultManager: PgserveManager | null = null;

/**
 * Get or create the default PgserveManager instance
 */
export function getDefaultPgserveManager(config?: Partial<PgserveConfig>): PgserveManager {
  if (!defaultManager) {
    defaultManager = new PgserveManager(config);
  }
  return defaultManager;
}
