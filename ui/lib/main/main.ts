import { app, BrowserWindow } from 'electron'
import { electronApp, optimizer } from '@electron-toolkit/utils'
import { createAppWindow } from './app'
import { cleanupBackendMonitor, startBackendOnStartup } from '@/lib/conveyor/handlers/backend-handler'

// Detect if running in WSL (development environment)
const isWSL = process.env.WSL_DISTRO_NAME || process.env.WSL_INTEROP
const isDev = !app.isPackaged

// Enable debug logging in development
if (isDev) {
  app.commandLine.appendSwitch('enable-logging')
  app.commandLine.appendSwitch('log-level', '0')
  console.log('🔧 Running in development mode')
  console.log('Platform:', process.platform)
  console.log('Is WSL:', !!isWSL)
  console.log('Is Packaged:', app.isPackaged)
}

// WSL FIX: Only disable GPU in WSL environment (not production Windows)
if (isWSL) {
  console.log('🐧 WSL detected - disabling GPU acceleration')
  app.commandLine.appendSwitch('disable-gpu')
  app.commandLine.appendSwitch('disable-gpu-compositing')
  app.commandLine.appendSwitch('disable-software-rasterizer')
  app.disableHardwareAcceleration()
}

// Enable emoji rendering on Windows
if (process.platform === 'win32') {
  app.commandLine.appendSwitch('enable-features', 'DirectWriteFontCache')
  app.commandLine.appendSwitch('font-render-hinting', 'none')
  if (isDev) {
    console.log('🪟 Windows emoji rendering enabled')
  }
}

// Global error handlers for debugging
process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught Exception:', error)
  if (isDev) {
    console.error('Stack:', error.stack)
  }
})

process.on('unhandledRejection', (reason) => {
  console.error('❌ Unhandled Rejection:', reason)
})

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(async () => {
  console.log('✅ Electron app ready')

  // Set app user model id for windows
  electronApp.setAppUserModelId('com.automagik.omni')

  try {
    // Start backend before creating window
    console.log('🚀 Starting backend...')
    await startBackendOnStartup()
    console.log('✅ Backend started successfully')
  } catch (error) {
    console.error('❌ Failed to start backend:', error)
    if (isDev) {
      console.error('Stack:', error)
    }
    // Continue anyway - user can manually start backend from UI
  }

  // Create app window
  console.log('🪟 Creating main window...')
  try {
    createAppWindow()
    console.log('✅ Main window created')
  } catch (error) {
    console.error('❌ Failed to create window:', error)
    if (isDev) {
      console.error('Stack:', error)
    }
  }

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)

    // Auto-open DevTools in development
    if (isDev) {
      window.webContents.openDevTools()
      console.log('🔧 DevTools opened (development mode)')
    }

    // Log renderer errors
    window.webContents.on('console-message', (_event, level, message) => {
      const levels = ['verbose', 'info', 'warning', 'error']
      console.log(`[Renderer ${levels[level]}]:`, message)
    })
  })

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) {
      createAppWindow()
    }
  })
}).catch((error) => {
  console.error('❌ App initialization failed:', error)
  if (isDev) {
    console.error('Stack:', error.stack)
  }
})

// CRITICAL FIX: Handle app cleanup on multiple quit scenarios
// On Windows, the app can quit through multiple paths:
// 1. User clicks X button → fires 'window-all-closed' → fires 'will-quit'
// 2. User uses Alt+F4 → fires 'before-quit' directly
// 3. System shutdown → fires 'before-quit' directly
// We must ensure backend cleanup happens in ALL scenarios

let isCleaningUp = false // Prevent duplicate cleanup calls

// Handle graceful shutdown BEFORE app quits (most reliable for Windows)
app.on('before-quit', async (event) => {
  if (isCleaningUp) {
    // Cleanup already in progress, let it finish
    return
  }

  // Prevent app from quitting until cleanup completes
  event.preventDefault()
  isCleaningUp = true

  console.log('🛑 App is quitting, cleaning up backend processes...')

  try {
    await cleanupBackendMonitor()
    console.log('✅ Backend cleanup completed successfully')
  } catch (error) {
    console.error('❌ Error during backend cleanup:', error)
  } finally {
    // Now force exit the app (app.quit() would trigger before-quit again!)
    isCleaningUp = false
    app.exit(0) // Use exit() instead of quit() to avoid infinite loop
  }
})

// Quit when all windows are closed, except on macOS
// Note: Cleanup happens in 'before-quit', not here
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// In this file, you can include the rest of your app's specific main process
// code. You can also put them in separate files and import them here.
