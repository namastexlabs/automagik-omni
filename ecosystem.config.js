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

// Windows Process Grouping: Set App User Model ID for Task Manager grouping
// This ensures all PM2 processes (api, discord, wait) appear under single "Automagik Omni" entry
if (process.platform === 'win32') {
  try {
    // Set AUMID for PM2 parent process using environment variable
    // Child processes will inherit this and appear grouped in Task Manager
    process.env.ELECTRON_AUMID = 'com.namastex.automagik-omni';

    // Also set as regular env var for Python processes
    envVars.ELECTRON_AUMID = 'com.namastex.automagik-omni';

    console.log('🔗 Windows process grouping enabled (AUMID: com.namastex.automagik-omni)');
  } catch (error) {
    console.warn('⚠️ Failed to set Windows process grouping:', error.message);
  }
}

module.exports = {
  apps: [
    // ===================================================================
    // 🐘 Evolution API (SQLite) - WhatsApp Gateway (Priority 0 - Starts First)
    // ===================================================================
    {
      name: 'Evolution API (SQLite)',
      cwd: envVars.EVOLUTION_API_PATH ? path.join(PROJECT_ROOT, envVars.EVOLUTION_API_PATH) : path.join(PROJECT_ROOT, 'resources/evolution-api'),
      script: 'npm',
      args: 'run start',
      interpreter: 'none',
      version: '2.3.6',
      env: {
        NODE_ENV: 'production',
        // Use env vars from .env with EVOLUTION_ prefix
        SERVER_PORT: envVars.EVOLUTION_API_PORT || '18082',
        SERVER_URL: envVars.EVOLUTION_API_URL || 'http://localhost:18082',
        SERVER_DISABLE_MANAGER: 'true',
        SERVER_DISABLE_DOCS: 'true',
        // Database - Fixed for SQLite local setup
        DATABASE_ENABLED: 'true',
        DATABASE_PROVIDER: 'sqlite',
        DATABASE_CONNECTION_URI: `file:${path.join(envVars.EVOLUTION_API_PATH ? path.join(PROJECT_ROOT, envVars.EVOLUTION_API_PATH) : path.join(PROJECT_ROOT, 'resources/evolution-api'), 'prisma/evolution-desktop.db')}`,
        DATABASE_SAVE_DATA_INSTANCE: 'true',
        DATABASE_SAVE_DATA_NEW_MESSAGE: 'true',
        DATABASE_SAVE_MESSAGE_UPDATE: 'true',
        DATABASE_SAVE_DATA_CONTACTS: 'true',
        DATABASE_SAVE_DATA_CHATS: 'true',
        // Cache - Fixed for local (no Redis)
        CACHE_REDIS_ENABLED: 'false',
        CACHE_LOCAL_ENABLED: 'true',
        // Auth from .env
        AUTHENTICATION_API_KEY: envVars.EVOLUTION_API_KEY || '',
        // Disable integrations - Fixed for local
        TELEMETRY_ENABLED: 'false',
        PROVIDER_ENABLED: 'false',
        RABBITMQ_ENABLED: 'false',
        WEBSOCKET_ENABLED: 'false',
        // Logging from .env
        LOG_LEVEL: envVars.EVOLUTION_LOG_LEVEL || 'ERROR,WARN',
        LOG_COLOR: 'false',
        LOG_BAILEYS: envVars.EVOLUTION_LOG_BAILEYS || 'error',
        PROCESS_TITLE: 'Evolution API (SQLite)'
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 3000,
      kill_timeout: 5000,
      error_file: path.join(PROJECT_ROOT, 'logs/evolution-err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/evolution-out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/evolution-combined.log'),
      merge_logs: true,
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },

    // ===================================================================
    // 🚀 Automagik-Omni API Server (Priority 1 - Starts Second)
    // ===================================================================
    {
      name: 'Omni Backend - API',
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
        NODE_ENV: 'production',
        // Set process title for Windows Task Manager
        PROCESS_TITLE: 'Omni Backend - API'
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
      name: 'Omni Backend - Health Check',
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
        NODE_ENV: 'production',
        // Set process title for Windows Task Manager
        PROCESS_TITLE: 'Omni Backend - Health Check'
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
    // 🤖 Automagik-Omni Discord Service Manager (Priority 3 - Manages ALL Discord Bots)
    // ===================================================================
    {
      name: 'Omni Backend - Discord',
      cwd: PROJECT_ROOT,
      script: '.venv/bin/python',
      args: 'src/commands/discord_service_manager.py',
      interpreter: 'none',
      version: version,
      env: {
        ...envVars,
        PYTHONPATH: PROJECT_ROOT,
        AUTOMAGIK_OMNI_API_HOST: envVars.AUTOMAGIK_OMNI_API_HOST || 'localhost',
        AUTOMAGIK_OMNI_API_PORT: envVars.AUTOMAGIK_OMNI_API_PORT || '8882',
        DISCORD_HEALTH_CHECK_TIMEOUT: '60',
        NODE_ENV: 'production',
        // Set process title for Windows Task Manager
        PROCESS_TITLE: 'Omni Backend - Discord'
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
    },

    // ===================================================================
    // 🎨 Omni UI (Frontend Dashboard)
    // ===================================================================
    {
      name: 'omni-ui',
      cwd: path.join(PROJECT_ROOT, 'resources/ui'),
      script: 'npm',
      args: 'run dev',
      interpreter: 'none',
      env: {
        NODE_ENV: 'development',
        UI_HOST: envVars.UI_HOST || '0.0.0.0',
        UI_PORT: envVars.UI_PORT || '9882',
        VITE_API_URL: `http://localhost:${envVars.AUTOMAGIK_OMNI_API_PORT || '8882'}`,
        VITE_API_KEY: envVars.AUTOMAGIK_OMNI_API_KEY || 'your-secret-api-key-here',
        PROCESS_TITLE: 'Omni UI (Vite)'
      },
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      max_restarts: 10,
      min_uptime: '5s',
      restart_delay: 2000,
      kill_timeout: 3000,
      error_file: path.join(PROJECT_ROOT, 'logs/omni-ui-err.log'),
      out_file: path.join(PROJECT_ROOT, 'logs/omni-ui-out.log'),
      log_file: path.join(PROJECT_ROOT, 'logs/omni-ui-combined.log'),
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