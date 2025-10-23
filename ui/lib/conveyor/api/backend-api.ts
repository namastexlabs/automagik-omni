import { ConveyorApi } from '@/lib/preload/shared'
import type {
  BackendStatus,
  HealthCheck,
  BackendConfig,
  BackendLogResult,
} from '@/lib/conveyor/schemas/backend-schema'

/**
 * Backend API
 * Type-safe client for backend service management
 */
export class BackendApi extends ConveyorApi {
  /**
   * Get overall backend status
   */
  status = (): Promise<BackendStatus> => {
    return this.invoke('backend:status')
  }

  /**
   * Start backend services
   */
  start = (): Promise<{ success: boolean; message: string }> => {
    return this.invoke('backend:manager:start')
  }

  /**
   * Stop backend services
   */
  stop = (): Promise<{ success: boolean; message: string }> => {
    return this.invoke('backend:manager:stop')
  }

  /**
   * Restart backend services
   */
  restart = (): Promise<{ success: boolean; message: string }> => {
    return this.invoke('backend:manager:restart')
  }

  /**
   * Perform health check
   */
  health = (): Promise<HealthCheck> => {
    return this.invoke('backend:health')
  }

  /**
   * Get backend configuration
   */
  getConfig = (): Promise<BackendConfig> => {
    return this.invoke('backend:config:get')
  }

  /**
   * Update backend configuration
   */
  setConfig = (config: Partial<BackendConfig>): Promise<{ success: boolean; message: string }> => {
    return this.invoke('backend:config:set', config)
  }

  /**
   * Get logs from backend services
   */
  getLogs = (
    service: 'api' | 'discord' | 'pm2' | 'all' = 'all',
    lines = 100,
    tail = false
  ): Promise<BackendLogResult> => {
    return this.invoke('backend:logs', { service, lines, tail })
  }
}
