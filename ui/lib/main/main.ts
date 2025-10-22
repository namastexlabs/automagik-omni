import { app, BrowserWindow } from 'electron'
import { electronApp, optimizer } from '@electron-toolkit/utils'
import { createAppWindow } from './app'
import { cleanupBackendMonitor } from '@/lib/conveyor/handlers/backend-handler'

// WSL FIX: Disable GPU to make window visible in WSL2
app.commandLine.appendSwitch('disable-gpu')
app.commandLine.appendSwitch('disable-gpu-compositing')
app.commandLine.appendSwitch('disable-software-rasterizer')
app.disableHardwareAcceleration()

// Enable emoji rendering on Windows
if (process.platform === 'win32') {
  app.commandLine.appendSwitch('enable-features', 'DirectWriteFontCache')
  app.commandLine.appendSwitch('font-render-hinting', 'none')
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  // Set app user model id for windows
  electronApp.setAppUserModelId('com.automagik.omni')
  // Create app window
  createAppWindow()

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) {
      createAppWindow()
    }
  })
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', async () => {
  // Cleanup before quitting
  await cleanupBackendMonitor()

  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// In this file, you can include the rest of your app's specific main process
// code. You can also put them in separate files and import them here.
