/**
 * Automagik Omni Gateway
 * Single-port TypeScript gateway that proxies to Python API, Evolution API, and serves UI
 */

import Fastify from 'fastify';
import proxy from '@fastify/http-proxy';
import fastifyStatic from '@fastify/static';
import cors from '@fastify/cors';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { config } from 'dotenv';

import { ProcessManager } from './process.js';
import { HealthChecker } from './health.js';

// Load environment variables
config({ path: join(dirname(fileURLToPath(import.meta.url)), '../../.env') });

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = join(__dirname, '../..');

// Parse CLI arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const result: Record<string, string | boolean> = {};

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--dev') result.dev = true;
    else if (arg === '--proxy-only') result.proxyOnly = true;
    else if (arg === '--port' && args[i + 1]) {
      result.port = args[++i];
    } else if (arg.startsWith('--port=')) {
      result.port = arg.split('=')[1];
    }
  }
  return result;
}

const cliArgs = parseArgs();

// Find available port starting from preferred
async function findAvailablePort(preferred: number, host = '127.0.0.1'): Promise<number> {
  const net = await import('node:net');

  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(preferred, host, () => {
      server.close(() => resolve(preferred));
    });
    server.on('error', () => {
      // Port in use, try next
      resolve(findAvailablePort(preferred + 1, host));
    });
  });
}

// Configuration
const GATEWAY_PORT = parseInt(cliArgs.port as string ?? process.env.OMNI_PORT ?? process.env.AUTOMAGIK_OMNI_API_PORT ?? '8882', 10);
const PYTHON_PORT_PREFERRED = parseInt(process.env.PYTHON_API_PORT ?? '18881', 10);
const EVOLUTION_PORT_PREFERRED = parseInt(process.env.EVOLUTION_PORT ?? '18082', 10);
const VITE_PORT_PREFERRED = parseInt(process.env.VITE_PORT ?? '19882', 10);
const DEV_MODE = process.env.NODE_ENV === 'development' || cliArgs.dev === true;
const PROXY_ONLY = process.env.PROXY_ONLY === 'true' || cliArgs.proxyOnly === true;

async function main() {
  // Resolve ports (find available ones for internal services)
  const PYTHON_PORT = PROXY_ONLY
    ? PYTHON_PORT_PREFERRED
    : await findAvailablePort(PYTHON_PORT_PREFERRED);
  const EVOLUTION_PORT = PROXY_ONLY
    ? EVOLUTION_PORT_PREFERRED
    : await findAvailablePort(EVOLUTION_PORT_PREFERRED);
  const VITE_PORT = PROXY_ONLY
    ? VITE_PORT_PREFERRED
    : await findAvailablePort(VITE_PORT_PREFERRED);

  console.log(`
╔═══════════════════════════════════════════════════════════╗
║           Automagik Omni Gateway                          ║
║           Single Port Access to All Services              ║
╚═══════════════════════════════════════════════════════════╝

Mode: ${PROXY_ONLY ? 'PROXY-ONLY' : (DEV_MODE ? 'DEVELOPMENT' : 'PRODUCTION')}
Gateway Port: ${GATEWAY_PORT} (--port or OMNI_PORT to change)
Python API:   http://127.0.0.1:${PYTHON_PORT}${PYTHON_PORT !== PYTHON_PORT_PREFERRED ? ' (auto-assigned)' : ''}
Evolution:    http://127.0.0.1:${EVOLUTION_PORT}${EVOLUTION_PORT !== EVOLUTION_PORT_PREFERRED ? ' (auto-assigned)' : ''}
${DEV_MODE ? `Vite Dev:     http://127.0.0.1:${VITE_PORT}${VITE_PORT !== VITE_PORT_PREFERRED ? ' (auto-assigned)' : ''}` : ''}
${PROXY_ONLY ? '(Proxy-only mode: not spawning processes, connecting to existing services)' : ''}
`);

  // Initialize process manager
  const processManager = new ProcessManager({
    pythonPort: PYTHON_PORT,
    evolutionPort: EVOLUTION_PORT,
    vitePort: VITE_PORT,
    devMode: DEV_MODE,
  });

  // Initialize health checker
  const healthChecker = new HealthChecker({
    pythonUrl: `http://127.0.0.1:${PYTHON_PORT}/health`,
    evolutionUrl: `http://127.0.0.1:${EVOLUTION_PORT}/`,
    viteUrl: DEV_MODE ? `http://127.0.0.1:${VITE_PORT}/` : undefined,
  });

  // Start backend services (unless proxy-only mode)
  if (!PROXY_ONLY) {
    console.log('\n[Gateway] Starting backend services...\n');

    // Start Python API first (critical)
    await processManager.startPython();

    // Start Evolution API (optional, can fail)
    try {
      await processManager.startEvolution();
    } catch (error) {
      console.warn('[Gateway] Evolution API failed to start, continuing without it');
    }

    // Start Vite in dev mode
    if (DEV_MODE) {
      await processManager.startVite();
    }
  } else {
    console.log('\n[Gateway] Proxy-only mode - connecting to existing services...\n');
  }

  // Create Fastify server
  const fastify = Fastify({
    logger: {
      level: DEV_MODE ? 'info' : 'warn',
      transport: DEV_MODE ? {
        target: 'pino-pretty',
        options: { colorize: true },
      } : undefined,
    },
  });

  // Enable CORS
  await fastify.register(cors, {
    origin: true,
    credentials: true,
  });

  // ============================================================
  // Route: /health - Aggregated health check
  // ============================================================
  fastify.get('/health', async () => {
    return healthChecker.getHealth();
  });

  // ============================================================
  // Route: /api/* - Proxy to Python FastAPI
  // ============================================================
  await fastify.register(proxy, {
    upstream: `http://127.0.0.1:${PYTHON_PORT}`,
    prefix: '/api',
    rewritePrefix: '/api',
    http2: false,
  });

  // ============================================================
  // Route: /webhook/* - Proxy to Python FastAPI (Evolution webhooks)
  // ============================================================
  await fastify.register(proxy, {
    upstream: `http://127.0.0.1:${PYTHON_PORT}`,
    prefix: '/webhook',
    rewritePrefix: '/webhook',
    http2: false,
  });

  // ============================================================
  // Route: /docs - Proxy OpenAPI docs to Python
  // ============================================================
  await fastify.register(proxy, {
    upstream: `http://127.0.0.1:${PYTHON_PORT}`,
    prefix: '/docs',
    rewritePrefix: '/docs',
    http2: false,
  });

  await fastify.register(proxy, {
    upstream: `http://127.0.0.1:${PYTHON_PORT}`,
    prefix: '/openapi.json',
    rewritePrefix: '/openapi.json',
    http2: false,
  });

  await fastify.register(proxy, {
    upstream: `http://127.0.0.1:${PYTHON_PORT}`,
    prefix: '/redoc',
    rewritePrefix: '/redoc',
    http2: false,
  });

  // ============================================================
  // Route: /evolution/* - Proxy to Evolution API
  // ============================================================
  await fastify.register(proxy, {
    upstream: `http://127.0.0.1:${EVOLUTION_PORT}`,
    prefix: '/evolution',
    rewritePrefix: '',
    http2: false,
  });

  // ============================================================
  // Route: /* - UI (static files in prod, Vite proxy in dev)
  // ============================================================
  const uiDistDir = join(ROOT_DIR, 'resources', 'ui', 'dist');

  if (DEV_MODE) {
    // Development: Proxy to Vite dev server (with WebSocket for HMR)
    await fastify.register(proxy, {
      upstream: `http://127.0.0.1:${VITE_PORT}`,
      prefix: '/',
      rewritePrefix: '/',
      websocket: true,
      http2: false,
    });
  } else if (existsSync(uiDistDir)) {
    // Production: Serve static files
    await fastify.register(fastifyStatic, {
      root: uiDistDir,
      prefix: '/',
    });

    // SPA fallback - serve index.html for unmatched routes
    fastify.setNotFoundHandler(async (request, reply) => {
      // Don't serve index.html for API routes
      if (request.url.startsWith('/api') ||
          request.url.startsWith('/webhook') ||
          request.url.startsWith('/evolution') ||
          request.url.startsWith('/health')) {
        return reply.status(404).send({ error: 'Not Found' });
      }
      return reply.sendFile('index.html');
    });
  } else {
    console.warn('[Gateway] UI dist not found, run `npm run build` in resources/ui first');
    fastify.get('/', async () => ({
      message: 'Automagik Omni Gateway',
      status: 'running',
      ui: 'not built - run npm run build in resources/ui',
      api: `/api/v1`,
      docs: `/docs`,
      health: `/health`,
    }));
  }

  // ============================================================
  // Status endpoint (gateway internals)
  // ============================================================
  fastify.get('/gateway/status', async () => {
    return {
      gateway: {
        port: GATEWAY_PORT,
        mode: DEV_MODE ? 'development' : 'production',
        uptime: process.uptime(),
      },
      processes: processManager.getStatus(),
    };
  });

  // Start the gateway server
  try {
    await fastify.listen({
      port: GATEWAY_PORT,
      host: '0.0.0.0',
    });

    console.log(`
╔═══════════════════════════════════════════════════════════╗
║  Gateway Ready!                                           ║
║                                                           ║
║  Access all services at:                                  ║
║  → http://localhost:${GATEWAY_PORT.toString().padEnd(38)}║
║                                                           ║
║  Routes:                                                  ║
║  → /           UI Dashboard                               ║
║  → /api/v1/*   REST API                                   ║
║  → /docs       API Documentation                          ║
║  → /webhook/*  Webhooks                                   ║
║  → /evolution/* WhatsApp API                              ║
║  → /health     Health Check                               ║
╚═══════════════════════════════════════════════════════════╝
`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
