#!/usr/bin/env node
/**
 * Build Evolution API for embedding in Electron app
 *
 * Steps:
 * 1. Install Evolution API dependencies
 * 2. Generate Prisma client for SQLite
 * 3. Build TypeScript to dist/
 * 4. Prepare production-ready package
 */

const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')

const EVOLUTION_DIR = path.resolve(__dirname, '../../resources/evolution-api')
const DIST_DIR = path.resolve(__dirname, '../../dist-evolution')

/**
 * Execute command with logging
 */
function exec(command, options = {}) {
  console.log(`   $ ${command}`)
  try {
    execSync(command, {
      cwd: EVOLUTION_DIR,
      stdio: 'inherit',
      ...options
    })
  } catch (error) {
    console.error(`   ❌ Command failed: ${command}`)
    throw error
  }
}

/**
 * Check if Evolution API directory exists
 */
function checkEvolutionExists() {
  if (!fs.existsSync(EVOLUTION_DIR)) {
    console.error(`❌ Evolution API not found at: ${EVOLUTION_DIR}`)
    console.error('   Run: git submodule update --init --recursive')
    process.exit(1)
  }

  if (!fs.existsSync(path.join(EVOLUTION_DIR, 'package.json'))) {
    console.error(`❌ Invalid Evolution API directory (no package.json)`)
    process.exit(1)
  }

  console.log(`✅ Evolution API found at: ${EVOLUTION_DIR}`)
}

/**
 * Install Evolution API dependencies
 */
function installDependencies() {
  console.log('\n📦 Installing Evolution API dependencies (production only)...')

  const nodeModules = path.join(EVOLUTION_DIR, 'node_modules')

  if (fs.existsSync(nodeModules)) {
    console.log('   node_modules exists, checking if up to date...')
  }

  // Install production dependencies only (ignore scripts to skip husky/dev tools)
  exec('npm install --omit=dev --ignore-scripts')

  console.log('   ✅ Dependencies installed')
}

/**
 * Generate Prisma client for SQLite
 */
function generatePrismaClient() {
  console.log('\n🔧 Generating Prisma client for SQLite...')

  // Set DATABASE_PROVIDER to sqlite
  const env = {
    ...process.env,
    DATABASE_PROVIDER: 'sqlite'
  }

  try {
    execSync('npm run db:generate', {
      cwd: EVOLUTION_DIR,
      stdio: 'inherit',
      env
    })

    console.log('   ✅ Prisma client generated')
  } catch (error) {
    console.error('   ❌ Prisma generation failed')
    throw error
  }
}

/**
 * Build TypeScript to dist/
 */
function buildTypeScript() {
  console.log('\n🔨 Building TypeScript...')
  console.log('   (skipping type check due to Evolution API type errors)')

  // Skip type check, just run tsup
  exec('npx tsup')

  const distPath = path.join(EVOLUTION_DIR, 'dist')
  if (!fs.existsSync(distPath)) {
    throw new Error('Build failed: dist/ directory not created')
  }

  console.log('   ✅ TypeScript built to dist/')
}

/**
 * Clean unnecessary files from node_modules to reduce size
 */
function cleanNodeModules() {
  console.log('\n🧹 Cleaning unnecessary files from node_modules...')

  const nodeModulesPath = path.join(DIST_DIR, 'node_modules')
  let removedSize = 0

  // Patterns to remove
  const patternsToRemove = [
    '**/*.md',
    '**/*.markdown',
    '**/README*',
    '**/CHANGELOG*',
    '**/HISTORY*',
    '**/LICENSE*',
    '**/LICENCE*',
    '**/.npmignore',
    '**/.gitignore',
    '**/.eslintrc*',
    '**/.prettierrc*',
    '**/test/**',
    '**/tests/**',
    '**/__tests__/**',
    '**/docs/**',
    '**/doc/**',
    '**/examples/**',
    '**/example/**',
    '**/.github/**',
    '**/*.ts.map',
    '**/*.d.ts.map'
  ]

  function removeMatchingFiles(dir, patterns) {
    if (!fs.existsSync(dir)) return

    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true })

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name)

        if (entry.isDirectory()) {
          // Check if entire directory should be removed
          const shouldRemoveDir = patterns.some(pattern => {
            const patternParts = pattern.split('/')
            const dirPattern = patternParts[patternParts.length - 1]
            return entry.name === dirPattern || entry.name === dirPattern.replace('**', '')
          })

          if (shouldRemoveDir) {
            try {
              const stats = fs.statSync(fullPath)
              removedSize += getDirSize(fullPath)
              fs.rmSync(fullPath, { recursive: true, force: true })
            } catch (e) {}
          } else {
            removeMatchingFiles(fullPath, patterns)
          }
        } else {
          // Check if file should be removed
          const shouldRemove = patterns.some(pattern => {
            const fileName = entry.name
            const patternFile = pattern.split('/').pop()

            if (patternFile.includes('*')) {
              const regex = new RegExp(patternFile.replace(/\*/g, '.*'))
              return regex.test(fileName)
            }
            return fileName === patternFile
          })

          if (shouldRemove) {
            try {
              const stats = fs.statSync(fullPath)
              removedSize += stats.size
              fs.rmSync(fullPath, { force: true })
            } catch (e) {}
          }
        }
      }
    } catch (e) {
      // Skip directories that can't be read
    }
  }

  function getDirSize(dirPath) {
    let size = 0
    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true })
      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name)
        if (entry.isDirectory()) {
          size += getDirSize(fullPath)
        } else {
          size += fs.statSync(fullPath).size
        }
      }
    } catch (e) {}
    return size
  }

  removeMatchingFiles(nodeModulesPath, patternsToRemove)

  const removedMB = (removedSize / 1024 / 1024).toFixed(1)
  console.log(`   ✅ Cleaned ${removedMB} MB of unnecessary files`)
}

/**
 * Prepare production package in dist-evolution/
 */
function prepareProductionPackage() {
  console.log('\n📁 Preparing production package...')

  // Clean dist-evolution if exists
  if (fs.existsSync(DIST_DIR)) {
    console.log('   Cleaning existing dist-evolution...')
    fs.rmSync(DIST_DIR, { recursive: true, force: true })
  }

  fs.mkdirSync(DIST_DIR, { recursive: true })

  // Copy dist/
  console.log('   Copying dist/...')
  fs.cpSync(
    path.join(EVOLUTION_DIR, 'dist'),
    path.join(DIST_DIR, 'dist'),
    { recursive: true }
  )

  // Copy node_modules/ (production only)
  console.log('   Copying node_modules/ (this may take a moment)...')
  fs.cpSync(
    path.join(EVOLUTION_DIR, 'node_modules'),
    path.join(DIST_DIR, 'node_modules'),
    { recursive: true }
  )

  // Optimize node_modules by removing dev dependencies and unnecessary files
  console.log('   Optimizing node_modules...')
  const optimizeScript = path.join(__dirname, 'optimize-evolution-deps.js')
  execSync(`node "${optimizeScript}"`, { stdio: 'inherit' })

  // Copy prisma/ (schema + generated client)
  console.log('   Copying prisma/...')
  fs.cpSync(
    path.join(EVOLUTION_DIR, 'prisma'),
    path.join(DIST_DIR, 'prisma'),
    { recursive: true }
  )

  // Copy package.json
  console.log('   Copying package.json...')
  fs.copyFileSync(
    path.join(EVOLUTION_DIR, 'package.json'),
    path.join(DIST_DIR, 'package.json')
  )

  // Create default .env for desktop
  console.log('   Creating default .env.desktop...')
  createDefaultEnv()

  console.log(`   ✅ Production package ready at: ${DIST_DIR}`)
}

/**
 * Create default .env file for desktop deployment
 */
function createDefaultEnv() {
  const defaultEnv = `# Evolution API Desktop Configuration
# This file contains defaults for desktop deployment
# The Electron app will override these with runtime configuration

# Server Configuration
SERVER_NAME=evolution
SERVER_TYPE=http
SERVER_PORT=8080
SERVER_URL=http://localhost:8080

# Database - SQLite for desktop
DATABASE_PROVIDER=sqlite
DATABASE_CONNECTION_URI=file:./evolution-data/evolution.db
DATABASE_CONNECTION_CLIENT_NAME=evolution_desktop

# Data Storage
DATABASE_SAVE_DATA_INSTANCE=true
DATABASE_SAVE_DATA_NEW_MESSAGE=true
DATABASE_SAVE_MESSAGE_UPDATE=true
DATABASE_SAVE_DATA_CONTACTS=true
DATABASE_SAVE_DATA_CHATS=true
DATABASE_SAVE_DATA_LABELS=true
DATABASE_SAVE_DATA_HISTORIC=true

# Telemetry - Disabled for desktop
TELEMETRY_ENABLED=false
SENTRY_DSN=

# Prometheus metrics - Disabled for desktop
PROMETHEUS_METRICS=false

# Logging
LOG_LEVEL=ERROR,WARN,INFO
LOG_COLOR=true
LOG_BAILEYS=error

# CORS - Allow local connections
CORS_ORIGIN=http://localhost:*,http://127.0.0.1:*
CORS_METHODS=GET,POST,PUT,DELETE
CORS_CREDENTIALS=true

# Cache - Use local cache (no Redis for desktop)
CACHE_REDIS_ENABLED=false
CACHE_LOCAL_ENABLED=true

# Authentication - Will be set by Electron app
AUTHENTICATION_API_KEY=

# Delete instance on disconnect - disabled for desktop
DEL_INSTANCE=false

# Session configuration
CONFIG_SESSION_PHONE_CLIENT=Omni Desktop
CONFIG_SESSION_PHONE_NAME=Chrome

# QR Code configuration
QRCODE_LIMIT=30
QRCODE_COLOR=#175197

# Disable external integrations by default
WEBHOOK_GLOBAL_ENABLED=false
RABBITMQ_ENABLED=false
SQS_ENABLED=false
WEBSOCKET_ENABLED=false
KAFKA_ENABLED=false
PUSHER_ENABLED=false
TYPEBOT_ENABLED=false
CHATWOOT_ENABLED=false
OPENAI_ENABLED=false
DIFY_ENABLED=false
N8N_ENABLED=false
EVOAI_ENABLED=false
S3_ENABLED=false

# Language
LANGUAGE=en
`

  fs.writeFileSync(path.join(DIST_DIR, '.env.desktop'), defaultEnv)
  console.log('   ✅ Default .env.desktop created')
}

/**
 * Show package size
 */
function showPackageSize() {
  console.log('\n📊 Package size summary:')

  const getSize = (dirPath) => {
    if (!fs.existsSync(dirPath)) return 0

    let size = 0
    const files = fs.readdirSync(dirPath, { withFileTypes: true })

    for (const file of files) {
      const filePath = path.join(dirPath, file.name)
      if (file.isDirectory()) {
        size += getSize(filePath)
      } else {
        size += fs.statSync(filePath).size
      }
    }

    return size
  }

  const formatSize = (bytes) => {
    const mb = bytes / 1024 / 1024
    return `${mb.toFixed(1)} MB`
  }

  const distSize = getSize(path.join(DIST_DIR, 'dist'))
  const nodeModulesSize = getSize(path.join(DIST_DIR, 'node_modules'))
  const prismaSize = getSize(path.join(DIST_DIR, 'prisma'))
  const totalSize = distSize + nodeModulesSize + prismaSize

  console.log(`   dist/         : ${formatSize(distSize)}`)
  console.log(`   node_modules/ : ${formatSize(nodeModulesSize)}`)
  console.log(`   prisma/       : ${formatSize(prismaSize)}`)
  console.log(`   ────────────────────────`)
  console.log(`   Total         : ${formatSize(totalSize)}`)
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Evolution API Build Script for Electron\n')

  try {
    checkEvolutionExists()
    installDependencies()
    generatePrismaClient()
    buildTypeScript()
    prepareProductionPackage()
    showPackageSize()

    console.log('\n✅ Evolution API build complete!')
    console.log(`   Ready for packaging at: ${DIST_DIR}`)
  } catch (error) {
    console.error('\n❌ Build failed:', error.message)
    process.exit(1)
  }
}

// Run if called directly
if (require.main === module) {
  main()
}

module.exports = { main }
