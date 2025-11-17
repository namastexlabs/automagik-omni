#!/usr/bin/env node
/**
 * Optimize Evolution API node_modules for production distribution
 * Removes unnecessary files and dev dependencies to reduce installer size
 */

const fs = require('fs')
const path = require('path')

const EVOLUTION_MODULES = path.join(__dirname, '../../dist-evolution/node_modules')

console.log('🧹 Optimizing Evolution API dependencies for production...')

let totalSaved = 0

function removeDir(dirPath, description) {
  if (fs.existsSync(dirPath)) {
    const stats = fs.statSync(dirPath)
    const sizeMB = (getDirectorySize(dirPath) / (1024 * 1024)).toFixed(2)
    fs.rmSync(dirPath, { recursive: true, force: true })
    totalSaved += parseFloat(sizeMB)
    console.log(`   ✅ Removed ${description}: ${sizeMB} MB`)
  }
}

function getDirectorySize(dirPath) {
  let size = 0
  try {
    const files = fs.readdirSync(dirPath)
    for (const file of files) {
      const filePath = path.join(dirPath, file)
      const stats = fs.statSync(filePath)
      if (stats.isDirectory()) {
        size += getDirectorySize(filePath)
      } else {
        size += stats.size
      }
    }
  } catch (err) {
    // Ignore errors
  }
  return size
}

// Remove Prisma CLI build directory (not needed at runtime, only query engine is needed)
removeDir(path.join(EVOLUTION_MODULES, 'prisma/build'), 'Prisma CLI build')

// Remove TypeScript (dev dependency that shouldn't be in production)
removeDir(path.join(EVOLUTION_MODULES, 'typescript'), 'TypeScript')

// Remove all @types packages (TypeScript definitions not needed at runtime)
const typesDir = path.join(EVOLUTION_MODULES, '@types')
if (fs.existsSync(typesDir)) {
  const typePackages = fs.readdirSync(typesDir)
  for (const pkg of typePackages) {
    removeDir(path.join(typesDir, pkg), `@types/${pkg}`)
  }
}

// Remove ESBuild (dev/build tool not needed at runtime)
removeDir(path.join(EVOLUTION_MODULES, '@esbuild'), '@esbuild')
removeDir(path.join(EVOLUTION_MODULES, 'esbuild'), 'esbuild')

// Remove test/example files from large packages
const cleanupPatterns = [
  // Remove test directories
  { pattern: 'test', description: 'test directories' },
  { pattern: 'tests', description: 'tests directories' },
  { pattern: '__tests__', description: '__tests__ directories' },
  // Remove example directories
  { pattern: 'example', description: 'example directories' },
  { pattern: 'examples', description: 'examples directories' },
  // Remove documentation
  { pattern: 'docs', description: 'docs directories' },
  { pattern: '.github', description: '.github directories' },
]

let cleanupSaved = 0
for (const { pattern, description } of cleanupPatterns) {
  const matches = findMatchingDirs(EVOLUTION_MODULES, pattern)
  for (const match of matches) {
    const sizeMB = (getDirectorySize(match) / (1024 * 1024)).toFixed(2)
    if (parseFloat(sizeMB) > 0.1) {
      // Only remove if > 100KB
      fs.rmSync(match, { recursive: true, force: true })
      cleanupSaved += parseFloat(sizeMB)
    }
  }
}
if (cleanupSaved > 0) {
  totalSaved += cleanupSaved
  console.log(`   ✅ Removed ${cleanupPatterns.map(p => p.description).join(', ')}: ${cleanupSaved.toFixed(2)} MB`)
}

function findMatchingDirs(baseDir, pattern) {
  const results = []
  try {
    const entries = fs.readdirSync(baseDir, { withFileTypes: true })
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const fullPath = path.join(baseDir, entry.name)
        if (entry.name === pattern) {
          results.push(fullPath)
        } else if (!entry.name.startsWith('.')) {
          // Recursively search subdirectories (but skip hidden dirs)
          results.push(...findMatchingDirs(fullPath, pattern))
        }
      }
    }
  } catch (err) {
    // Ignore errors
  }
  return results
}

console.log(`\n✅ Optimization complete! Saved ${totalSaved.toFixed(2)} MB`)
console.log(`   New node_modules size: ${(getDirectorySize(EVOLUTION_MODULES) / (1024 * 1024)).toFixed(2)} MB`)
