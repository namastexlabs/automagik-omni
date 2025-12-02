/**
 * Process Manager for Automagik Omni Gateway
 * Spawns and manages Python API, Evolution API, and Vite dev server as subprocesses
 */

import { execa, type ExecaChildProcess, type Options } from 'execa';
import { existsSync, readdirSync, createWriteStream } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { createConnection } from 'node:net';
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
   * Setup logging for a process (file + console)
   */
  private setupLogging(logName: string, proc: ExecaChildProcess, consolePrefix: string) {
    try {
      // Ensure logs directory exists
      const logsDir = join(ROOT_DIR, 'logs');
      if (!existsSync(logsDir)) {
        const fs = require('fs');
        fs.mkdirSync(logsDir, { recursive: true });
      }

      const logFile = join(logsDir, `${logName}-combined.log`);
      const stream = createWriteStream(logFile, { flags: 'a' });

      proc.stdout?.on('data', (data: Buffer) => {
        stream.write(data); // Write raw to file
        const line = data.toString().trim();
        if (line) console.log(`[${consolePrefix}] ${line}`);
      });

      proc.stderr?.on('data', (data: Buffer) => {
        stream.write(data);
        const line = data.toString().trim();
        if (line) console.error(`[${consolePrefix}] ${line}`);
      });
      
      proc.on('exit', () => {
        stream.end();
      });
    } catch (error) {
      console.warn(`[ProcessManager] Failed to setup file logging for ${logName}:`, error);
      // Fallback to console only
      proc.stdout?.on('data', (data: Buffer) => {
        console.log(`[${consolePrefix}] ${data.toString().trim()}`);
      });
      proc.stderr?.on('data', (data: Buffer) => {
        console.error(`[${consolePrefix}] ${data.toString().trim()}`);
      });
    }
  }

  /**
   * Check if lazy channel loading is enabled.
   * When enabled, channels start on-demand (first instance creation) rather than at gateway startup.
   *
   * Environment variable: LAZY_CHANNELS=true
   *
   * @returns true if lazy loading is enabled
   */
  isLazyModeEnabled(): boolean {
    const value = process.env.LAZY_CHANNELS;
    return value === 'true' || value === '1';
  }

  /**
   * Check if a channel is enabled via environment variable.
   * Channels are enabled by default unless explicitly disabled.
   *
   * Environment variables:
   *   - EVOLUTION_ENABLED=false  - Disable WhatsApp/Evolution
   *   - DISCORD_ENABLED=false    - Disable Discord
   *
   * @param channel - Channel name (e.g., 'evolution', 'discord')
   * @returns true if enabled (default), false if explicitly disabled
   */
  isChannelEnabled(channel: string): boolean {
    const envKey = `${channel.toUpperCase()}_ENABLED`;
    const value = process.env[envKey];

    // Disabled only if explicitly set to 'false' or '0'
    if (value === 'false' || value === '0') {
      console.log(`[ProcessManager] ${channel} channel disabled via ${envKey}=${value}`);
      return false;
    }

    return true;
  }

  /**
   * Check if a channel process is currently running.
   *
   * @param channel - Channel name (e.g., 'evolution', 'discord')
   * @returns true if the channel process is running
   */
  isChannelRunning(channel: string): boolean {
    const managed = this.processes.get(channel);
    if (!managed || !managed.process) {
      return false;
    }
    // ExecaChildProcess.exitCode is null while running, number after exit
    return managed.process.exitCode === null;
  }

  /**
   * Ensure a channel is running. Starts the channel if not already running.
   * Used for on-demand channel startup in lazy mode.
   *
   * @param channel - Channel name (e.g., 'evolution', 'discord')
   * @returns Promise that resolves when channel is running
   */
  async ensureChannelRunning(channel: string): Promise<void> {
    if (this.isChannelRunning(channel)) {
      console.log(`[ProcessManager] ${channel} channel already running`);
      return;
    }

    if (!this.isChannelEnabled(channel)) {
      console.log(`[ProcessManager] ${channel} channel is disabled, not starting`);
      return;
    }

    console.log(`[ProcessManager] Starting ${channel} channel on-demand...`);

    switch (channel.toLowerCase()) {
      case 'evolution':
        await this.startEvolution();
        break;
      case 'discord':
        await this.startDiscord();
        break;
      default:
        console.warn(`[ProcessManager] Unknown channel: ${channel}`);
    }
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

    // Setup logging (file: api-combined.log, console: [Python])
    this.setupLogging('api', proc, 'Python');

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

    // Check if channel is enabled via environment
    if (!this.isChannelEnabled(name)) {
      console.log('[ProcessManager] Evolution/WhatsApp channel disabled, skipping...');
      return;
    }

    const port = this.portRegistry.getPort('evolution');
    if (!port) {
      throw new Error('Evolution port not allocated in registry');
    }

    const evolutionDir = join(ROOT_DIR, 'resources', 'omni-whatsapp-core');

    if (!existsSync(evolutionDir)) {
      console.warn('[ProcessManager] Evolution API directory not found, skipping...');
      return;
    }

    console.log(`[ProcessManager] Starting Evolution API on port ${port}...`);

    // Fetch database config from Python API before spawning
    // This is REQUIRED for Evolution to work - fail hard if not available
    const pythonPort = this.portRegistry.getPort('python');
    let subprocessEnv: Record<string, string> = {};

    if (!pythonPort) {
      throw new Error('Python API not running. Cannot start Evolution without database config.');
    }

    try {
      const configUrl = `http://127.0.0.1:${pythonPort}/api/v1/_internal/subprocess-config`;
      const response = await fetch(configUrl, { signal: AbortSignal.timeout(10000) }); // 10s timeout

      if (!response.ok) {
        throw new Error(`Failed to fetch subprocess config: HTTP ${response.status}`);
      }

      const config = await response.json();
      console.log('[ProcessManager] Loaded subprocess config from Python API');

      // Validate required fields - Evolution CANNOT work without database config
      if (!config.database_connection_uri) {
        throw new Error(
          'Database not configured. Please complete the setup wizard first. ' +
          'Evolution requires a PostgreSQL database to store WhatsApp sessions.'
        );
      }

      subprocessEnv.DATABASE_CONNECTION_URI = config.database_connection_uri;
      subprocessEnv.DATABASE_PROVIDER = config.database_provider || 'postgresql';
      subprocessEnv.DATABASE_SAVE_DATA_INSTANCE = 'true';  // Enable Prisma auth state storage
      console.log(`[ProcessManager] Evolution will use ${config.database_provider} database`);

      if (config.authentication_api_key) {
        subprocessEnv.AUTHENTICATION_API_KEY = config.authentication_api_key;
      }
    } catch (err) {
      // Re-throw with context - don't silently continue
      const message = err instanceof Error ? err.message : String(err);
      throw new Error(`Cannot start Evolution: ${message}`);
    }

    // Detect package manager (prefer pnpm over npm)
    const usesPnpm = existsSync(join(evolutionDir, 'pnpm-lock.yaml'));
    const packageManager = usesPnpm ? 'pnpm' : 'npm';

    console.log(`[ProcessManager] Using ${packageManager} for Evolution API`);

    const proc = execa(packageManager, ['run', 'start'], {
      cwd: evolutionDir,
      env: {
        ...process.env,
        ...subprocessEnv,
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

    // Setup logging (file: evolution-combined.log, console: [Evolution])
    this.setupLogging('evolution', proc, 'Evolution');

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

    // Wait for Evolution to be ready (120s for first-run: Prisma generation, etc.)
    await this.waitForHealth(`http://127.0.0.1:${port}/`, name, 120000);
  }

  /**
   * Start Discord service manager (manages all Discord bot instances)
   */
  async startDiscord(): Promise<void> {
    const name = 'discord';

    // Check if channel is enabled via environment
    if (!this.isChannelEnabled(name)) {
      console.log('[ProcessManager] Discord channel disabled, skipping...');
      return;
    }

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
        DISCORD_HEALTH_CHECK_TIMEOUT: '10',  // Reduced from 60s - Discord starts quickly
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    } as Options);

    this.processes.set(name, {
      name,
      process: proc,
      port: 0,
      healthy: false,
    });

    // Setup logging (file: discord-combined.log, console: [Discord])
    this.setupLogging('discord', proc, 'Discord');

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

    // Discord service manager creates Unix sockets for each bot instance
    // Poll the sockets directory until at least one Discord socket responds healthy
    // Reduced timeout from 60s to 10s - Discord starts quickly if configured
    await this.waitForDiscordHealth(name, 10000);
  }

  /**
   * Wait for Discord health by polling Unix socket endpoints
   * Discord bots create sockets at ~/automagik-omni/sockets/discord-{instance}.sock
   */
  private async waitForDiscordHealth(name: string, timeout = 10000): Promise<void> {
    const start = Date.now();
    const checkInterval = 2000;

    // Socket directory paths (matches ipc_config.py logic)
    const userSocketDir = join(homedir(), 'automagik-omni', 'sockets');
    const defaultSocketDir = '/automagik-omni/sockets';

    const getSocketDir = (): string => {
      const envDir = process.env.AUTOMAGIK_SOCKET_DIR;
      if (envDir) return envDir.replace('~', homedir());
      if (existsSync(defaultSocketDir)) return defaultSocketDir;
      return userSocketDir;
    };

    console.log(`[ProcessManager] Waiting for Discord health via Unix sockets...`);

    while (Date.now() - start < timeout) {
      try {
        const socketDir = getSocketDir();

        if (existsSync(socketDir)) {
          const files = readdirSync(socketDir);
          const discordSockets = files.filter((f) => f.startsWith('discord-') && f.endsWith('.sock'));

          if (discordSockets.length > 0) {
            // Try to connect to each socket and check health
            for (const socketFile of discordSockets) {
              const socketPath = join(socketDir, socketFile);
              const healthy = await this.checkUnixSocketHealth(socketPath);

              if (healthy) {
                console.log(`[ProcessManager] Discord socket ${socketFile} is healthy`);
                const proc = this.processes.get(name);
                if (proc) proc.healthy = true;
                return;
              }
            }
            console.log(`[ProcessManager] Found ${discordSockets.length} Discord socket(s), waiting for healthy status...`);
          }
        }
      } catch {
        // Socket dir not ready yet
      }

      await new Promise((r) => setTimeout(r, checkInterval));
    }

    // Timeout - mark healthy anyway if process is still running
    // Discord may have no instances configured, which is valid
    const proc = this.processes.get(name);
    if (proc?.process && !proc.process.killed) {
      proc.healthy = true;
      console.log(`[ProcessManager] Discord process running (no instances found or timeout), marking healthy`);
    } else {
      console.warn(`[ProcessManager] Discord health check timed out after ${timeout}ms`);
    }
  }

  /**
   * Check health of a Unix socket endpoint
   */
  private checkUnixSocketHealth(socketPath: string): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = createConnection(socketPath);
      let responseData = '';

      socket.setTimeout(5000);

      socket.on('connect', () => {
        // Send HTTP GET request for /health
        socket.write('GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n');
      });

      socket.on('data', (data) => {
        responseData += data.toString();
      });

      socket.on('end', () => {
        try {
          // Parse HTTP response - look for JSON body
          const bodyStart = responseData.indexOf('\r\n\r\n');
          if (bodyStart !== -1) {
            const body = responseData.slice(bodyStart + 4);
            const json = JSON.parse(body);
            resolve(json.status === 'ok' && json.bot_connected === true);
          } else {
            resolve(false);
          }
        } catch {
          resolve(false);
        }
      });

      socket.on('error', () => resolve(false));
      socket.on('timeout', () => {
        socket.destroy();
        resolve(false);
      });
    });
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
   * Stop a specific channel process gracefully.
   *
   * @param channel - Channel name (e.g., 'evolution', 'discord')
   * @returns true if stopped, false if not running
   */
  async stopChannel(channel: string): Promise<boolean> {
    const managed = this.processes.get(channel);
    if (!managed?.process || managed.process.exitCode !== null) {
      console.log(`[ProcessManager] ${channel} not running, nothing to stop`);
      return false;
    }

    console.log(`[ProcessManager] Stopping ${channel}...`);

    // Clear health monitoring for this channel
    const interval = this.healthCheckIntervals.get(channel);
    if (interval) {
      clearInterval(interval);
      this.healthCheckIntervals.delete(channel);
    }

    // Send SIGTERM for graceful shutdown
    managed.process.kill('SIGTERM');

    // Wait for exit with 5s timeout
    await new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        if (managed.process && managed.process.exitCode === null) {
          console.log(`[ProcessManager] Force killing ${channel}...`);
          managed.process.kill('SIGKILL');
        }
        resolve();
      }, 5000);

      managed.process?.on('exit', () => {
        clearTimeout(timeout);
        resolve();
      });
    });

    // Clean up state
    this.processes.delete(channel);
    this.restartCount.delete(channel);
    this.lastRestartTime.delete(channel);

    console.log(`[ProcessManager] ${channel} stopped`);
    return true;
  }

  /**
   * Get process info for a channel.
   *
   * @param channel - Channel name
   * @returns ManagedProcess or undefined if not found
   */
  getProcessInfo(channel: string): ManagedProcess | undefined {
    return this.processes.get(channel);
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
