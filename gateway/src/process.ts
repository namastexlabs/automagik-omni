/**
 * Process Manager for Automagik Omni Gateway
 * Spawns and manages Python API, Evolution API, and Vite dev server as subprocesses
 */

import { execa, type ExecaChildProcess, type Options } from 'execa';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '../..');

export interface ProcessConfig {
  pythonPort: number;
  evolutionPort: number;
  vitePort: number;
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
  private config: ProcessConfig;
  private shuttingDown = false;

  constructor(config: Partial<ProcessConfig> = {}) {
    this.config = {
      pythonPort: config.pythonPort ?? parseInt(process.env.PYTHON_API_PORT ?? '8881', 10),
      evolutionPort: config.evolutionPort ?? parseInt(process.env.EVOLUTION_PORT ?? '18082', 10),
      vitePort: config.vitePort ?? parseInt(process.env.VITE_PORT ?? '9882', 10),
      devMode: config.devMode ?? process.env.NODE_ENV === 'development',
    };

    // Handle graceful shutdown
    process.on('SIGTERM', () => this.shutdown());
    process.on('SIGINT', () => this.shutdown());
  }

  /**
   * Start the Python FastAPI backend
   */
  async startPython(): Promise<void> {
    const name = 'python';
    console.log(`[ProcessManager] Starting Python API on port ${this.config.pythonPort}...`);

    // Determine the Python executable (prefer venv)
    const venvPython = join(ROOT_DIR, '.venv', 'bin', 'python');
    const pythonExe = existsSync(venvPython) ? venvPython : 'python3';

    const uvicornArgs = [
      '-m', 'uvicorn',
      'src.api.app:app',
      '--host', '127.0.0.1',
      '--port', String(this.config.pythonPort),
    ];

    if (this.config.devMode) {
      uvicornArgs.push('--reload');
    }

    const proc = execa(pythonExe, uvicornArgs, {
      cwd: ROOT_DIR,
      env: {
        ...process.env,
        AUTOMAGIK_OMNI_API_PORT: String(this.config.pythonPort),
        AUTOMAGIK_OMNI_API_HOST: '127.0.0.1',
        PYTHONPATH: ROOT_DIR,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port: this.config.pythonPort,
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
        console.error(`[ProcessManager] Python exited with code ${code}, restarting...`);
        setTimeout(() => this.startPython(), 2000);
      }
    });

    // Wait for Python to be ready
    await this.waitForHealth(`http://127.0.0.1:${this.config.pythonPort}/health`, name);
  }

  /**
   * Start the Evolution API (WhatsApp gateway)
   */
  async startEvolution(): Promise<void> {
    const name = 'evolution';
    const evolutionDir = join(ROOT_DIR, 'resources', 'evolution-api');

    if (!existsSync(evolutionDir)) {
      console.warn('[ProcessManager] Evolution API directory not found, skipping...');
      return;
    }

    console.log(`[ProcessManager] Starting Evolution API on port ${this.config.evolutionPort}...`);

    const proc = execa('npm', ['run', 'start'], {
      cwd: evolutionDir,
      env: {
        ...process.env,
        SERVER_PORT: String(this.config.evolutionPort),
        SERVER_URL: `http://localhost:${this.config.evolutionPort}`,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port: this.config.evolutionPort,
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
        console.error(`[ProcessManager] Evolution exited with code ${code}, restarting...`);
        setTimeout(() => this.startEvolution(), 5000);
      }
    });

    // Wait for Evolution to be ready
    await this.waitForHealth(`http://127.0.0.1:${this.config.evolutionPort}/`, name, 60000);
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
    const uiDir = join(ROOT_DIR, 'resources', 'ui');

    if (!existsSync(uiDir)) {
      console.warn('[ProcessManager] UI directory not found, skipping...');
      return;
    }

    console.log(`[ProcessManager] Starting Vite dev server on port ${this.config.vitePort}...`);

    const proc = execa('npm', ['run', 'dev'], {
      cwd: uiDir,
      env: {
        ...process.env,
        UI_PORT: String(this.config.vitePort),
        UI_HOST: '127.0.0.1',
        // Point Vite's API proxy to our gateway (not directly to Python)
        VITE_API_URL: `http://127.0.0.1:${process.env.OMNI_PORT ?? 8882}`,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port: this.config.vitePort,
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
        console.error(`[ProcessManager] Vite exited with code ${code}, restarting...`);
        setTimeout(() => this.startVite(), 2000);
      }
    });

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
