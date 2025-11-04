import { spawn, ChildProcess, execSync } from 'child_process'
import { app } from 'electron'
import { join } from 'path'
import { existsSync, writeFileSync, mkdirSync } from 'fs'
import { randomBytes } from 'crypto'

/**
 * Evolution API process status enum
 */
export enum EvolutionProcessStatus {
  STOPPED = 'stopped',
  STARTING = 'starting',
  RUNNING = 'running',
  STOPPING = 'stopping',
  ERROR = 'error',
}

/**
 * Evolution API manager configuration
 */
export interface EvolutionManagerConfig {
  port: number
  databasePath: string
  apiKey?: string
  healthCheckUrl?: string
  startupTimeoutMs?: number
  healthCheckIntervalMs?: number
  maxRestartAttempts?: number
}

/**
 * Evolution API process information
 */
export interface EvolutionProcessInfo {
  status: EvolutionProcessStatus
  pid?: number
  uptime?: number
  lastError?: string
  restartCount: number
  port: number
  apiKey: string
}

/**
 * EvolutionManager
 * Manages the Evolution API (Node.js) subprocess lifecycle for Electron desktop application
 * - Spawns Evolution API via bundled Node.js runtime
 * - Manages SQLite database in user data directory
 * - Health checks via HTTP
 * - Graceful shutdown with SIGTERM
 * - Auto-restart on crash (optional)
 * - Stdout/stderr logging
 */
export class EvolutionManager {
  private process?: ChildProcess
  private status: EvolutionProcessStatus = EvolutionProcessStatus.STOPPED
  private config: Required<EvolutionManagerConfig>
  private healthCheckInterval?: NodeJS.Timeout
  private startTime?: number
  private restartCount = 0
  private isShuttingDown = false
  private isStarting = false
  private apiKey: string

  // Event listeners
  private onStatusChange?: (status: EvolutionProcessStatus) => void
  private onLog?: (type: 'stdout' | 'stderr', data: string) => void

  constructor(config: EvolutionManagerConfig) {
    // Generate or load API key
    this.apiKey = config.apiKey || this.loadOrGenerateApiKey()

    this.config = {
      port: config.port,
      databasePath: config.databasePath,
      apiKey: this.apiKey,
      healthCheckUrl: config.healthCheckUrl || `http://localhost:${config.port}/health`,
      startupTimeoutMs: config.startupTimeoutMs || 45000, // Evolution API takes longer to start
      healthCheckIntervalMs: config.healthCheckIntervalMs || 10000,
      maxRestartAttempts: config.maxRestartAttempts || 3,
    }
  }

  /**
   * Load or generate Evolution API key and store in user data
   */
  private loadOrGenerateApiKey(): string {
    const userDataPath = app.getPath('userData')
    const keyFilePath = join(userDataPath, 'evolution-api-key.txt')

    if (existsSync(keyFilePath)) {
      const fs = require('fs')
      return fs.readFileSync(keyFilePath, 'utf-8').trim()
    }

    // Generate new API key (32 bytes = 64 hex chars)
    const newKey = randomBytes(32).toString('hex').toUpperCase()
    mkdirSync(userDataPath, { recursive: true })
    writeFileSync(keyFilePath, newKey, 'utf-8')
    console.log('🔑 Generated new Evolution API key')
    return newKey
  }

  /**
   * Get Evolution API resources directory
   */
  private getEvolutionDir(): string {
    if (app.isPackaged) {
      // Production: Evolution API is bundled in resources/evolution/
      return join(process.resourcesPath, 'evolution')
    } else {
      // Development: use dist-evolution or resources/evolution-api
      const distEvolution = join(__dirname, '../../../dist-evolution')
      if (existsSync(distEvolution)) {
        return distEvolution
      }
      // Fallback to source
      return join(__dirname, '../../../resources/evolution-api')
    }
  }

  /**
   * Get Node.js runtime path
   */
  private getNodePath(): string {
    if (app.isPackaged) {
      // Production: Node.js is bundled in resources/nodejs/
      const nodejsDir = join(process.resourcesPath, 'nodejs')
      const platform = process.platform
      const nodeBinary = platform === 'win32' ? 'node.exe' : 'bin/node'
      return join(nodejsDir, nodeBinary)
    } else {
      // Development: use system Node.js
      return 'node'
    }
  }

  /**
   * Get Evolution API command and arguments
   */
  private getEvolutionCommand(): { command: string; args: string[]; env: NodeJS.ProcessEnv } {
    const nodePath = this.getNodePath()
    const evolutionDir = this.getEvolutionDir()
    const mainScript = join(evolutionDir, 'dist', 'main.mjs')

    if (!existsSync(mainScript)) {
      throw new Error(`Evolution API main script not found at: ${mainScript}`)
    }

    // Prepare environment variables from Evolution API .env.example defaults
    const userDataPath = app.getPath('userData')
    const evolutionDataDir = join(userDataPath, 'evolution-data')
    mkdirSync(evolutionDataDir, { recursive: true })

    const env: NodeJS.ProcessEnv = {
      ...process.env,

      // Server Configuration
      SERVER_NAME: 'evolution',
      SERVER_TYPE: 'http',
      SERVER_PORT: this.config.port.toString(),
      SERVER_URL: `http://localhost:${this.config.port}`,

      // Database - SQLite for desktop
      DATABASE_PROVIDER: 'sqlite',
      DATABASE_CONNECTION_URI: `file:${this.config.databasePath}`,
      DATABASE_CONNECTION_CLIENT_NAME: 'evolution_desktop',

      // Data Storage
      DATABASE_SAVE_DATA_INSTANCE: 'true',
      DATABASE_SAVE_DATA_NEW_MESSAGE: 'true',
      DATABASE_SAVE_MESSAGE_UPDATE: 'true',
      DATABASE_SAVE_DATA_CONTACTS: 'true',
      DATABASE_SAVE_DATA_CHATS: 'true',
      DATABASE_SAVE_DATA_LABELS: 'true',
      DATABASE_SAVE_DATA_HISTORIC: 'true',

      // Telemetry - Disabled for desktop
      TELEMETRY_ENABLED: 'false',
      SENTRY_DSN: '',
      PROMETHEUS_METRICS: 'false',

      // Logging
      LOG_LEVEL: 'ERROR,WARN,INFO',
      LOG_COLOR: 'true',
      LOG_BAILEYS: 'error',

      // CORS - Allow all origins for desktop app (Python backend communicates from null origin)
      CORS_ORIGIN: '*',
      CORS_METHODS: 'GET,POST,PUT,DELETE',
      CORS_CREDENTIALS: 'true',

      // Cache - Use local cache (no Redis for desktop)
      CACHE_REDIS_ENABLED: 'false',
      CACHE_LOCAL_ENABLED: 'true',

      // Authentication
      AUTHENTICATION_API_KEY: this.apiKey,
      AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES: 'true',

      // Delete instance on disconnect - disabled for desktop
      DEL_INSTANCE: 'false',

      // Session configuration
      CONFIG_SESSION_PHONE_CLIENT: 'Omni Desktop',
      CONFIG_SESSION_PHONE_NAME: 'Chrome',

      // QR Code configuration
      QRCODE_LIMIT: '30',
      QRCODE_COLOR: '#175197',

      // Disable external integrations by default
      WEBHOOK_GLOBAL_ENABLED: 'false',
      RABBITMQ_ENABLED: 'false',
      SQS_ENABLED: 'false',
      WEBSOCKET_ENABLED: 'false',
      KAFKA_ENABLED: 'false',
      PUSHER_ENABLED: 'false',
      TYPEBOT_ENABLED: 'false',
      CHATWOOT_ENABLED: 'false',
      OPENAI_ENABLED: 'false',
      DIFY_ENABLED: 'false',
      N8N_ENABLED: 'false',
      EVOAI_ENABLED: 'false',
      S3_ENABLED: 'false',

      // Language
      LANGUAGE: 'en',

      // Working directory for Evolution API to find its resources
      NODE_PATH: join(evolutionDir, 'node_modules'),
    }

    return {
      command: nodePath,
      args: [mainScript],
      env,
    }
  }

  /**
   * Kill any existing Evolution API processes on the configured port
   */
  private async killExistingEvolutionProcesses(): Promise<void> {
    console.log('🧹 Cleaning up existing Evolution API processes...')

    const currentPid = this.process?.pid
    if (currentPid) {
      console.log(`⚠️  Protecting current Evolution API process PID ${currentPid} from cleanup`)
    }

    try {
      if (process.platform === 'win32') {
        // Windows: Find node.exe listening on Evolution API port
        try {
          const output = execSync(`netstat -ano | findstr :${this.config.port}`, {
            encoding: 'utf-8',
          })
          const lines = output.split('\n').filter((line) => line.includes('LISTENING'))

          for (const line of lines) {
            const match = line.match(/\s+(\d+)\s*$/)
            if (match) {
              const pid = match[1]
              if (pid !== currentPid?.toString()) {
                try {
                  execSync(`taskkill /F /PID ${pid}`, { timeout: 3000 })
                  console.log(`✅ Killed existing process on port ${this.config.port}: PID ${pid}`)
                } catch (err: any) {
                  console.warn(`⚠️ Failed to kill PID ${pid}:`, err.message)
                }
              }
            }
          }
        } catch (err: any) {
          if (!err.message.includes('cannot find')) {
            console.warn('⚠️ Port cleanup failed:', err.message)
          }
        }
      } else {
        // macOS/Linux: Use lsof
        try {
          const output = execSync(`lsof -ti:${this.config.port}`, { encoding: 'utf-8' })
          const pids = output
            .split('\n')
            .filter(Boolean)
            .filter((pid) => pid !== currentPid?.toString())

          for (const pid of pids) {
            try {
              execSync(`kill -9 ${pid}`, { timeout: 3000 })
              console.log(`✅ Killed existing process on port ${this.config.port}: PID ${pid}`)
            } catch (err: any) {
              console.warn(`⚠️ Failed to kill PID ${pid}:`, err.message)
            }
          }
        } catch (err: any) {
          // lsof returns non-zero if no process found
          console.log('ℹ️ No existing Evolution API processes found')
        }
      }
    } catch (error: any) {
      console.warn('⚠️ Error during Evolution API cleanup:', error.message)
    }
  }

  /**
   * Initialize Prisma database schema for SQLite
   * Uses pre-built template database for faster initialization
   */
  private async initializeDatabase(): Promise<void> {
    const evolutionDir = this.getEvolutionDir()
    const templateDb = join(evolutionDir, 'evolution-template.db')
    const targetDb = this.config.databasePath

    console.log('🗄️  Initializing Evolution API database...')
    console.log('   Database:', targetDb)

    // Check if database already exists and is valid
    if (existsSync(targetDb)) {
      try {
        const fs = require('fs')
        const stats = fs.statSync(targetDb)
        if (stats.size > 0) {
          console.log('   ✅ Database already exists, skipping initialization')
          return
        }
      } catch (error) {
        console.warn('   ⚠️  Existing database appears corrupt, reinitializing...')
      }
    }

    // Ensure database directory exists
    const dbDir = require('path').dirname(targetDb)
    mkdirSync(dbDir, { recursive: true })

    // Copy template database if it exists
    if (existsSync(templateDb)) {
      try {
        const fs = require('fs')
        fs.copyFileSync(templateDb, targetDb)
        console.log('   ✅ Database initialized from template')
        return
      } catch (error: any) {
        console.warn('   ⚠️  Failed to copy template database:', error.message)
        console.warn('   Falling back to Prisma migration...')
      }
    }

    // Fallback: Run prisma db push if template doesn't exist
    console.log('   Running Prisma migration (first-time setup)...')
    const prismaPath = join(evolutionDir, 'node_modules', '.bin', 'prisma')
    const { env } = this.getEvolutionCommand()

    try {
      const pushProcess = spawn(
        prismaPath,
        ['db', 'push', '--schema', join(evolutionDir, 'prisma', 'sqlite-schema.prisma'), '--accept-data-loss'],
        {
          cwd: evolutionDir,
          env,
          stdio: 'inherit',
        }
      )

      await new Promise<void>((resolve, reject) => {
        pushProcess.on('exit', (code) => {
          if (code === 0) {
            console.log('   ✅ Database schema initialized via Prisma')
            resolve()
          } else {
            reject(new Error(`Prisma db push failed with code ${code}`))
          }
        })
        pushProcess.on('error', reject)
      })
    } catch (error: any) {
      console.error('   ❌ Failed to initialize database:', error.message)
      throw error
    }
  }

  /**
   * Start Evolution API process
   */
  /**
   * Check if port is available
   */
  private async isPortAvailable(port: number): Promise<boolean> {
    const net = require('net')
    return new Promise((resolve) => {
      const tester = net
        .createServer()
        .once('error', () => resolve(false))
        .once('listening', () => {
          tester.close(() => resolve(true))
        })
        .listen(port, '127.0.0.1')
    })
  }

  /**
   * Wait for port to be released
   */
  private async waitForPortRelease(port: number, timeoutMs: number = 5000): Promise<void> {
    const startTime = Date.now()
    while (Date.now() - startTime < timeoutMs) {
      if (await this.isPortAvailable(port)) {
        console.log(`✅ Port ${port} is now available`)
        return
      }
      await new Promise((resolve) => setTimeout(resolve, 500))
    }
    throw new Error(`Port ${port} is still in use after ${timeoutMs}ms`)
  }

  async start(): Promise<void> {
    if (this.isStarting) {
      throw new Error('Evolution API is already starting')
    }

    if (this.status === EvolutionProcessStatus.RUNNING) {
      console.log('Evolution API is already running')
      return
    }

    this.isStarting = true
    this.setStatus(EvolutionProcessStatus.STARTING)

    try {
      // Initialize database schema (idempotent - safe to run every time)
      await this.initializeDatabase()

      // Kill any existing Evolution API processes
      await this.killExistingEvolutionProcesses()

      // Wait for port to be released
      console.log(`⏳ Waiting for port ${this.config.port} to be available...`)
      await this.waitForPortRelease(this.config.port)

      // Get command and spawn process
      const { command, args, env } = this.getEvolutionCommand()
      const evolutionDir = this.getEvolutionDir()

      console.log('🚀 Starting Evolution API...')
      console.log('   Command:', command)
      console.log('   Args:', args)
      console.log('   Working Dir:', evolutionDir)
      console.log('   Port:', this.config.port)

      this.process = spawn(command, args, {
        cwd: evolutionDir,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
      })

      // Set up logging
      this.process.stdout?.on('data', (data) => {
        const message = data.toString()
        console.log('[Evolution API]', message)
        this.onLog?.('stdout', message)
      })

      this.process.stderr?.on('data', (data) => {
        const message = data.toString()
        console.error('[Evolution API Error]', message)
        this.onLog?.('stderr', message)
      })

      // Handle process exit
      this.process.on('exit', (code, signal) => {
        console.log(`Evolution API process exited: code=${code}, signal=${signal}`)
        this.handleProcessExit(code, signal)
      })

      // Wait for Evolution API to be ready
      await this.waitForReady()

      this.startTime = Date.now()
      this.setStatus(EvolutionProcessStatus.RUNNING)
      console.log('✅ Evolution API started successfully')
    } catch (error) {
      this.setStatus(EvolutionProcessStatus.ERROR)
      throw error
    } finally {
      this.isStarting = false
    }
  }

  /**
   * Wait for Evolution API to be ready by checking if port is accepting connections
   */
  private async waitForReady(): Promise<void> {
    const startTime = Date.now()
    const timeout = this.config.startupTimeoutMs
    const net = require('net')

    console.log(`⏳ Waiting for Evolution API to be ready (timeout: ${timeout}ms)...`)

    while (Date.now() - startTime < timeout) {
      try {
        // Try to connect to Evolution API port
        await new Promise<void>((resolve, reject) => {
          const socket = new net.Socket()
          const timer = setTimeout(() => {
            socket.destroy()
            reject(new Error('Connection timeout'))
          }, 2000)

          socket.on('connect', () => {
            clearTimeout(timer)
            socket.destroy()
            resolve()
          })

          socket.on('error', (err) => {
            clearTimeout(timer)
            reject(err)
          })

          socket.connect(this.config.port, 'localhost')
        })

        console.log('✅ Evolution API is accepting connections')
        // Give it an extra second to fully initialize
        await new Promise((resolve) => setTimeout(resolve, 1000))
        return
      } catch (error) {
        // Connection failed, retry
      }

      // Wait 1 second before retry
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }

    throw new Error(`Evolution API failed to start within ${timeout}ms`)
  }

  /**
   * Stop Evolution API process
   */
  async stop(): Promise<void> {
    if (this.status === EvolutionProcessStatus.STOPPED) {
      console.log('Evolution API is already stopped')
      return
    }

    this.isShuttingDown = true
    this.setStatus(EvolutionProcessStatus.STOPPING)

    console.log('🛑 Stopping Evolution API...')

    try {
      if (this.process && this.process.pid) {
        // Try graceful shutdown first
        this.process.kill('SIGTERM')

        // Wait up to 5 seconds for graceful shutdown
        await new Promise((resolve) => setTimeout(resolve, 5000))

        // Force kill if still running
        if (this.process && !this.process.killed) {
          console.warn('⚠️ Evolution API did not stop gracefully, force killing...')
          this.process.kill('SIGKILL')
        }
      }

      this.process = undefined
      this.startTime = undefined
      this.setStatus(EvolutionProcessStatus.STOPPED)
      console.log('✅ Evolution API stopped')
    } catch (error: any) {
      console.error('❌ Error stopping Evolution API:', error.message)
      throw error
    } finally {
      this.isShuttingDown = false
    }
  }

  /**
   * Restart Evolution API process
   */
  async restart(): Promise<void> {
    console.log('🔄 Restarting Evolution API...')
    await this.stop()
    await new Promise((resolve) => setTimeout(resolve, 2000)) // Wait 2s between stop and start
    await this.start()
  }

  /**
   * Get current status
   */
  getStatus(): EvolutionProcessInfo {
    return {
      status: this.status,
      pid: this.process?.pid,
      uptime: this.startTime ? Date.now() - this.startTime : undefined,
      restartCount: this.restartCount,
      port: this.config.port,
      apiKey: this.apiKey,
    }
  }

  /**
   * Cleanup on app quit
   */
  async cleanup(): Promise<void> {
    console.log('🧹 Cleaning up Evolution API...')
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
    }
    await this.stop()
  }

  /**
   * Set status and notify listeners
   */
  private setStatus(status: EvolutionProcessStatus): void {
    this.status = status
    this.onStatusChange?.(status)
  }

  /**
   * Handle process exit
   */
  private handleProcessExit(code: number | null, signal: NodeJS.Signals | null): void {
    if (this.isShuttingDown) {
      // Expected shutdown
      return
    }

    console.error(`❌ Evolution API process exited unexpectedly: code=${code}, signal=${signal}`)
    this.setStatus(EvolutionProcessStatus.ERROR)

    // Auto-restart if enabled and within attempt limit
    if (this.restartCount < this.config.maxRestartAttempts) {
      this.restartCount++
      console.log(`🔄 Auto-restarting Evolution API (attempt ${this.restartCount}/${this.config.maxRestartAttempts})...`)
      setTimeout(() => {
        this.start().catch((error) => {
          console.error('❌ Auto-restart failed:', error)
        })
      }, 5000)
    } else {
      console.error('❌ Max restart attempts reached, giving up')
    }
  }

  /**
   * Set event listeners
   */
  setEventListeners(listeners: {
    onStatusChange?: (status: EvolutionProcessStatus) => void
    onLog?: (type: 'stdout' | 'stderr', data: string) => void
  }): void {
    this.onStatusChange = listeners.onStatusChange
    this.onLog = listeners.onLog
  }
}
