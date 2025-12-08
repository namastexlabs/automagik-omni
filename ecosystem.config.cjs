// ===================================================================
// 🌐 Automagik-Omni - PM2 Configuration (Gateway Mode)
// ===================================================================
const path = require('path');
const fs = require('fs');

const PROJECT_ROOT = __dirname;

// Load environment variables
const envPath = path.join(PROJECT_ROOT, '.env');
let envVars = {};
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  envContent.split('\n').forEach(line => {
    const [key, value] = line.split('=');
    if (key && value) {
      envVars[key.trim()] = value.trim().replace(/^["']|["']$/g, '');
    }
  });
}

// Create logs directory
const logsDir = path.join(PROJECT_ROOT, 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// Find bun: prefer system bun (in PATH), then node_modules
// Bun runs TypeScript natively - no build step needed
const { execSync } = require('child_process');
let bunPath = 'bun';  // Default: assume bun is in PATH

// Check if system bun exists
try {
  execSync('which bun', { stdio: 'ignore' });
  bunPath = 'bun';  // System bun found
} catch {
  // Fall back to node_modules if system bun not found
  const bunLocations = [
    path.join(PROJECT_ROOT, 'gateway', 'node_modules', '.bin', 'bun'),
    path.join(PROJECT_ROOT, 'node_modules', '.bin', 'bun'),
  ];
  const found = bunLocations.find(p => fs.existsSync(p));
  if (found) bunPath = found;
}

// Determine port for naming
const OMNI_PORT = envVars.OMNI_PORT || envVars.AUTOMAGIK_OMNI_API_PORT || '8882';

module.exports = {
  apps: [
    {
      name: `${OMNI_PORT}-automagik-omni`,
      cwd: PROJECT_ROOT,
      script: bunPath,
      args: 'gateway/src/index.ts',  // Run TS directly - no build needed
      interpreter: 'none',
      env: {
        ...envVars,
        NODE_ENV: 'production',
        OMNI_PORT: OMNI_PORT,
        PYTHONPATH: PROJECT_ROOT,
        PROCESS_TITLE: `${OMNI_PORT}-automagik-omni`
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 2000,
      kill_timeout: 10000,
      error_file: path.join(PROJECT_ROOT, 'logs/gateway-err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/gateway-out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/gateway-combined.log'),
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
