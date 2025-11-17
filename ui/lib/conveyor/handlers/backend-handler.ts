import { handle } from '@/lib/main/shared'
import { BackendMonitor } from '@/lib/main/backend-monitor'
import { BackendManager } from '@/lib/main/backend-manager'
import { loadAppConfig } from '@/lib/main/config-loader'

let backendMonitor: BackendMonitor | null = null
let backendManager: BackendManager | null = null

/**
 * Initialize backend monitor singleton (legacy PM2-based)
 */
export const initBackendMonitor = () => {
  if (!backendMonitor) {
    // Pass backendManager reference for fallback status
    backendMonitor = new BackendMonitor(backendManager || undefined)
  }
  return backendMonitor
}

/**
 * Initialize backend manager singleton (new subprocess-based)
 */
export const initBackendManager = () => {
  if (!backendManager) {
    const config = loadAppConfig()
    backendManager = new BackendManager({
      host: config.apiHost,
      port: config.apiPort,
      apiKey: config.apiKey,
      healthCheckUrl: `${config.apiUrl}/health`,
      startupTimeoutMs: 30000,
      healthCheckIntervalMs: 10000,
      maxRestartAttempts: 3,
    })
  }
  return backendManager
}

/**
 * Get backend monitor instance
 */
const getMonitor = (): BackendMonitor => {
  if (!backendMonitor) {
    throw new Error('Backend monitor not initialized')
  }
  return backendMonitor
}

/**
 * Get backend manager instance
 */
const getManager = (): BackendManager => {
  if (!backendManager) {
    throw new Error('Backend manager not initialized')
  }
  return backendManager
}

/**
 * Register backend IPC handlers
 */
export const registerBackendHandlers = () => {
  // Initialize manager first, then monitor (so monitor can reference manager)
  initBackendManager()
  initBackendMonitor()

  // ==================== BackendManager (subprocess) handlers ====================

  // Start backend via BackendManager
  handle('backend:manager:start', async () => {
    try {
      await getManager().start()
      return { success: true, message: 'Backend started successfully' }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  })

  // Stop backend via BackendManager
  handle('backend:manager:stop', async () => {
    try {
      await getManager().stop()
      return { success: true, message: 'Backend stopped successfully' }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  })

  // Restart backend via BackendManager
  handle('backend:manager:restart', async () => {
    try {
      await getManager().restart()
      return { success: true, message: 'Backend restarted successfully' }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  })

  // Get backend process info
  handle('backend:manager:status', async () => {
    return getManager().getStatus()
  })

  // ==================== BackendMonitor (PM2) handlers ====================

  // Status endpoint
  handle('backend:status', async () => {
    return await getMonitor().getStatus()
  })

  // Start backend
  handle('backend:start', async () => {
    return await getMonitor().start()
  })

  // Stop backend
  handle('backend:stop', async () => {
    return await getMonitor().stop()
  })

  // Restart backend
  handle('backend:restart', async () => {
    return await getMonitor().restart()
  })

  // Health check
  handle('backend:health', async () => {
    return await getMonitor().healthCheck()
  })

  // Get configuration
  handle('backend:config:get', async () => {
    return getMonitor().getConfig()
  })

  // Update configuration
  handle('backend:config:set', async (config) => {
    return getMonitor().updateConfig(config)
  })

  // Get logs
  handle('backend:logs', async (options) => {
    return await getMonitor().getLogs(options.service, options.lines, options.tail)
  })
}

/**
 * Cleanup backend monitor and manager on app quit
 */
export const cleanupBackendMonitor = async () => {
  if (backendManager) {
    await backendManager.cleanup()
  }
  if (backendMonitor) {
    await backendMonitor.cleanup()
  }
}

/**
 * Start backend on app startup (using BackendManager)
 */
export const startBackendOnStartup = async () => {
  try {
    const manager = initBackendManager()
    console.log('Starting backend on app startup...')
    await manager.start()
    console.log('Backend started successfully on startup')
  } catch (error) {
    console.error('Failed to start backend on startup:', error)
    throw error
  }
}
