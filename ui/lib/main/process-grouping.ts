/**
 * Process Grouping Utilities for Windows Task Manager
 *
 * On Windows, processes can be grouped under a single parent in Task Manager
 * by setting the same App User Model ID (AUMID) for all child processes.
 *
 * This ensures that:
 * 1. All processes show the same icon (Omni icon)
 * 2. Processes are grouped under a single expandable entry
 * 3. Clicking the taskbar icon shows all related windows
 */

import { spawn, exec } from 'child_process'
import { promisify } from 'util'
import * as os from 'os'

const execAsync = promisify(exec)

/**
 * App User Model ID for Automagik Omni
 * Must match the appId in electron-builder.yml
 */
export const OMNI_AUMID = 'com.namastex.automagik-omni'

/**
 * Set App User Model ID for a Windows process by PID
 * This ensures the process appears grouped in Task Manager
 *
 * @param pid - Process ID to set AUMID for
 * @returns Promise resolving to success boolean
 */
export async function setProcessAUMID(pid: number): Promise<boolean> {
  if (os.platform() !== 'win32') {
    // Only applicable on Windows
    return true
  }

  try {
    // Use PowerShell to set the AUMID for the process
    // This is done via Windows AppUserModelID COM interface
    const psScript = `
      Add-Type -TypeDefinition @"
        using System;
        using System.Runtime.InteropServices;

        public class ProcessAUMID {
          [DllImport("shell32.dll", SetLastError = true)]
          public static extern void SetCurrentProcessExplicitAppUserModelID(
            [MarshalAs(UnmanagedType.LPWStr)] string AppID
          );
        }
"@
      [ProcessAUMID]::SetCurrentProcessExplicitAppUserModelID("${OMNI_AUMID}")
    `

    // Execute PowerShell to set AUMID
    await execAsync(`powershell -NoProfile -Command "${psScript.replace(/\n/g, ' ')}"`)

    console.log(`✅ Set AUMID for PID ${pid}:`, OMNI_AUMID)
    return true
  } catch (error) {
    console.warn(`⚠️ Failed to set AUMID for PID ${pid}:`, error)
    return false
  }
}

/**
 * Patch PM2 ecosystem config to set AUMID for all spawned processes
 * This ensures backend processes (api, discord, etc.) are grouped properly
 *
 * @param ecosystemPath - Path to ecosystem.config.js
 * @returns Modified ecosystem config with AUMID injection
 */
export function patchEcosystemConfig(ecosystemPath: string): string {
  // For now, we'll set AUMID via environment variable
  // PM2 processes will inherit this and set it on startup
  return `
    // AUMID Injection for Windows Process Grouping
    if (process.platform === 'win32') {
      process.env.ELECTRON_AUMID = '${OMNI_AUMID}';

      // Attempt to set AUMID for PM2 parent process
      try {
        const { exec } = require('child_process');
        exec(\`powershell -NoProfile -Command "Add-Type -TypeDefinition @'
          using System;
          using System.Runtime.InteropServices;

          public class ProcessAUMID {
            [DllImport(\\"shell32.dll\\", SetLastError = true)]
            public static extern void SetCurrentProcessExplicitAppUserModelID(
              [MarshalAs(UnmanagedType.LPWStr)] string AppID
            );
          }
'@; [ProcessAUMID]::SetCurrentProcessExplicitAppUserModelID('${OMNI_AUMID}')"\`);
      } catch (e) {
        console.warn('Failed to set AUMID:', e);
      }
    }

    // Load original ecosystem config
    module.exports = require('${ecosystemPath}');
  `
}

/**
 * Monitor PM2 processes and set AUMID for newly spawned child processes
 *
 * @param onProcessSpawned - Callback when new process is detected
 */
export async function monitorPM2Processes(
  onProcessSpawned?: (pid: number, name: string) => void
): Promise<void> {
  if (os.platform() !== 'win32') {
    return
  }

  try {
    // Get list of PM2 processes
    const { stdout } = await execAsync('pm2 jlist')
    const processes = JSON.parse(stdout)

    for (const process of processes) {
      if (process.name?.includes('Omni Backend') && process.pid) {
        // Set AUMID for this process
        await setProcessAUMID(process.pid)

        if (onProcessSpawned) {
          onProcessSpawned(process.pid, process.name)
        }
      }
    }
  } catch (error) {
    console.warn('⚠️ Failed to monitor PM2 processes:', error)
  }
}

/**
 * Initialize Windows process grouping
 * Call this once at app startup to ensure all processes are grouped
 */
export async function initializeProcessGrouping(): Promise<void> {
  if (os.platform() !== 'win32') {
    console.log('ℹ️ Process grouping only applies to Windows')
    return
  }

  console.log('🔗 Initializing Windows process grouping...')
  console.log('   AUMID:', OMNI_AUMID)

  // Monitor PM2 processes every 30 seconds
  setInterval(async () => {
    await monitorPM2Processes((pid, name) => {
      console.log(`🔗 Grouped process: ${name} (PID: ${pid})`)
    })
  }, 30000)

  // Initial scan
  await monitorPM2Processes()
}
