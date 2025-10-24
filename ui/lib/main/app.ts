import { BrowserWindow, shell, app, Menu } from 'electron'
import { join } from 'path'
import { existsSync, readFileSync } from 'fs'
import appIcon from '@/resources/build/icon.png?asset'
import { registerResourcesProtocol } from './protocols'
import { registerWindowHandlers } from '@/lib/conveyor/handlers/window-handler'
import { registerAppHandlers } from '@/lib/conveyor/handlers/app-handler'
import { registerBackendHandlers } from '@/lib/conveyor/handlers/backend-handler'
import { registerOmniHandlers, initOmniClient } from '@/lib/conveyor/handlers/omni-handler'

/**
 * Load configuration from .env file
 */
function loadEnvConfig(): { apiUrl: string; apiKey: string } {
  const projectRoot = app.isPackaged
    ? join(process.resourcesPath, 'backend')
    : join(__dirname, '../../..')

  const envPath = join(projectRoot, '.env')
  let apiHost = 'localhost'
  let apiPort = '8882' // Automagik Omni default port
  let apiKey = ''

  if (existsSync(envPath)) {
    const envContent = readFileSync(envPath, 'utf-8')
    envContent.split('\n').forEach((line) => {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=')
        if (key && valueParts.length > 0) {
          const value = valueParts.join('=').trim().replace(/^["']|["']$/g, '')
          if (key.trim() === 'AUTOMAGIK_OMNI_API_HOST') apiHost = value
          if (key.trim() === 'AUTOMAGIK_OMNI_API_PORT') apiPort = value
          if (key.trim() === 'AUTOMAGIK_OMNI_API_KEY') apiKey = value
        }
      }
    })
  }

  // Handle 0.0.0.0 -> localhost for client requests
  if (apiHost === '0.0.0.0') apiHost = 'localhost'

  return {
    apiUrl: `http://${apiHost}:${apiPort}`,
    apiKey,
  }
}

export function createAppWindow(): void {
  // Register custom protocol for resources
  registerResourcesProtocol()

  // Remove default menu bar
  Menu.setApplicationMenu(null)

  // Load config and initialize Omni client
  const { apiUrl, apiKey } = loadEnvConfig()
  initOmniClient(apiUrl, apiKey)

  // Create the main window.
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    show: true, // Show immediately
    backgroundColor: '#000000',
    icon: appIcon,
    frame: false, // Frameless for custom titlebar
    title: 'Automagik Omni',
    maximizable: true,
    resizable: true,
    center: true,
    alwaysOnTop: false, // Don't force on top
    webPreferences: {
      preload: join(__dirname, '../preload/preload.js'),
      sandbox: false,
    },
  })

  // Register IPC events for the main window.
  registerWindowHandlers(mainWindow)
  registerAppHandlers(app)
  registerBackendHandlers()
  registerOmniHandlers()

  // Handle window controls
  const { ipcMain } = require('electron')
  ipcMain.on('window-minimize', () => mainWindow.minimize())
  ipcMain.on('window-maximize', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow.maximize()
    }
  })
  ipcMain.on('window-close', () => mainWindow.close())

  // DevTools can be opened with F12 if needed (disabled by default)
  // if (!app.isPackaged) {
  //   mainWindow.webContents.openDevTools()
  // }

  // Disable always on top after 3 seconds
  setTimeout(() => {
    mainWindow.setAlwaysOnTop(false)
  }, 3000)

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // HMR for renderer base on electron-vite cli.
  // Load the remote URL for development or the local html file for production.
  if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}
