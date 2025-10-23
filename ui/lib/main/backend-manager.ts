import { spawn, ChildProcess } from 'child_process'
import { app } from 'electron'
import { join } from 'path'
import { existsSync } from 'fs'

/**
 * Backend process status enum
 */
export enum BackendProcessStatus {
  STOPPED = 'stopped',
  STARTING = 'starting',
  RUNNING = 'running',
  STOPPING = 'stopping',
  ERROR = 'error',
}

/**
 * Backend manager configuration
 */
export interface BackendManagerConfig {
  host: string
  port: number
  apiKey?: string
  healthCheckUrl?: string
  startupTimeoutMs?: number
  healthCheckIntervalMs?: number
  maxRestartAttempts?: number
}

/**
 * Backend process information
 */
export interface BackendProcessInfo {
  status: BackendProcessStatus
  pid?: number
  uptime?: number
  lastError?: string
  restartCount: number
}

/**
 * BackendManager
 * Manages the Python backend subprocess lifecycle for Electron desktop application
 * - Spawns backend as direct subprocess (not PM2)
 * - Health checks via HTTP
 * - Graceful shutdown with SIGTERM
 * - Auto-restart on crash (optional)
 * - Stdout/stderr logging
 */
export class BackendManager {
  private process?: ChildProcess
  private status: BackendProcessStatus = BackendProcessStatus.STOPPED
  private config: Required<BackendManagerConfig>
  private healthCheckInterval?: NodeJS.Timeout
  private startTime?: number
  private restartCount = 0
  private isShuttingDown = false

  // Event listeners
  private onStatusChange?: (status: BackendProcessStatus) => void
  private onLog?: (type: 'stdout' | 'stderr', data: string) => void

  constructor(config: BackendManagerConfig) {
    this.config = {
      host: config.host,
      port: config.port,
      apiKey: config.apiKey || '',
      healthCheckUrl: config.healthCheckUrl || `http://${config.host}:${config.port}/health`,
      startupTimeoutMs: config.startupTimeoutMs || 30000,
      healthCheckIntervalMs: config.healthCheckIntervalMs || 10000,
      maxRestartAttempts: config.maxRestartAttempts || 3,
    }
  }

  /**
   * Get project root directory
   */
  private getProjectRoot(): string {
    if (app.isPackaged) {
      // In production, backend is bundled in resources/backend/
      return join(process.resourcesPath, 'backend')
    } else {
      // In development, go up from ui directory to project root
      return join(__dirname, '../../..')
    }
  }

  /**
   * Get backend executable path and arguments
   */
  private getBackendCommand(): { command: string; args: string[] } {
    const projectRoot = this.getProjectRoot()

    if (app.isPackaged) {
      // Production: Use bundled executable
      const platform = process.platform
      let executablePath: string

      if (platform === 'win32') {
        executablePath = join(projectRoot, 'automagik-omni-backend.exe')
      } else if (platform === 'darwin') {
        executablePath = join(projectRoot, 'automagik-omni-backend')
      } else {
        // Linux
        executablePath = join(projectRoot, 'automagik-omni-backend')
      }

      if (!existsSync(executablePath)) {
        throw new Error(`Backend executable not found at: ${executablePath}`)
      }

      return {
        command: executablePath,
        args: ['start', '--host', this.config.host, '--port', this.config.port.toString()],
      }
    } else {
      // Development: Use uv run python
      return {
        command: 'uv',
        args: [
          'run',
          'python',
          '-m',
          'src.cli.main_cli',
          'start',
          '--host',
          this.config.host,
          '--port',
          this.config.port.toString(),
        ],
      }
    }
  }

  /**
   * Start the backend process
   */
  async start(): Promise<void> {
    if (this.status === BackendProcessStatus.RUNNING) {
      console.log('Backend is already running')
      return
    }

    if (this.status === BackendProcessStatus.STARTING) {
      console.log('Backend is already starting')
      return
    }

    this.setStatus(BackendProcessStatus.STARTING)

    try {
      const { command, args } = this.getBackendCommand()
      const projectRoot = this.getProjectRoot()

      console.log(`Starting backend: ${command} ${args.join(' ')}`)
      console.log(`Working directory: ${projectRoot}`)

      // Spawn the backend process
      this.process = spawn(command, args, {
        cwd: projectRoot,
        env: {
          ...process.env,
          AUTOMAGIK_OMNI_API_HOST: this.config.host,
          AUTOMAGIK_OMNI_API_PORT: this.config.port.toString(),
          AUTOMAGIK_OMNI_API_KEY: this.config.apiKey,
          // Ensure Python output is not buffered
          PYTHONUNBUFFERED: '1',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      })

      this.startTime = Date.now()

      // Handle process stdout
      this.process.stdout?.on('data', (data: Buffer) => {
        const message = data.toString()
        console.log(`[Backend stdout]: ${message}`)
        this.onLog?.('stdout', message)
      })

      // Handle process stderr
      this.process.stderr?.on('data', (data: Buffer) => {
        const message = data.toString()
        console.error(`[Backend stderr]: ${message}`)
        this.onLog?.('stderr', message)
      })

      // Handle process exit
      this.process.on('exit', (code, signal) => {
        console.log(`Backend process exited with code ${code}, signal ${signal}`)
        this.handleProcessExit(code, signal)
      })

      // Handle process errors
      this.process.on('error', (error) => {
        console.error('Backend process error:', error)
        this.setStatus(BackendProcessStatus.ERROR)
      })

      // Wait for backend to be healthy
      await this.waitForHealthy()

      this.setStatus(BackendProcessStatus.RUNNING)
      this.startHealthCheck()

      console.log('Backend started successfully')
    } catch (error) {
      this.setStatus(BackendProcessStatus.ERROR)
      throw error
    }
  }

  /**
   * Stop the backend process
   */
  async stop(): Promise<void> {
    if (!this.process || this.status === BackendProcessStatus.STOPPED) {
      console.log('Backend is not running')
      return
    }

    this.isShuttingDown = true
    this.setStatus(BackendProcessStatus.STOPPING)
    this.stopHealthCheck()

    try {
      // Send SIGTERM for graceful shutdown
      console.log('Sending SIGTERM to backend process...')
      this.process.kill('SIGTERM')

      // Wait for process to exit (with timeout)
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          console.warn('Backend did not stop gracefully, forcing SIGKILL...')
          this.process?.kill('SIGKILL')
          reject(new Error('Backend process did not stop within timeout'))
        }, 10000)

        this.process?.on('exit', () => {
          clearTimeout(timeout)
          resolve()
        })
      })

      this.process = undefined
      this.startTime = undefined
      this.setStatus(BackendProcessStatus.STOPPED)

      console.log('Backend stopped successfully')
    } catch (error) {
      console.error('Error stopping backend:', error)
      this.process = undefined
      this.startTime = undefined
      this.setStatus(BackendProcessStatus.STOPPED)
    } finally {
      this.isShuttingDown = false
    }
  }

  /**
   * Restart the backend process
   */
  async restart(): Promise<void> {
    console.log('Restarting backend...')
    await this.stop()
    await new Promise((resolve) => setTimeout(resolve, 2000))
    await this.start()
  }

  /**
   * Check if backend is healthy via HTTP health endpoint
   */
  private async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(this.config.healthCheckUrl, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      })
      return response.ok
    } catch (error) {
      return false
    }
  }

  /**
   * Wait for backend to be healthy (with timeout)
   */
  private async waitForHealthy(): Promise<void> {
    const startTime = Date.now()
    const timeout = this.config.startupTimeoutMs

    console.log(`Waiting for backend to be healthy (timeout: ${timeout}ms)...`)

    while (Date.now() - startTime < timeout) {
      const healthy = await this.checkHealth()

      if (healthy) {
        const elapsed = Date.now() - startTime
        console.log(`Backend is healthy (took ${elapsed}ms)`)
        return
      }

      // Check if process is still running
      if (!this.process || this.status === BackendProcessStatus.ERROR) {
        throw new Error('Backend process exited before becoming healthy')
      }

      // Wait before next check
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }

    throw new Error(`Backend did not become healthy within ${timeout}ms`)
  }

  /**
   * Start periodic health checks
   */
  private startHealthCheck(): void {
    this.stopHealthCheck()

    this.healthCheckInterval = setInterval(async () => {
      const healthy = await this.checkHealth()

      if (!healthy && this.status === BackendProcessStatus.RUNNING) {
        console.warn('Backend health check failed')
        // Optionally trigger restart or notification
      }
    }, this.config.healthCheckIntervalMs)
  }

  /**
   * Stop periodic health checks
   */
  private stopHealthCheck(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
      this.healthCheckInterval = undefined
    }
  }

  /**
   * Handle process exit
   */
  private handleProcessExit(code: number | null, signal: string | null): void {
    this.stopHealthCheck()

    if (this.isShuttingDown) {
      // Expected shutdown
      this.setStatus(BackendProcessStatus.STOPPED)
      return
    }

    // Unexpected exit - potentially restart
    console.warn(`Backend exited unexpectedly (code: ${code}, signal: ${signal})`)
    this.setStatus(BackendProcessStatus.ERROR)

    // Auto-restart if enabled and under max attempts
    if (this.restartCount < this.config.maxRestartAttempts) {
      this.restartCount++
      console.log(`Auto-restarting backend (attempt ${this.restartCount}/${this.config.maxRestartAttempts})...`)

      setTimeout(() => {
        this.start().catch((error) => {
          console.error('Failed to auto-restart backend:', error)
        })
      }, 5000)
    } else {
      console.error('Max restart attempts reached, giving up')
    }
  }

  /**
   * Get current backend status
   */
  getStatus(): BackendProcessInfo {
    return {
      status: this.status,
      pid: this.process?.pid,
      uptime: this.startTime ? Date.now() - this.startTime : undefined,
      restartCount: this.restartCount,
    }
  }

  /**
   * Set status and notify listeners
   */
  private setStatus(status: BackendProcessStatus): void {
    this.status = status
    this.onStatusChange?.(status)
  }

  /**
   * Register status change listener
   */
  onStatusChangeListener(callback: (status: BackendProcessStatus) => void): void {
    this.onStatusChange = callback
  }

  /**
   * Register log listener
   */
  onLogListener(callback: (type: 'stdout' | 'stderr', data: string) => void): void {
    this.onLog = callback
  }

  /**
   * Cleanup on app quit
   */
  async cleanup(): Promise<void> {
    await this.stop()
  }
}
