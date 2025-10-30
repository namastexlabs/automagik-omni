import { handle } from '@/lib/main/shared'
import { EvolutionManager } from '@/lib/main/evolution-manager'
import { app } from 'electron'
import { join } from 'path'
import { config } from 'dotenv'
import { existsSync } from 'fs'

let evolutionManager: EvolutionManager | null = null

/**
 * Load .env file from project root
 */
function loadEnvConfig() {
  // Try to load .env from project root (3 levels up from ui/lib/conveyor/handlers/)
  const projectRoot = join(__dirname, '../../../../')
  const envPath = join(projectRoot, '.env')

  if (existsSync(envPath)) {
    config({ path: envPath })
    console.log('✅ Loaded .env file from:', envPath)
  } else {
    console.log('ℹ️  No .env file found, using defaults')
  }
}

/**
 * Initialize Evolution API manager singleton
 */
export const initEvolutionManager = () => {
  if (!evolutionManager) {
    // Load environment variables
    loadEnvConfig()

    const userDataPath = app.getPath('userData')
    const databasePath = join(userDataPath, 'evolution-data', 'evolution.db')

    // Read from environment variables with fallbacks
    const port = parseInt(process.env.EVOLUTION_API_PORT || '8080', 10)
    const apiKey = process.env.EVOLUTION_API_KEY || undefined

    console.log('🔧 Evolution API Configuration:')
    console.log('   Port:', port)
    console.log('   API Key:', apiKey ? '***' + apiKey.slice(-4) : '(auto-generate)')
    console.log('   Database:', databasePath)

    evolutionManager = new EvolutionManager({
      port,
      databasePath,
      apiKey, // Pass from .env
      healthCheckUrl: `http://localhost:${port}/health`,
      startupTimeoutMs: 45000, // Evolution API needs more time to initialize
      healthCheckIntervalMs: 10000,
      maxRestartAttempts: 3,
    })

    // Set up event listeners for logging
    evolutionManager.setEventListeners({
      onStatusChange: (status) => {
        console.log('Evolution API status changed:', status)
      },
      onLog: (type, data) => {
        if (type === 'stderr') {
          console.error('[Evolution API]', data)
        } else {
          console.log('[Evolution API]', data)
        }
      },
    })
  }
  return evolutionManager
}

/**
 * Get Evolution API manager instance
 */
const getManager = (): EvolutionManager => {
  if (!evolutionManager) {
    throw new Error('Evolution API manager not initialized')
  }
  return evolutionManager
}

/**
 * Register Evolution API IPC handlers
 */
export const registerEvolutionHandlers = () => {
  initEvolutionManager()

  // Start Evolution API
  handle('evolution:start', async () => {
    try {
      await getManager().start()
      return { success: true, message: 'Evolution API started successfully' }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  })

  // Stop Evolution API
  handle('evolution:stop', async () => {
    try {
      await getManager().stop()
      return { success: true, message: 'Evolution API stopped successfully' }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  })

  // Restart Evolution API
  handle('evolution:restart', async () => {
    try {
      await getManager().restart()
      return { success: true, message: 'Evolution API restarted successfully' }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  })

  // Get Evolution API status
  handle('evolution:status', async () => {
    return getManager().getStatus()
  })
}

/**
 * Cleanup Evolution API manager on app quit
 */
export const cleanupEvolutionManager = async () => {
  if (evolutionManager) {
    console.log('🧹 Cleaning up Evolution API manager...')
    await evolutionManager.cleanup()
  }
}

/**
 * Start Evolution API on app startup
 */
export const startEvolutionOnStartup = async () => {
  try {
    const manager = initEvolutionManager()
    console.log('Starting Evolution API on app startup...')
    await manager.start()
    console.log('Evolution API started successfully on startup')
  } catch (error) {
    console.error('Failed to start Evolution API on startup:', error)
    throw error
  }
}
