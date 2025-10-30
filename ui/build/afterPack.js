/**
 * electron-builder afterPack hook
 * Manually sets Windows executable version info and icon using rcedit
 *
 * This ensures Task Manager displays "Omni" with custom icon instead of "Electron"
 */

const path = require('path')
const { execFile } = require('child_process')
const { promisify } = require('util')
const fs = require('fs')

const execFileAsync = promisify(execFile)

exports.default = async function (context) {
  const appOutDir = context.appOutDir

  // Copy Evolution API node_modules (cross-platform)
  console.log(`\n📦 Copying Evolution API node_modules...`)
  const evolutionSrc = path.join(__dirname, '..', '..', 'dist-evolution', 'node_modules')
  const evolutionDest = path.join(appOutDir, 'resources', 'evolution', 'node_modules')

  if (fs.existsSync(evolutionSrc)) {
    console.log(`   Source: ${evolutionSrc}`)
    console.log(`   Destination: ${evolutionDest}`)
    console.log(`   This may take a moment...`)

    try {
      fs.cpSync(evolutionSrc, evolutionDest, { recursive: true })
      console.log(`   ✅ Evolution API node_modules copied successfully`)
    } catch (error) {
      console.error(`   ❌ Failed to copy Evolution API node_modules:`, error)
      throw error
    }
  } else {
    console.warn(`   ⚠️  Evolution API node_modules not found at ${evolutionSrc}`)
  }

  // Only run Windows-specific tasks on Windows platform
  if (context.electronPlatformName !== 'win32') {
    return
  }

  const executableName = context.packager.appInfo.productFilename + '.exe'
  const executablePath = path.join(appOutDir, executableName)

  // Find rcedit.exe in node_modules
  const rceditPath = path.join(
    __dirname,
    '..',
    'node_modules',
    'rcedit',
    'bin',
    'rcedit.exe'
  )

  // Path to custom icon
  const iconPath = path.join(__dirname, '..', 'resources', 'build', 'icon.ico')

  if (!fs.existsSync(rceditPath)) {
    console.error(`❌ rcedit not found at ${rceditPath}`)
    throw new Error(`rcedit not found`)
  }

  if (!fs.existsSync(iconPath)) {
    console.error(`❌ icon.ico not found at ${iconPath}`)
    throw new Error(`icon.ico not found`)
  }

  console.log(`\n🔧 Running afterPack hook to set Windows version info and icon...`)
  console.log(`   Executable: ${executablePath}`)
  console.log(`   rcedit: ${rceditPath}`)
  console.log(`   Icon: ${iconPath}`)
  console.log(`   Product Name: Omni`)

  try {
    // Set version info strings AND icon in a single rcedit call
    // This avoids double-processing and potential conflicts
    await execFileAsync(rceditPath, [
      executablePath,
      '--set-version-string', 'FileDescription', 'Omni',
      '--set-version-string', 'ProductName', 'Omni',
      '--set-version-string', 'CompanyName', 'Namastex Labs',
      '--set-version-string', 'LegalCopyright', 'Copyright © 2025 Namastex Labs',
      '--set-version-string', 'OriginalFilename', executableName,
      '--set-icon', iconPath
    ])

    console.log(`✅ Successfully updated Windows version info and icon for ${executableName}`)
  } catch (error) {
    console.error(`❌ Failed to set version info/icon:`, error)
    throw error
  }
}
