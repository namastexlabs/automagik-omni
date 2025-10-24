/**
 * Shared configuration loader for Electron desktop app
 * Ensures backend and UI use the same API key and configuration
 */

import { app } from 'electron'
import { join } from 'path'
import { existsSync, readFileSync } from 'fs'

export interface AppConfig {
  apiHost: string
  apiPort: number
  apiKey: string
  apiUrl: string
}

let cachedConfig: AppConfig | null = null

/**
 * Generate a secure default API key for desktop installations
 */
function generateDefaultApiKey(): string {
  // Generate a random API key for desktop installations
  // This is secure because the backend only runs on localhost
  const timestamp = Date.now().toString(36)
  const random = Math.random().toString(36).substring(2, 15)
  return `desktop-${timestamp}-${random}`
}

/**
 * Load configuration from .env file (cached)
 * This ensures both backend and UI use the SAME configuration
 */
export function loadAppConfig(): AppConfig {
  // Return cached config if available
  if (cachedConfig) {
    return cachedConfig
  }

  const projectRoot = app.isPackaged
    ? join(process.resourcesPath, 'backend')
    : join(__dirname, '../../..')

  const envPath = join(projectRoot, '.env')
  let apiHost = 'localhost'
  let apiPort = 8882 // Automagik Omni default port
  let apiKey = ''

  console.log('📁 Loading configuration from:', envPath)

  if (existsSync(envPath)) {
    const envContent = readFileSync(envPath, 'utf-8')
    envContent.split('\n').forEach((line) => {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=')
        if (key && valueParts.length > 0) {
          const value = valueParts.join('=').trim().replace(/^["']|["']$/g, '')
          if (key.trim() === 'AUTOMAGIK_OMNI_API_HOST') apiHost = value
          if (key.trim() === 'AUTOMAGIK_OMNI_API_PORT') apiPort = parseInt(value, 10)
          if (key.trim() === 'AUTOMAGIK_OMNI_API_KEY') apiKey = value
        }
      }
    })
  } else {
    console.warn('⚠️  .env file not found at:', envPath)
  }

  // Handle 0.0.0.0 -> localhost for client requests
  if (apiHost === '0.0.0.0') apiHost = 'localhost'

  // Desktop installations: Generate a default API key if none is configured
  // This is secure because the backend only runs on localhost
  if (!apiKey) {
    apiKey = generateDefaultApiKey()
    console.log('🔑 Generated default API key for desktop installation')
  }

  // Cache the config
  cachedConfig = {
    apiHost,
    apiPort,
    apiKey,
    apiUrl: `http://${apiHost}:${apiPort}`,
  }

  console.log('📋 API Configuration loaded:')
  console.log('  - API URL:', cachedConfig.apiUrl)
  console.log('  - API Key:', apiKey ? `${apiKey.substring(0, 8)}***` : '(empty)')

  return cachedConfig
}

/**
 * Reset cached config (useful for testing)
 */
export function resetConfigCache(): void {
  cachedConfig = null
}
