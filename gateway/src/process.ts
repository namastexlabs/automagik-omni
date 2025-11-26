/**
 * Process Manager for Automagik Omni Gateway
 * Spawns and manages Python API, Evolution API, and Vite dev server as subprocesses
 */

import { execa, type ExecaChildProcess, type Options } from 'execa';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { PortRegistry } from './port-registry.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '../..');

/**
 * Detect Python runtime paths (development vs bundled)
 */
function detectPythonRuntime(): { python: string; backend: string; mode: 'development' | 'bundled' } {
  const isDev = process.env.NODE_ENV === 'development' || existsSync(join(ROOT_DIR, 'src', 'api'));

  if (isDev) {
    // Development mode: use source Python from workspace
    const venvPython = join(ROOT_DIR, '.venv', 'bin', 'python');
    return {
      python: existsSync(venvPython) ? venvPython : 'python3',
      backend: ROOT_DIR,
      mode: 'development',
    };
  }

  // Production/bundled mode: use extracted Python from user home
  const bundledRoot = join(homedir(), 'automagik', 'omni');
  const pythonBin = process.platform === 'win32'
    ? join(bundledRoot, 'python', 'Scripts', 'python.exe')
    : join(bundledRoot, 'python', 'bin', 'python');

  return {
    python: pythonBin,
    backend: join(bundledRoot, 'backend'),
    mode: 'bundled',
  };
}

export interface ProcessConfig {
  devMode: boolean;
}

export interface ManagedProcess {
  name: string;
  process: ExecaChildProcess | null;
  port: number;
  healthy: boolean;
}

export class ProcessManager {
  private processes: Map<string, ManagedProcess> = new Map();
  private portRegistry: PortRegistry;
  private config: ProcessConfig;
  private shuttingDown = false;
  // Circuit breaker state
  private restartCount: Map<string, number> = new Map();
  private lastRestartTime: Map<string, number> = new Map();
  // Active health monitoring
  private healthCheckIntervals: Map<string, NodeJS.Timeout> = new Map();

  constructor(portRegistry: PortRegistry, config: Partial<ProcessConfig> = {}) {
    this.portRegistry = portRegistry;
    this.config = {
      devMode: config.devMode ?? process.env.NODE_ENV === 'development',
    };

    // Note: Signal handlers are registered in index.ts to avoid duplicates
    // The main() function will call processManager.shutdown() on SIGTERM/SIGINT
  }

  /**
   * Start the Python FastAPI backend
   */
  async startPython(): Promise<void> {
    const name = 'python';
    const port = this.portRegistry.getPort('python');
    if (!port) {
      throw new Error('Python port not allocated in registry');
    }

    // Detect runtime paths (development vs bundled)
    const runtime = detectPythonRuntime();
    console.log(`[ProcessManager] Starting Python API in ${runtime.mode} mode on port ${port}...`);
    console.log(`[ProcessManager] Python: ${runtime.python}`);
    console.log(`[ProcessManager] Backend: ${runtime.backend}`);

    const uvicornArgs = [
      '-m', 'uvicorn',
      'src.api.app:app',
      '--host', '127.0.0.1',
      '--port', String(port),
    ];

    if (this.config.devMode && runtime.mode === 'development') {
      uvicornArgs.push('--reload');
    }

    const proc = execa(runtime.python, uvicornArgs, {
      cwd: runtime.backend,
      env: {
        ...process.env,
        AUTOMAGIK_OMNI_API_PORT: String(port),
        AUTOMAGIK_OMNI_API_HOST: '127.0.0.1',
        PYTHONPATH: runtime.backend,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port,
      healthy: false,
    });

    // Log output
    proc.stdout?.on('data', (data: Buffer) => {
      console.log(`[Python] ${data.toString().trim()}`);
    });
    proc.stderr?.on('data', (data: Buffer) => {
      console.error(`[Python] ${data.toString().trim()}`);
    });

    proc.on('exit', (code) => {
      if (!this.shuttingDown) {
        const count = this.restartCount.get(name) || 0;

        // Circuit breaker: stop after 5 consecutive failures
        if (count >= 5) {
          console.error(`[ProcessManager] Circuit breaker: ${name} failed 5 times, giving up`);
          return;
        }

        // Exponential backoff: 2s, 4s, 8s, 16s, 32s (capped at 60s)
        const delay = Math.min(2000 * Math.pow(2, count), 60000);

        console.error(`[ProcessManager] Python exited with code ${code}, restarting in ${delay}ms (attempt ${count + 1}/5)...`);
        this.restartCount.set(name, count + 1);
        this.lastRestartTime.set(name, Date.now());

        setTimeout(() => this.startPython(), delay);
      }
    });

    // Reset restart counter after 30s uptime (successful start)
    setTimeout(() => {
      const proc = this.processes.get(name);
      if (proc && proc.healthy) {
        this.restartCount.set(name, 0);
        console.log(`[ProcessManager] ${name} running stable, reset restart counter`);
      }
    }, 30000);

    // Wait for Python to be ready
    await this.waitForHealth(`http://127.0.0.1:${port}/health`, name);
  }

  /**
   * Start the standalone MCP server
   */
  async startMCP(): Promise<void> {
    const name = 'mcp';
    const MCP_PORT = 18880; // Dedicated MCP port

    // Detect runtime paths (development vs bundled)
    const runtime = detectPythonRuntime();
    console.log(`[ProcessManager] Starting standalone MCP server on port ${MCP_PORT}...`);

    const proc = execa(runtime.python, [
      'src/mcp_server.py'
    ], {
      cwd: runtime.backend,
      env: {
        ...process.env,
        MCP_PORT: String(MCP_PORT),
        MCP_HOST: '127.0.0.1',
        PYTHONPATH: runtime.backend,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port: MCP_PORT,
      healthy: false,
    });

    // Log output
    proc.stdout?.on('data', (data: Buffer) => {
      console.log(`[MCP] ${data.toString().trim()}`);
    });
    proc.stderr?.on('data', (data: Buffer) => {
      console.error(`[MCP] ${data.toString().trim()}`);
    });

    proc.on('exit', (code) => {
      if (!this.shuttingDown) {
        const count = this.restartCount.get(name) || 0;

        // Circuit breaker: stop after 5 consecutive failures
        if (count >= 5) {
          console.error(`[ProcessManager] Circuit breaker: ${name} failed 5 times, giving up`);
          return;
        }

        // Exponential backoff: 2s, 4s, 8s, 16s, 32s (capped at 60s)
        const delay = Math.min(2000 * Math.pow(2, count), 60000);

        console.error(`[ProcessManager] MCP exited with code ${code}, restarting in ${delay}ms (attempt ${count + 1}/5)...`);
        this.restartCount.set(name, count + 1);
        this.lastRestartTime.set(name, Date.now());

        setTimeout(() => this.startMCP(), delay);
      }
    });

    // Reset restart counter after 30s uptime (successful start)
    setTimeout(() => {
      const proc = this.processes.get(name);
      if (proc && proc.healthy) {
        this.restartCount.set(name, 0);
        console.log(`[ProcessManager] ${name} running stable, reset restart counter`);
      }
    }, 30000);

    // Wait for MCP to be ready (try root path)
    await this.waitForHealth(`http://127.0.0.1:${MCP_PORT}/`, name);
  }

  /**
   * Start the Evolution API (WhatsApp gateway)
   */
  async startEvolution(): Promise<void> {
    const name = 'evolution';
    const port = this.portRegistry.getPort('evolution');
    if (!port) {
      throw new Error('Evolution port not allocated in registry');
    }

    const evolutionDir = join(ROOT_DIR, 'resources', 'evolution-api');

    if (!existsSync(evolutionDir)) {
      console.warn('[ProcessManager] Evolution API directory not found, skipping...');
      return;
    }

    console.log(`[ProcessManager] Starting Evolution API on port ${port}...`);

    // Detect package manager (prefer pnpm over npm)
    const usesPnpm = existsSync(join(evolutionDir, 'pnpm-lock.yaml'));
    const packageManager = usesPnpm ? 'pnpm' : 'npm';

    console.log(`[ProcessManager] Using ${packageManager} for Evolution API`);

    const proc = execa(packageManager, ['run', 'start'], {
      cwd: evolutionDir,
      env: {
        ...process.env,
        SERVER_PORT: String(port),
        SERVER_URL: `http://localhost:${port}`,
        NODE_ENV: 'production',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port,
      healthy: false,
    });

    proc.stdout?.on('data', (data: Buffer) => {
      console.log(`[Evolution] ${data.toString().trim()}`);
    });
    proc.stderr?.on('data', (data: Buffer) => {
      console.error(`[Evolution] ${data.toString().trim()}`);
    });

    proc.on('exit', (code) => {
      if (!this.shuttingDown) {
        const count = this.restartCount.get(name) || 0;

        // Circuit breaker: stop after 5 consecutive failures
        if (count >= 5) {
          console.error(`[ProcessManager] Circuit breaker: ${name} failed 5 times, giving up`);
          return;
        }

        // Exponential backoff: 2s, 4s, 8s, 16s, 32s (capped at 60s)
        const delay = Math.min(2000 * Math.pow(2, count), 60000);

        console.error(`[ProcessManager] Evolution exited with code ${code}, restarting in ${delay}ms (attempt ${count + 1}/5)...`);
        this.restartCount.set(name, count + 1);
        this.lastRestartTime.set(name, Date.now());

        setTimeout(() => this.startEvolution(), delay);
      }
    });

    // Reset restart counter after 30s uptime (successful start)
    setTimeout(() => {
      const proc = this.processes.get(name);
      if (proc && proc.healthy) {
        this.restartCount.set(name, 0);
        console.log(`[ProcessManager] ${name} running stable, reset restart counter`);
      }
    }, 30000);

    // Wait for Evolution to be ready
    await this.waitForHealth(`http://127.0.0.1:${port}/`, name, 60000);
  }

  /**
   * Start Discord service manager (manages all Discord bot instances)
   */
  async startDiscord(): Promise<void> {
    const name = 'discord';

    console.log(`[ProcessManager] Starting Discord service manager...`);

    const runtime = detectPythonRuntime();

    const proc = execa(runtime.python, [
      'src/commands/discord_service_manager.py'
    ], {
      cwd: runtime.backend,
      env: {
        ...process.env,
        PYTHONPATH: runtime.backend,
        AUTOMAGIK_OMNI_API_HOST: '127.0.0.1',
        AUTOMAGIK_OMNI_API_PORT: String(this.portRegistry.getPort('python') || 8882),
        DISCORD_HEALTH_CHECK_TIMEOUT: '60',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port: 0,
      healthy: false,
    });

    proc.stdout?.on('data', (data: Buffer) => {
      console.log(`[Discord] ${data.toString().trim()}`);
    });
    proc.stderr?.on('data', (data: Buffer) => {
      console.error(`[Discord] ${data.toString().trim()}`);
    });

    proc.on('exit', (code) => {
      if (!this.shuttingDown) {
        const count = this.restartCount.get(name) || 0;

        // Circuit breaker: stop after 5 consecutive failures
        if (count >= 5) {
          console.error(`[ProcessManager] Circuit breaker: ${name} failed 5 times, giving up`);
          return;
        }

        // Exponential backoff: 5s, 10s, 20s, 40s, 60s (capped at 60s)
        const delay = Math.min(5000 * Math.pow(2, count), 60000);

        console.error(`[ProcessManager] Discord exited with code ${code}, restarting in ${delay}ms (attempt ${count + 1}/5)...`);
        this.restartCount.set(name, count + 1);
        this.lastRestartTime.set(name, Date.now());

        setTimeout(() => this.startDiscord(), delay);
      }
    });

    // Reset restart counter after 30s uptime (successful start)
    setTimeout(() => {
      const proc = this.processes.get(name);
      if (proc && proc.healthy) {
        this.restartCount.set(name, 0);
        console.log(`[ProcessManager] ${name} running stable, reset restart counter`);
      }
    }, 30000);

    // Discord service manager doesn't have HTTP health endpoint
    // Wait 3s and mark healthy if process still running
    await new Promise((r) => setTimeout(r, 3000));

    const p = this.processes.get(name);
    if (p) {
      p.healthy = true;
      console.log(`[ProcessManager] ${name} is healthy`);
    }
  }

  /**
   * Start Vite dev server (development mode only)
   */
  async startVite(): Promise<void> {
    if (!this.config.devMode) {
      console.log('[ProcessManager] Production mode, skipping Vite dev server');
      return;
    }

    const name = 'vite';
    const port = this.portRegistry.getPort('vite');
    if (!port) {
      throw new Error('Vite port not allocated in registry');
    }

    const uiDir = join(ROOT_DIR, 'resources', 'ui');

    if (!existsSync(uiDir)) {
      console.warn('[ProcessManager] UI directory not found, skipping...');
      return;
    }

    console.log(`[ProcessManager] Starting Vite dev server on port ${port}...`);

    const proc = execa('npm', ['run', 'dev'], {
      cwd: uiDir,
      env: {
        ...process.env,
        UI_PORT: String(port),
        UI_HOST: '127.0.0.1',
        // Point Vite's API proxy to our gateway (not directly to Python)
        VITE_API_URL: `http://127.0.0.1:${process.env.OMNI_PORT ?? 8882}`,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port,
      healthy: false,
    });

    proc.stdout?.on('data', (data: Buffer) => {
      const line = data.toString().trim();
      console.log(`[Vite] ${line}`);
      // Detect Vite ready message
      if (line.includes('Local:') || line.includes('ready in')) {
        const p = this.processes.get(name);
        if (p) p.healthy = true;
      }
    });
    proc.stderr?.on('data', (data: Buffer) => {
      console.error(`[Vite] ${data.toString().trim()}`);
    });

    proc.on('exit', (code) => {
      if (!this.shuttingDown) {
        const count = this.restartCount.get(name) || 0;

        // Circuit breaker: stop after 5 consecutive failures
        if (count >= 5) {
          console.error(`[ProcessManager] Circuit breaker: ${name} failed 5 times, giving up`);
          return;
        }

        // Exponential backoff: 2s, 4s, 8s, 16s, 32s (capped at 60s)
        const delay = Math.min(2000 * Math.pow(2, count), 60000);

        console.error(`[ProcessManager] Vite exited with code ${code}, restarting in ${delay}ms (attempt ${count + 1}/5)...`);
        this.restartCount.set(name, count + 1);
        this.lastRestartTime.set(name, Date.now());

        setTimeout(() => this.startVite(), delay);
      }
    });

    // Reset restart counter after 30s uptime (successful start)
    setTimeout(() => {
      const proc = this.processes.get(name);
      if (proc && proc.healthy) {
        this.restartCount.set(name, 0);
        console.log(`[ProcessManager] ${name} running stable, reset restart counter`);
      }
    }, 30000);

    // Give Vite a few seconds to start
    await new Promise((r) => setTimeout(r, 3000));
  }

  /**
   * Wait for a service to become healthy
   */
  private async waitForHealth(url: string, name: string, timeout = 30000): Promise<void> {
    const start = Date.now();
    const checkInterval = 500;

    while (Date.now() - start < timeout) {
      try {
        const response = await fetch(url, { method: 'GET' });
        if (response.ok || response.status < 500) {
          console.log(`[ProcessManager] ${name} is healthy`);
          const proc = this.processes.get(name);
          if (proc) proc.healthy = true;

          // Release port reservation socket (atomic handoff complete)
          if (name === 'python') {
            this.portRegistry.confirmAllocation('python');
          } else if (name === 'evolution') {
            this.portRegistry.confirmAllocation('evolution');
          } else if (name === 'vite') {
            this.portRegistry.confirmAllocation('vite');
          }

          // Start active health monitoring (polls every 10s)
          this.startHealthMonitoring(url, name);

          return;
        }
      } catch {
        // Service not ready yet
      }
      await new Promise((r) => setTimeout(r, checkInterval));
    }

    console.warn(`[ProcessManager] ${name} health check timed out after ${timeout}ms`);
  }

  /**
   * Start active health monitoring for a service (polls every 10s)
   */
  private startHealthMonitoring(url: string, name: string): void {
    // Clear existing interval if any
    const existingInterval = this.healthCheckIntervals.get(name);
    if (existingInterval) {
      clearInterval(existingInterval);
    }

    // Poll health every 10 seconds
    const interval = setInterval(async () => {
      if (this.shuttingDown) {
        clearInterval(interval);
        return;
      }

      try {
        const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(5000) });
        const proc = this.processes.get(name);
        if (proc) {
          const wasHealthy = proc.healthy;
          proc.healthy = response.ok || response.status < 500;

          // Log state changes
          if (wasHealthy && !proc.healthy) {
            console.warn(`[ProcessManager] ${name} became unhealthy`);
          } else if (!wasHealthy && proc.healthy) {
            console.log(`[ProcessManager] ${name} recovered to healthy state`);
          }
        }
      } catch (error) {
        // Network error or timeout - mark as unhealthy
        const proc = this.processes.get(name);
        if (proc && proc.healthy) {
          proc.healthy = false;
          console.warn(`[ProcessManager] ${name} health check failed, marked unhealthy`);
        }
      }
    }, 10000);

    this.healthCheckIntervals.set(name, interval);
    console.log(`[ProcessManager] Started active health monitoring for ${name}`);
  }

  /**
   * Get status of all managed processes
   */
  getStatus(): Record<string, { port: number; healthy: boolean; pid?: number }> {
    const status: Record<string, { port: number; healthy: boolean; pid?: number }> = {};
    for (const [name, proc] of this.processes) {
      status[name] = {
        port: proc.port,
        healthy: proc.healthy,
        pid: proc.process?.pid,
      };
    }
    return status;
  }

  /**
   * Gracefully shutdown all processes
   */
  async shutdown(): Promise<void> {
    if (this.shuttingDown) return;
    this.shuttingDown = true;

    console.log('[ProcessManager] Shutting down all processes...');

    // Clear all health check intervals
    for (const [name, interval] of this.healthCheckIntervals) {
      clearInterval(interval);
      console.log(`[ProcessManager] Stopped health monitoring for ${name}`);
    }
    this.healthCheckIntervals.clear();

    const shutdownPromises: Promise<void>[] = [];

    for (const [name, managed] of this.processes) {
      if (managed.process && !managed.process.killed) {
        console.log(`[ProcessManager] Stopping ${name}...`);
        managed.process.kill('SIGTERM');

        // Give process time to gracefully shutdown
        const timeoutPromise = new Promise<void>((resolve) => {
          const timeout = setTimeout(() => {
            if (managed.process && !managed.process.killed) {
              console.log(`[ProcessManager] Force killing ${name}...`);
              managed.process.kill('SIGKILL');
            }
            resolve();
          }, 5000);

          managed.process?.on('exit', () => {
            clearTimeout(timeout);
            resolve();
          });
        });

        shutdownPromises.push(timeoutPromise);
      }
    }

    await Promise.all(shutdownPromises);
    console.log('[ProcessManager] All processes stopped');
    process.exit(0);
  }
}
