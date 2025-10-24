import { exec } from 'child_process'
import { promisify } from 'util'
import { app } from 'electron'
import { join } from 'path'
import { existsSync, readFileSync } from 'fs'
import type { BackendStatus, HealthCheck, BackendConfig } from '@/lib/conveyor/schemas/backend-schema'
import type { BackendManager } from './backend-manager'

const execAsync = promisify(exec)

/**
 * Backend Monitor
 * Manages the lifecycle of Automagik Omni backend services
 * - PM2 process management
 * - Health checks
 * - Configuration management
 * - Log streaming
 */
export class BackendMonitor {
  private healthCheckInterval?: NodeJS.Timeout
  private readonly healthCheckIntervalMs = 10000 // 10 seconds
  private readonly healthCheckTimeoutMs = 30000 // 30 seconds
  private isStarting = false
  private isStopping = false
  private backendManager?: BackendManager

  // Cache PM2 availability check (checked once at initialization, not every 10 seconds)
  private static pm2Available: boolean | null = null

  // Default configuration
  private config: BackendConfig = {
    apiHost: 'localhost',
    apiPort: 8882, // Automagik Omni default port
    apiKey: '',
    databaseUrl: undefined,
    sqlitePath: undefined,
    enableTracing: false,
    logLevel: 'INFO',
  }

  constructor(backendManager?: BackendManager) {
    this.backendManager = backendManager
    // Load configuration from .env file and environment
    this.loadConfig()
  }

  /**
   * Get project root (parent of ui directory)
   */
  private getProjectRoot(): string {
    if (app.isPackaged) {
      // In production, use resources path
      return join(process.resourcesPath, 'backend')
    } else {
      // In development, go up one level from ui directory
      return join(__dirname, '../../..')
    }
  }

  /**
   * Load configuration from .env file and environment variables
   */
  private loadConfig(): void {
    const projectRoot = this.getProjectRoot()
    const envPath = join(projectRoot, '.env')

    // Load .env file if it exists
    if (existsSync(envPath)) {
      try {
        const envContent = readFileSync(envPath, 'utf-8')
        const envVars: Record<string, string> = {}

        // Parse .env file manually (simple key=value parser)
        envContent.split('\n').forEach((line) => {
          const trimmed = line.trim()
          if (trimmed && !trimmed.startsWith('#')) {
            const [key, ...valueParts] = trimmed.split('=')
            if (key && valueParts.length > 0) {
              // Remove quotes from value
              let value = valueParts.join('=').trim()
              value = value.replace(/^["']|["']$/g, '')
              envVars[key.trim()] = value
            }
          }
        })

        // Apply configuration from .env (environment variables take precedence)
        this.config = {
          apiHost:
            process.env.AUTOMAGIK_OMNI_API_HOST ||
            envVars.AUTOMAGIK_OMNI_API_HOST ||
            'localhost',
          apiPort: parseInt(
            process.env.AUTOMAGIK_OMNI_API_PORT ||
              envVars.AUTOMAGIK_OMNI_API_PORT ||
              '8882'
          ),
          apiKey:
            process.env.AUTOMAGIK_OMNI_API_KEY || envVars.AUTOMAGIK_OMNI_API_KEY || '',
          databaseUrl:
            process.env.AUTOMAGIK_OMNI_DATABASE_URL || envVars.AUTOMAGIK_OMNI_DATABASE_URL,
          sqlitePath:
            process.env.AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH ||
            envVars.AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH,
          enableTracing:
            (process.env.AUTOMAGIK_OMNI_ENABLE_TRACING ||
              envVars.AUTOMAGIK_OMNI_ENABLE_TRACING) === 'true',
          logLevel: process.env.LOG_LEVEL || envVars.LOG_LEVEL || 'INFO',
        }

        console.warn('Loaded configuration from .env:', {
          apiHost: this.config.apiHost,
          apiPort: this.config.apiPort,
          hasApiKey: !!this.config.apiKey,
        })
      } catch (error) {
        console.error('Error loading .env file:', error)
      }
    } else {
      // Fallback to environment variables only
      this.config = {
        apiHost: process.env.AUTOMAGIK_OMNI_API_HOST || 'localhost',
        apiPort: parseInt(process.env.AUTOMAGIK_OMNI_API_PORT || '8882'),
        apiKey: process.env.AUTOMAGIK_OMNI_API_KEY || '',
        databaseUrl: process.env.AUTOMAGIK_OMNI_DATABASE_URL,
        sqlitePath: process.env.AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH,
        enableTracing: process.env.AUTOMAGIK_OMNI_ENABLE_TRACING === 'true',
        logLevel: process.env.LOG_LEVEL || 'INFO',
      }
    }
  }

  /**
   * Get current backend status
   */
  async getStatus(): Promise<BackendStatus> {
    try {
      // Check if PM2 is available first
      const pm2Available = await this.checkCommand('pm2')
      const mode: 'pm2' | 'direct' = pm2Available ? 'pm2' : 'direct'

      const pm2Status = await this.getPM2Status()
      const apiHealth = await this.checkAPIHealth()
      const discordHealth = await this.checkDiscordHealth()

      // Check if API is running (either via PM2 or direct process)
      const apiRunningViaPM2 = pm2Status.some(
        (p) => p.name.includes('api') && p.status === 'online'
      )
      const apiRunning = apiRunningViaPM2 || apiHealth // If health check passes, API is running

      return {
        api: {
          running: apiRunning,
          healthy: apiHealth,
          port: this.config.apiPort,
          url: `http://${this.config.apiHost}:${this.config.apiPort}`,
        },
        discord: {
          running: pm2Status.some((p) => p.name.includes('discord') && p.status === 'online'),
          healthy: discordHealth,
        },
        pm2: {
          running: pm2Status.length > 0,
          processes: pm2Status,
          mode,
        },
      }
    } catch (_error) {
      console.error('Error getting backend status:', _error)
      return {
        api: { running: false, healthy: false, port: this.config.apiPort, url: '' },
        discord: { running: false, healthy: false },
        pm2: { running: false, processes: [], mode: 'direct' },
      }
    }
  }

  /**
   * Check if a command exists in PATH (cached for PM2)
   * Platform-specific: uses 'where' on Windows, 'which' on Unix
   */
  private async checkCommand(command: string): Promise<boolean> {
    // Use cached result for PM2 checks to avoid spamming every 10 seconds
    if (command === 'pm2' && BackendMonitor.pm2Available !== null) {
      return BackendMonitor.pm2Available
    }

    try {
      const checkCmd = process.platform === 'win32' ? 'where' : 'which'
      await execAsync(`${checkCmd} ${command}`)

      // Cache PM2 availability
      if (command === 'pm2') {
        BackendMonitor.pm2Available = true
      }
      return true
    } catch {
      // Cache PM2 unavailability
      if (command === 'pm2') {
        BackendMonitor.pm2Available = false
      }
      return false
    }
  }

  /**
   * Get status for direct process (non-PM2) backend
   * Returns PM2-like status object for compatibility
   */
  private getDirectProcessStatus(): Array<{ name: string; status: string; cpu: number; memory: number }> {
    if (!this.backendManager) {
      return []
    }

    const processInfo = this.backendManager.getStatus()

    // If backend process is running, return a PM2-like status entry
    if (processInfo.status === 'running' && processInfo.pid) {
      return [
        {
          name: 'automagik-omni-api',
          status: 'online',
          cpu: 0, // CPU/memory metrics not available for direct process
          memory: 0,
        }
      ]
    }

    return []
  }

  /**
   * Get PM2 process status with fallback to direct process
   */
  private async getPM2Status(): Promise<
    Array<{ name: string; status: string; cpu: number; memory: number }>
  > {
    try {
      // Check if PM2 is available (cached after first check)
      const pm2Available = await this.checkCommand('pm2')

      if (!pm2Available) {
        // PM2 not available - fallback to direct process status (silently)
        return this.getDirectProcessStatus()
      }

      // PM2 is available - try to get PM2 process list
      const { stdout } = await execAsync('pm2 jlist', {
        cwd: this.getProjectRoot(),
      })

      const processes = JSON.parse(stdout)
      return processes
        .filter((p: any) => p.name?.includes('automagik-omni'))
        .map((p: any) => ({
          name: p.name,
          status: p.pm2_env?.status || 'unknown',
          cpu: p.monit?.cpu || 0,
          memory: p.monit?.memory || 0,
        }))
    } catch (_error) {
      console.error('Error getting PM2 status:', _error)
      // Fallback to direct process status on any error
      return this.getDirectProcessStatus()
    }
  }

  /**
   * Check if API is healthy
   */
  private async checkAPIHealth(): Promise<boolean> {
    try {
      const response = await fetch(`http://${this.config.apiHost}:${this.config.apiPort}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      })
      return response.ok
    } catch {
      return false
    }
  }

  /**
   * Check if Discord bot is healthy
   */
  private async checkDiscordHealth(): Promise<boolean> {
    try {
      const processes = await this.getPM2Status()
      return processes.some((p) => p.name.includes('discord') && p.status === 'online')
    } catch {
      return false
    }
  }

  /**
   * Perform comprehensive health check
   */
  async healthCheck(): Promise<HealthCheck> {
    try {
      const apiHealth = await this.checkAPIHealth()
      const discordHealth = await this.checkDiscordHealth()
      const dbHealth = await this.checkDatabaseHealth()

      return {
        healthy: apiHealth && dbHealth,
        timestamp: new Date().toISOString(),
        services: {
          api: apiHealth,
          discord: discordHealth,
          database: dbHealth,
        },
      }
    } catch (error) {
      return {
        healthy: false,
        timestamp: new Date().toISOString(),
        services: {
          api: false,
          discord: false,
          database: false,
        },
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  /**
   * Check database health
   */
  private async checkDatabaseHealth(): Promise<boolean> {
    try {
      const response = await fetch(`http://${this.config.apiHost}:${this.config.apiPort}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      })

      if (!response.ok) return false

      const data = await response.json()
      return data.database === 'ok' || data.status === 'healthy'
    } catch {
      return false
    }
  }

  /**
   * Start backend services using make start-local (PM2)
   */
  async start(): Promise<{ success: boolean; message: string }> {
    if (this.isStarting) {
      return { success: false, message: 'Backend is already starting' }
    }

    if (this.isStopping) {
      return { success: false, message: 'Backend is stopping, please wait' }
    }

    this.isStarting = true

    try {
      const projectRoot = this.getProjectRoot()

      // Use make start-local to start via PM2
      const { stdout, stderr } = await execAsync('make start-local', {
        cwd: projectRoot,
        env: {
          ...process.env,
          AUTOMAGIK_OMNI_API_HOST: this.config.apiHost,
          AUTOMAGIK_OMNI_API_PORT: this.config.apiPort.toString(),
          AUTOMAGIK_OMNI_API_KEY: this.config.apiKey,
        },
      })

      // eslint-disable-next-line no-console
      console.log('Backend start output:', stdout)
      if (stderr) console.error('Backend start stderr:', stderr)

      // Wait for services to be healthy
      const healthy = await this.waitForHealthy()

      if (healthy) {
        this.startHealthCheckInterval()
        return { success: true, message: 'Backend services started successfully via PM2' }
      } else {
        return {
          success: false,
          message: 'Backend services started but health check failed',
        }
      }
    } catch (error) {
      console.error('Error starting backend:', error)
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    } finally {
      this.isStarting = false
    }
  }

  /**
   * Stop backend services using make stop-local
   */
  async stop(): Promise<{ success: boolean; message: string }> {
    if (this.isStopping) {
      return { success: false, message: 'Backend is already stopping' }
    }

    this.isStopping = true
    this.stopHealthCheckInterval()

    try {
      const projectRoot = this.getProjectRoot()

      // Use make stop-local to stop PM2 services
      const { stdout, stderr } = await execAsync('make stop-local', {
        cwd: projectRoot,
      })

      // eslint-disable-next-line no-console
      console.log('Backend stop output:', stdout)
      if (stderr) console.error('Backend stop stderr:', stderr)

      return { success: true, message: 'Backend services stopped successfully' }
    } catch (error) {
      console.error('Error stopping backend:', error)
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    } finally {
      this.isStopping = false
    }
  }

  /**
   * Restart backend services
   */
  async restart(): Promise<{ success: boolean; message: string }> {
    const stopResult = await this.stop()
    if (!stopResult.success) {
      return stopResult
    }

    // Wait a bit before restarting
    await new Promise((resolve) => setTimeout(resolve, 2000))

    return await this.start()
  }

  /**
   * Wait for backend to be healthy (with timeout)
   */
  private async waitForHealthy(): Promise<boolean> {
    const startTime = Date.now()

    while (Date.now() - startTime < this.healthCheckTimeoutMs) {
      const health = await this.healthCheck()
      if (health.healthy) {
        return true
      }

      // Wait 2 seconds before next check
      await new Promise((resolve) => setTimeout(resolve, 2000))
    }

    return false
  }

  /**
   * Start periodic health checks
   */
  private startHealthCheckInterval(): void {
    this.stopHealthCheckInterval()

    this.healthCheckInterval = setInterval(async () => {
      const health = await this.healthCheck()
      if (!health.healthy) {
        console.warn('Backend health check failed:', health)
        // Could emit event to notify renderer process
      }
    }, this.healthCheckIntervalMs)
  }

  /**
   * Stop periodic health checks
   */
  private stopHealthCheckInterval(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval)
      this.healthCheckInterval = undefined
    }
  }

  /**
   * Get backend logs
   */
  async getLogs(
    service: 'api' | 'discord' | 'pm2' | 'all',
    lines = 100,
    tail = false
  ): Promise<{ service: string; output: string; error?: string }> {
    try {
      const projectRoot = this.getProjectRoot()
      let command: string

      if (service === 'all' || service === 'pm2') {
        command = `make logs`
      } else {
        command = `pm2 logs automagik-omni-${service} --lines ${lines} ${tail ? '--raw' : '--nostream'}`
      }

      const { stdout, stderr } = await execAsync(command, {
        cwd: projectRoot,
      })

      return {
        service,
        output: stdout,
        error: stderr || undefined,
      }
    } catch (error) {
      return {
        service,
        output: '',
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  /**
   * Get current configuration
   */
  getConfig(): BackendConfig {
    return { ...this.config }
  }

  /**
   * Update configuration
   */
  updateConfig(updates: Partial<BackendConfig>): { success: boolean; message: string } {
    try {
      this.config = { ...this.config, ...updates }
      return { success: true, message: 'Configuration updated successfully' }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  /**
   * Cleanup on app quit
   */
  async cleanup(): Promise<void> {
    this.stopHealthCheckInterval()
    // Optionally stop backend services
    // await this.stop()
  }
}
