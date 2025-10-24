import { BrowserWindow, shell, app, Menu, ipcMain } from 'electron'
import { join } from 'path'
import appIcon from '@/resources/build/icon.png?asset'
import { registerResourcesProtocol } from './protocols'
import { registerWindowHandlers } from '@/lib/conveyor/handlers/window-handler'
import { registerAppHandlers } from '@/lib/conveyor/handlers/app-handler'
import { registerBackendHandlers } from '@/lib/conveyor/handlers/backend-handler'
import { registerOmniHandlers, initOmniClient } from '@/lib/conveyor/handlers/omni-handler'
import { loadAppConfig } from './config-loader'

export function createAppWindow(): void {
  // Register custom protocol for resources
  registerResourcesProtocol()

  // Remove default menu bar
  Menu.setApplicationMenu(null)

  // Load config and initialize Omni client (uses shared cached config)
  const config = loadAppConfig()
  initOmniClient(config.apiUrl, config.apiKey)

  // Create the main window.
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    show: true, // Show immediately
    backgroundColor: '#000000',
    icon: appIcon,
    frame: false, // Frameless for custom titlebar
    title: 'Omni UI - Main Window', // Descriptive title for Task Manager
    maximizable: true,
    resizable: true,
    center: true,
    alwaysOnTop: false, // Don't force on top
    webPreferences: {
      preload: join(__dirname, '../preload/preload.js'),
      sandbox: false,
      // Enable proper icon display in Windows
      affinity: 'main-window',
    },
  })

  // Set descriptive process name for renderer process (Windows Task Manager)
  mainWindow.webContents.on('did-finish-load', () => {
    if (process.platform === 'win32') {
      mainWindow.setTitle('Omni UI - Renderer')
    }
  })

  // Register IPC events for the main window.
  registerWindowHandlers(mainWindow)
  registerAppHandlers(app)
  registerBackendHandlers()
  registerOmniHandlers()

  // Handle window controls
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
