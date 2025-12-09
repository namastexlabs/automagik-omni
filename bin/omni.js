#!/usr/bin/env node
/**
 * Automagik Omni CLI Entry Point
 * Extracts bundled Python backend on first run, then starts the gateway
 */

const { spawn } = require('child_process');
const { join } = require('path');
const { existsSync, mkdirSync, cpSync } = require('fs');
const { homedir } = require('os');

const BUNDLED_ROOT = join(homedir(), 'automagik', 'omni');
const BUNDLED_SRC = join(__dirname, '../.bundled');

/**
 * Extract bundled Python backend to user home directory (first run only)
 */
async function extractBundledBackend() {
  if (existsSync(BUNDLED_ROOT)) {
    // Already extracted
    return;
  }

  console.log('🚀 First run: Extracting Python backend...');
  console.log(`   Target: ${BUNDLED_ROOT}`);

  if (!existsSync(BUNDLED_SRC)) {
    console.error('❌ Error: Bundled Python backend not found.');
    console.error('   This package may be corrupted or incomplete.');
    console.error('   Try reinstalling: bun add -g @automagik/omni');
    process.exit(1);
  }

  try {
    // Create root directory
    mkdirSync(BUNDLED_ROOT, { recursive: true });

    // Copy Python venv
    console.log('   Copying Python runtime...');
    cpSync(
      join(BUNDLED_SRC, 'python'),
      join(BUNDLED_ROOT, 'python'),
      { recursive: true }
    );

    // Copy Python backend source
    console.log('   Copying backend source...');
    cpSync(
      join(BUNDLED_SRC, 'backend'),
      join(BUNDLED_ROOT, 'backend'),
      { recursive: true }
    );

    console.log('✅ Backend extracted successfully!\n');
  } catch (err) {
    console.error('❌ Failed to extract backend:', err.message);
    process.exit(1);
  }
}

/**
 * Start the Omni gateway
 */
function startGateway() {
  const gatewayPath = join(__dirname, '../gateway/dist/index.js');

  if (!existsSync(gatewayPath)) {
    console.error('❌ Error: Gateway not found at', gatewayPath);
    console.error('   This package may be corrupted.');
    process.exit(1);
  }

  // Forward all CLI args to gateway
  const args = process.argv.slice(2);

  const child = spawn('node', [gatewayPath, ...args], {
    stdio: 'inherit',
    env: process.env,
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });

  child.on('error', (err) => {
    console.error('❌ Failed to start gateway:', err.message);
    process.exit(1);
  });
}

/**
 * Main entry point
 */
async function main() {
  // Extract backend on first run
  await extractBundledBackend();

  // Start gateway
  startGateway();
}

// Run
main().catch((err) => {
  console.error('❌ Fatal error:', err);
  process.exit(1);
});
