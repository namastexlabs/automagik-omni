import { spawn, ChildProcess, execSync } from 'child_process'
import { app } from 'electron'
import { join, dirname } from 'path'
import { existsSync, mkdirSync } from 'fs'
import { Socket } from 'net'

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
  private isStarting = false // Startup lock to prevent simultaneous starts

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
        // Listen on all interfaces (0.0.0.0) to allow WSL/Docker to reach the backend
        // This is required when Evolution API runs in WSL Docker and needs to send webhooks
        args: ['start', '--host', '0.0.0.0', '--port', this.config.port.toString()],
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
          '127.0.0.1', // Force IPv4-only (same as production, see comment above)
          '--port',
          this.config.port.toString(),
        ],
      }
    }
  }

  /**
   * Kill any existing backend processes on port 8882
   * Platform-specific implementation:
   * - Windows: Use tasklist + taskkill
   * - macOS/Linux: Use lsof + kill
   *
   * IMPORTANT: Excludes current process's backend child process to prevent self-termination
   */
  private async killExistingBackends(): Promise<void> {
    console.log('🧹 Cleaning up existing backend processes...')

    // Protect current backend process from being killed
    const currentPid = this.process?.pid
    if (currentPid) {
      console.log(`⚠️  Protecting current backend process PID ${currentPid} from cleanup`)
    }

    try {
      if (process.platform === 'win32') {
        // Windows: Use tasklist + taskkill
        try {
          const output = execSync(
            'tasklist /FI "IMAGENAME eq automagik-omni-backend.exe" /FO CSV /NH',
            { encoding: 'utf-8' }
          )
          const pids = output
            .split('\n')
            .filter((line) => line.includes('automagik-omni-backend.exe'))
            .map((line) => {
              const match = line.match(/"(\d+)"/)
              return match ? match[1] : null
            })
            .filter(Boolean)
            .filter((pid) => pid !== currentPid?.toString()) // Exclude current process

          if (pids.length > 0) {
            console.log(
              `Found ${pids.length} existing backend process(es), killing: ${pids.join(', ')}`
            )

            // Strategy 1: Kill by process name (safer, handles race conditions)
            // This kills all instances regardless of PID changes during cleanup
            try {
              execSync('taskkill /F /IM automagik-omni-backend.exe', { timeout: 3000 })
              console.log('✅ Killed all backend processes by name')
            } catch (nameKillErr: any) {
              // If kill by name fails, fall back to PID-based cleanup
              // This can happen if processes already exited
              if (nameKillErr.message && nameKillErr.message.includes('not found')) {
                console.log('ℹ️ No backend processes found (already exited)')
              } else {
                console.warn('⚠️ Kill by name failed, attempting PID-based cleanup:', nameKillErr.message)

                // Strategy 2: Kill by PID with proper error handling
                for (const pid of pids) {
                  try {
                    // Try graceful termination first
                    execSync(`taskkill /PID ${pid} /T`, { timeout: 2000 })
                    console.log(`✅ Gracefully terminated PID ${pid}`)
                  } catch (gracefulErr: any) {
                    // If graceful fails, try force kill
                    try {
                      execSync(`taskkill /PID ${pid} /T /F`, { timeout: 2000 })
                      console.log(`✅ Force killed PID ${pid}`)
                    } catch (forceErr: any) {
                      // Check if process is already gone (not an error)
                      if (forceErr.message && forceErr.message.includes('not found')) {
                        console.log(`ℹ️ PID ${pid} already exited (race condition handled)`)
                      } else {
                        console.error(`❌ Failed to kill PID ${pid}:`, forceErr.message)
                      }
                    }
                  }

                  // Small delay between kill attempts to let processes exit cleanly
                  await new Promise((resolve) => setTimeout(resolve, 500))
                }
              }
            }

            // Wait for processes to actually terminate and release port
            await new Promise((resolve) => setTimeout(resolve, 1000))
          } else {
            console.log('No existing backend processes found')
          }

        } catch (err) {
          // tasklist returns error if no processes found, that's OK
          console.log('No existing backend processes found')
        }
      } else {
        // macOS/Linux: Use lsof + kill
        try {
          const output = execSync(`lsof -ti :8882`, { encoding: 'utf-8' })
          const pids = output.trim().split('\n').filter(Boolean)
            .filter((pid) => pid !== currentPid?.toString()) // Exclude current process

          if (pids.length > 0) {
            console.log(
              `Found ${pids.length} process(es) on port 8882, killing: ${pids.join(', ')}`
            )
            for (const pid of pids) {
              try {
                // Try SIGTERM first
                execSync(`kill -TERM ${pid}`, { timeout: 2000 })
                await new Promise((resolve) => setTimeout(resolve, 500))
                // Check if still alive, force kill
                try {
                  execSync(`kill -0 ${pid}`)
                  execSync(`kill -KILL ${pid}`)
                } catch {
                  // Process already dead, good
                }
              } catch (err) {
                console.error(`Failed to kill PID ${pid}:`, err)
              }
            }
          } else {
            console.log('No processes found on port 8882 (excluding current)')
          }
        } catch (err) {
          // lsof returns error if no processes found, that's OK
          console.log('No processes found on port 8882')
        }
      }
    } catch (err) {
      console.error('Error cleaning up backend processes:', err)
      // Don't throw - continue with startup anyway
    }
  }

  /**
   * Wait for a port to be released (becomes available)
   * Uses socket probe: ECONNREFUSED means port is free
   */
  private async waitForPortRelease(port: number, timeout: number): Promise<void> {
    console.log(`⏳ Waiting for port ${port} to be released...`)

    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      try {
        // Try to connect to the port
        await new Promise<void>((resolve, reject) => {
          const socket = new Socket()
          socket.setTimeout(200)

          socket.on('connect', () => {
            socket.destroy()
            reject(new Error('Port still in use'))
          })

          socket.on('error', (err: any) => {
            socket.destroy()
            if (err.code === 'ECONNREFUSED') {
              // Port is free!
              resolve()
            } else {
              reject(err)
            }
          })

          socket.on('timeout', () => {
            socket.destroy()
            reject(new Error('Connection timeout'))
          })

          socket.connect(port, '127.0.0.1')
        })

        // If we get here, port is free
        console.log(`✅ Port ${port} is now available`)
        return
      } catch (err: any) {
        // Port still in use or other error, wait and retry
        await new Promise((resolve) => setTimeout(resolve, 500))
      }
    }

    throw new Error(`Timeout waiting for port ${port} to be released`)
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

    // Startup lock: prevent simultaneous start() calls
    if (this.isStarting) {
      console.log('⚠️  Startup already in progress, ignoring duplicate start() call')
      return
    }

    this.isStarting = true
    this.setStatus(BackendProcessStatus.STARTING)

    try {
      // Clean up any existing backend processes before starting
      // NOTE: This will exclude this.process?.pid (protected from self-termination)
      await this.killExistingBackends()

      // Wait for port to be released
      await this.waitForPortRelease(8882, 5000)

      const { command, args } = this.getBackendCommand()
      const projectRoot = this.getProjectRoot()

      console.log(`Starting backend: ${command} ${args.join(' ')}`)
      console.log(`Working directory: ${projectRoot}`)

      // Get persistent data directory for SQLite database
      // app.getPath('userData') provides OS-appropriate location:
      // - Windows: C:\Users\<user>\AppData\Roaming\AutomagikOmni
      // - macOS: ~/Library/Application Support/AutomagikOmni
      // - Linux: ~/.config/AutomagikOmni
      const userDataPath = app.getPath('userData')
      const dbPath = join(userDataPath, 'data', 'automagik-omni.db')

      // Ensure database directory exists
      const dbDir = dirname(dbPath)
      if (!existsSync(dbDir)) {
        mkdirSync(dbDir, { recursive: true })
        console.log(`📁 Created database directory: ${dbDir}`)
      }

      console.log(`📁 Using persistent database path: ${dbPath}`)

      // Spawn the backend process
      this.process = spawn(command, args, {
        cwd: projectRoot,
        env: {
          ...process.env,
          AUTOMAGIK_OMNI_API_HOST: '0.0.0.0', // Force listen on all interfaces for WSL/Docker access
          AUTOMAGIK_OMNI_API_PORT: this.config.port.toString(),
          AUTOMAGIK_OMNI_API_KEY: this.config.apiKey,
          // Use persistent SQLite database path in user's AppData/Library/config directory
          AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH: dbPath,
          // Skip legacy Hive API health check for packaged Omni-only deployments
          AUTOMAGIK_OMNI_SKIP_LEGACY_HEALTH_CHECK: 'true',
          // Enable desktop mode to preserve localhost URLs for local Evolution API
          AUTOMAGIK_OMNI_DESKTOP_MODE: 'true',
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

      // NEW: Wait for backend API to confirm it's ready
      // This prevents race condition where health check passes before API finishes initialization
      const apiReady = await this.waitForUvicornLog(
        /API ready - use \/api\/v1\/instances to create instances/,
        10000 // 10 second timeout
      )

      if (!apiReady) {
        throw new Error('Backend failed to initialize (API did not become ready)')
      }

      // Wait for backend to be healthy
      await this.waitForHealthy()

      this.setStatus(BackendProcessStatus.RUNNING)
      this.startHealthCheck()

      console.log('✅ Backend started successfully')
    } catch (error) {
      this.setStatus(BackendProcessStatus.ERROR)
      throw error
    } finally {
      // Release startup lock
      this.isStarting = false
    }
  }

  /**
   * Stop the backend process
   * Windows-specific: Uses taskkill for reliable process termination
   */
  async stop(): Promise<void> {
    if (!this.process || this.status === BackendProcessStatus.STOPPED) {
      console.log('Backend is not running')
      return
    }

    this.isShuttingDown = true
    this.setStatus(BackendProcessStatus.STOPPING)
    this.stopHealthCheck()

    const pid = this.process.pid

    try {
      // Platform-specific termination strategy
      if (process.platform === 'win32' && pid) {
        console.log(`Stopping backend process (PID: ${pid}) on Windows...`)

        // Windows: Use taskkill with /T flag to terminate process tree
        // This ensures all child processes are also terminated
        try {
          // Force kill immediately with /F flag (more reliable for app quit)
          console.log(`Force killing PID ${pid} and all children...`)
          execSync(`taskkill /PID ${pid} /T /F`, { timeout: 3000 })
          console.log(`✅ Backend process ${pid} force killed`)
        } catch (error: any) {
          // If taskkill fails, process may already be gone
          if (error.message && error.message.includes('not found')) {
            console.log(`Process ${pid} already exited`)
          } else {
            console.warn(`taskkill error (may be harmless):`, error.message)
          }
        }

        // Also kill all instances by name to catch any orphaned processes
        try {
          execSync('taskkill /F /IM automagik-omni-backend.exe', { timeout: 2000 })
          console.log('✅ Killed all backend processes by name (cleanup)')
        } catch (err: any) {
          // Ignore errors - processes may already be gone
          if (!err.message?.includes('not found')) {
            console.log('ℹ️ No additional backend processes to clean up')
          }
        }
      } else {
        // Unix/macOS: Use SIGTERM then SIGKILL
        console.log(`Sending SIGTERM to backend process (PID: ${pid})...`)
        this.process.kill('SIGTERM')

        // Wait for process to exit (with timeout)
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => {
            console.warn('Backend did not stop gracefully, forcing SIGKILL...')
            this.process?.kill('SIGKILL')
            // Don't reject - force kill should work
            setTimeout(() => resolve(), 1000)
          }, 5000)

          this.process?.once('exit', () => {
            clearTimeout(timeout)
            resolve()
          })
        })
      }

      this.process = undefined
      this.startTime = undefined
      this.setStatus(BackendProcessStatus.STOPPED)

      console.log('✅ Backend stopped successfully')
    } catch (error) {
      console.error('❌ Error stopping backend:', error)
      // Even on error, clean up references
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
   * Wait for uvicorn to confirm it's listening via log output
   * This prevents race condition where HTTP health check passes but uvicorn
   * hasn't finished binding all interfaces (IPv4/IPv6 dual-stack issue on Windows)
   */
  private async waitForUvicornLog(pattern: RegExp, timeout: number): Promise<boolean> {
    console.log(`⏳ Waiting for backend ready log (pattern: ${pattern.source})...`)

    return new Promise((resolve) => {
      const startTime = Date.now()
      let logBuffer = ''

      const checkTimeout = () => {
        if (Date.now() - startTime > timeout) {
          console.error('❌ Timeout waiting for uvicorn ready log')
          resolve(false)
          return true
        }
        return false
      }

      const timeoutId = setInterval(() => {
        if (checkTimeout()) {
          clearInterval(timeoutId)
        }
      }, 500)

      // Listen to backend stdout
      const stdoutHandler = (data: Buffer) => {
        const output = data.toString()
        logBuffer += output

        // Check for backend ready patterns
        if (pattern.test(logBuffer)) {
          console.log(`✅ Backend confirmed ready (matched pattern: ${pattern.source})`)
          console.log(`   Detected in log: ${output.trim()}`)
          clearInterval(timeoutId)
          this.process?.stdout?.removeListener('data', stdoutHandler)
          this.process?.removeListener('exit', exitHandler)
          resolve(true)
        }

        // Also check for fatal errors
        if (
          output.includes('error while attempting to bind') ||
          output.includes('Address already in use') ||
          output.includes('[Errno 10048]') ||
          output.includes('WSAEADDRINUSE')
        ) {
          console.error('❌ Uvicorn binding error detected in logs')
          clearInterval(timeoutId)
          this.process?.stdout?.removeListener('data', stdoutHandler)
          this.process?.removeListener('exit', exitHandler)
          resolve(false)
        }
      }

      // Attach listener
      if (this.process?.stdout) {
        this.process.stdout.on('data', stdoutHandler)
      } else {
        console.error('❌ Backend process has no stdout')
        clearInterval(timeoutId)
        resolve(false)
      }

      // Handle process exit during wait
      const exitHandler = (code: number | null) => {
        console.error(`❌ Backend exited with code ${code} before uvicorn ready`)
        clearInterval(timeoutId)
        this.process?.stdout?.removeListener('data', stdoutHandler)
        resolve(false)
      }

      this.process?.once('exit', exitHandler)
    })
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
