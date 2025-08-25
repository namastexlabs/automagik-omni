// ===================================================================
// 🌐 Automagik-Omni - Dual Service PM2 Configuration with Health Checks
// ===================================================================
// This file manages both the API server and Discord bot services with proper startup ordering
// It ensures API is healthy before Discord bot attempts to start
const path = require('path');
const fs = require('fs');

// Get the current directory (automagik-omni)
const PROJECT_ROOT = __dirname;

/**
 * Extract version from pyproject.toml file using standardized approach
 * @param {string} projectPath - Path to the project directory
 * @returns {string} Version string or 'unknown'
 */
function extractVersionFromPyproject(projectPath) {
  const pyprojectPath = path.join(projectPath, 'pyproject.toml');
  
  if (!fs.existsSync(pyprojectPath)) {
    return 'unknown';
  }
  
  try {
    const content = fs.readFileSync(pyprojectPath, 'utf8');
    
    // Standard approach: Static version in [project] section
    const projectVersionMatch = content.match(/\[project\][\s\S]*?version\s*=\s*["']([^"']+)["']/);
    if (projectVersionMatch) {
      return projectVersionMatch[1];
    }
    
    // Fallback: Simple version = "..." pattern anywhere in file
    const simpleVersionMatch = content.match(/^version\s*=\s*["']([^"']+)["']/m);
    if (simpleVersionMatch) {
      return simpleVersionMatch[1];
    }
    
    return 'unknown';
  } catch (error) {
    console.warn(`Failed to read version from ${pyprojectPath}:`, error.message);
    return 'unknown';
  }
}

// Load environment variables from .env file if it exists
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

// Create logs and scripts directories if they don't exist
const logsDir = path.join(PROJECT_ROOT, 'logs');
const scriptsDir = path.join(PROJECT_ROOT, 'scripts');

if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}
if (!fs.existsSync(scriptsDir)) {
  fs.mkdirSync(scriptsDir, { recursive: true });
}

const version = extractVersionFromPyproject(PROJECT_ROOT);

module.exports = {
  apps: [
    // ===================================================================
    // 🚀 Automagik-Omni API Server (Priority 1 - Starts First)
    // ===================================================================
    {
      name: 'automagik-omni-api',
      cwd: PROJECT_ROOT,
      script: '.venv/bin/uvicorn',
      args: 'src.api.app:app --host 0.0.0.0 --port ' + (envVars.AUTOMAGIK_OMNI_API_PORT || '8882'),
      interpreter: 'none',
      version: version,
      env: {
        ...envVars,
        PYTHONPATH: PROJECT_ROOT,
        API_PORT: envVars.AUTOMAGIK_OMNI_API_PORT || '8882',
        API_HOST: envVars.AUTOMAGIK_OMNI_API_HOST || '0.0.0.0',
        API_KEY: envVars.AUTOMAGIK_OMNI_API_KEY || '',
        NODE_ENV: 'production'
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 1000,
      kill_timeout: 5000,
      error_file: path.join(PROJECT_ROOT, 'logs/api-err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/api-out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/api-combined.log'),
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },

    // ===================================================================
    // ⏳ API Health Check Wait Script (Priority 2 - Waits for API)
    // ===================================================================
    {
      name: 'automagik-omni-wait',
      cwd: PROJECT_ROOT,
      script: '.venv/bin/python',
      args: 'scripts/wait_for_api.py',
      interpreter: 'none',
      version: version,
      env: {
        ...envVars,
        PYTHONPATH: PROJECT_ROOT,
        AUTOMAGIK_OMNI_API_HOST: envVars.AUTOMAGIK_OMNI_API_HOST || 'localhost',
        AUTOMAGIK_OMNI_API_PORT: envVars.AUTOMAGIK_OMNI_API_PORT || '8882',
        DISCORD_HEALTH_CHECK_TIMEOUT: '120',
        NODE_ENV: 'production'
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: false, // Don't restart - it's a one-time check
      watch: false,
      restart_delay: 0,
      kill_timeout: 2000,
      error_file: path.join(PROJECT_ROOT, 'logs/wait-err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/wait-out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/wait-combined.log'),
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },

    // ===================================================================
    // 🤖 Automagik-Omni Discord Bot Service (Priority 3 - Starts After API)
    // ===================================================================
    {
      name: 'automagik-omni-discord',
      cwd: PROJECT_ROOT,
      script: '.venv/bin/python',
      args: 'src/commands/discord_cmd.py start ' + (envVars.DEFAULT_DISCORD_INSTANCE || 'testonho-discord'),
      interpreter: 'none',
      version: version,
      env: {
        ...envVars,
        PYTHONPATH: PROJECT_ROOT,
        AUTOMAGIK_OMNI_API_HOST: envVars.AUTOMAGIK_OMNI_API_HOST || 'localhost',
        AUTOMAGIK_OMNI_API_PORT: envVars.AUTOMAGIK_OMNI_API_PORT || '8882',
        DISCORD_HEALTH_CHECK_TIMEOUT: '60',
        NODE_ENV: 'production'
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      max_restarts: 5,
      min_uptime: '30s',
      restart_delay: 10000, // Wait 10s before restart to allow API recovery
      kill_timeout: 10000,
      error_file: path.join(PROJECT_ROOT, 'logs/discord-err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/discord-out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/discord-combined.log'),
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ],

  // ===================================================================
  // 🔧 PM2 Deploy Configuration (Optional)
  // ===================================================================
  deploy: {
    production: {
      user: 'deploy',
      host: 'your-server.com',
      ref: 'origin/main',
      repo: 'git@github.com:your-org/automagik-omni.git',
      path: '/var/www/automagik-omni',
      'pre-deploy-local': '',
      'post-deploy': 'uv sync && pm2 reload ecosystem_with_health_check.config.js --env production',
      'pre-setup': '',
      env: {
        NODE_ENV: 'production'
      }
    }
  }
};