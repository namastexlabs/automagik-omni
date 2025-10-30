#!/usr/bin/env node
/**
 * Download Node.js binaries for embedding in Electron app
 * Downloads official Node.js binaries for Windows, macOS, and Linux
 */

const fs = require('fs')
const path = require('path')
const https = require('https')
const { execSync } = require('child_process')

const NODE_VERSION = '20.18.0'
const RESOURCES_DIR = path.join(__dirname, '../resources')
const NODEJS_DIR = path.join(RESOURCES_DIR, 'nodejs')

// Platform-specific Node.js downloads
const PLATFORMS = {
  win32: {
    url: `https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-win-x64.zip`,
    archiveName: `node-v${NODE_VERSION}-win-x64.zip`,
    extractedDir: `node-v${NODE_VERSION}-win-x64`,
    targetDir: 'nodejs-win'
  },
  darwin: {
    url: `https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-darwin-x64.tar.gz`,
    archiveName: `node-v${NODE_VERSION}-darwin-x64.tar.gz`,
    extractedDir: `node-v${NODE_VERSION}-darwin-x64`,
    targetDir: 'nodejs-mac'
  },
  linux: {
    url: `https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.gz`,
    archiveName: `node-v${NODE_VERSION}-linux-x64.tar.gz`,
    extractedDir: `node-v${NODE_VERSION}-linux-x64`,
    targetDir: 'nodejs-linux'
  }
}

/**
 * Download file from URL
 */
function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    console.log(`📥 Downloading: ${url}`)
    const file = fs.createWriteStream(dest)

    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        // Follow redirect
        return downloadFile(response.headers.location, dest).then(resolve).catch(reject)
      }

      if (response.statusCode !== 200) {
        reject(new Error(`Failed to download: ${response.statusCode}`))
        return
      }

      const totalBytes = parseInt(response.headers['content-length'], 10)
      let downloadedBytes = 0

      response.on('data', (chunk) => {
        downloadedBytes += chunk.length
        const percent = ((downloadedBytes / totalBytes) * 100).toFixed(1)
        process.stdout.write(`\r   Progress: ${percent}%`)
      })

      response.pipe(file)

      file.on('finish', () => {
        file.close()
        console.log('\n   ✅ Download complete')
        resolve()
      })
    }).on('error', (err) => {
      fs.unlink(dest, () => {}) // Delete incomplete file
      reject(err)
    })
  })
}

/**
 * Extract archive (zip or tar.gz)
 */
function extractArchive(archivePath, platform) {
  console.log(`📦 Extracting: ${path.basename(archivePath)}`)

  const tempDir = path.join(NODEJS_DIR, 'temp')
  fs.mkdirSync(tempDir, { recursive: true })

  try {
    if (archivePath.endsWith('.zip')) {
      // Windows: use PowerShell to extract
      execSync(`powershell -command "Expand-Archive -Path '${archivePath}' -DestinationPath '${tempDir}' -Force"`, {
        stdio: 'inherit'
      })
    } else if (archivePath.endsWith('.tar.gz')) {
      // Unix: use tar
      execSync(`tar -xzf "${archivePath}" -C "${tempDir}"`, {
        stdio: 'inherit'
      })
    }

    console.log('   ✅ Extraction complete')
    return tempDir
  } catch (error) {
    console.error('   ❌ Extraction failed:', error.message)
    throw error
  }
}

/**
 * Download and prepare Node.js for a specific platform
 */
async function downloadPlatform(platformKey) {
  const config = PLATFORMS[platformKey]
  const targetPath = path.join(NODEJS_DIR, config.targetDir)

  // Check if already exists
  if (fs.existsSync(targetPath)) {
    console.log(`✅ ${config.targetDir} already exists, skipping download`)
    return
  }

  console.log(`\n🔧 Preparing Node.js for ${platformKey}...`)

  // Create temp directory
  fs.mkdirSync(NODEJS_DIR, { recursive: true })

  const archivePath = path.join(NODEJS_DIR, config.archiveName)

  try {
    // Download
    await downloadFile(config.url, archivePath)

    // Extract
    const tempDir = extractArchive(archivePath, platformKey)

    // Move to target directory
    const extractedPath = path.join(tempDir, config.extractedDir)

    if (!fs.existsSync(extractedPath)) {
      throw new Error(`Extracted directory not found: ${extractedPath}`)
    }

    console.log(`📁 Moving to ${config.targetDir}`)
    fs.renameSync(extractedPath, targetPath)

    // Cleanup
    fs.rmSync(archivePath, { force: true })
    fs.rmSync(tempDir, { recursive: true, force: true })

    console.log(`✅ ${platformKey} Node.js ready at ${config.targetDir}`)
  } catch (error) {
    console.error(`❌ Failed to prepare ${platformKey}:`, error.message)
    // Cleanup on error
    fs.rmSync(archivePath, { force: true })
    throw error
  }
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Node.js Binary Downloader for Electron')
  console.log(`   Version: ${NODE_VERSION}`)
  console.log(`   Target: ${NODEJS_DIR}`)
  console.log('')

  try {
    // On Windows, we can only extract ZIP files reliably
    // For cross-platform builds, download all on the respective platform
    const currentPlatform = process.platform

    if (currentPlatform === 'win32') {
      console.log('ℹ️  Windows detected - downloading Windows binaries only')
      console.log('   (macOS/Linux binaries should be downloaded on those platforms)')
      await downloadPlatform('win32')
    } else if (currentPlatform === 'darwin') {
      console.log('ℹ️  macOS detected - downloading macOS binaries only')
      await downloadPlatform('darwin')
    } else {
      console.log('ℹ️  Linux detected - downloading Linux binaries only')
      await downloadPlatform('linux')
    }

    console.log('\n✅ Node.js binaries ready!')
    console.log(`   Location: ${NODEJS_DIR}`)
  } catch (error) {
    console.error('\n❌ Download failed:', error.message)
    process.exit(1)
  }
}

// Run if called directly
if (require.main === module) {
  main()
}

module.exports = { downloadPlatform, PLATFORMS, NODE_VERSION }
