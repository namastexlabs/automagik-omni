import { ConveyorApi } from '@/lib/preload/shared'

/**
 * Evolution API Process Info
 */
export interface EvolutionProcessInfo {
  status: 'stopped' | 'starting' | 'running' | 'stopping' | 'error'
  pid?: number
  uptime?: number
  lastError?: string
  restartCount: number
  port: number
  apiKey: string
}

/**
 * Evolution API Client
 * Type-safe client for Evolution API (WhatsApp service) management
 */
export class EvolutionApi extends ConveyorApi {
  /**
   * Get Evolution API status
   */
  status = (): Promise<EvolutionProcessInfo> => {
    return this.invoke('evolution:status')
  }

  /**
   * Start Evolution API service
   */
  start = (): Promise<{ success: boolean; message: string }> => {
    return this.invoke('evolution:start')
  }

  /**
   * Stop Evolution API service
   */
  stop = (): Promise<{ success: boolean; message: string }> => {
    return this.invoke('evolution:stop')
  }

  /**
   * Restart Evolution API service
   */
  restart = (): Promise<{ success: boolean; message: string }> => {
    return this.invoke('evolution:restart')
  }
}
