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
import { execa } from 'execa';

import { ProcessManager } from './process.js';
import { HealthChecker } from './health.js';
import { PortRegistry } from './port-registry.js';
import { getLogTailer, getAvailableServices, LOG_SERVICES, restartPm2Service, getPm2Status, type ServiceName, type LogEntry } from './logs.js';

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

// Helper to parse port from env (strips quotes if present)
const parsePort = (value: string | undefined, defaultValue: string): number => {
  const raw = value ?? defaultValue;
  // Strip surrounding quotes if present (common .env parsing issue)
  const cleaned = raw.replace(/^["']|["']$/g, '');
  return parseInt(cleaned, 10);
};

// Configuration
const GATEWAY_PORT = parsePort(cliArgs.port as string ?? process.env.OMNI_PORT ?? process.env.AUTOMAGIK_OMNI_API_PORT, '8882');
const DEV_MODE = process.env.NODE_ENV === 'development' || cliArgs.dev === true;
const PROXY_ONLY = process.env.PROXY_ONLY === 'true' || cliArgs.proxyOnly === true;

// Legacy env var support for PROXY_ONLY mode (connecting to external services)
const PROXY_PYTHON_PORT = parsePort(process.env.PYTHON_API_PORT, '18881');
const PROXY_EVOLUTION_PORT = parsePort(process.env.EVOLUTION_PORT, '18082');
const PROXY_VITE_PORT = parsePort(process.env.VITE_PORT, '19882');

export async function main() {
  // Initialize port registry for dynamic port allocation
  const portRegistry = new PortRegistry();

  // Allocate ports for internal services (unless proxy-only mode)
  let PYTHON_PORT: number;
  let EVOLUTION_PORT: number | undefined;
  let VITE_PORT: number | undefined;

  if (PROXY_ONLY) {
    // Proxy-only mode: use configured ports to connect to external services
    PYTHON_PORT = PROXY_PYTHON_PORT;
    EVOLUTION_PORT = PROXY_EVOLUTION_PORT;
    VITE_PORT = DEV_MODE ? PROXY_VITE_PORT : undefined;
  } else {
    // Normal mode: allocate ports dynamically from dedicated ranges
    const pythonAllocation = await portRegistry.allocate('python');
    PYTHON_PORT = pythonAllocation.port;

    try {
      const evolutionAllocation = await portRegistry.allocate('evolution');
      EVOLUTION_PORT = evolutionAllocation.port;
    } catch (error) {
      console.warn('[Gateway] Could not allocate Evolution port:', error);
      EVOLUTION_PORT = undefined;
    }

    if (DEV_MODE) {
      const viteAllocation = await portRegistry.allocate('vite');
      VITE_PORT = viteAllocation.port;
    }
  }

  console.log(`
╔═══════════════════════════════════════════════════════════╗
║           Automagik Omni Gateway                          ║
║           Single Port Access to All Services              ║
╚═══════════════════════════════════════════════════════════╝

Mode: ${PROXY_ONLY ? 'PROXY-ONLY' : (DEV_MODE ? 'DEVELOPMENT' : 'PRODUCTION')}
Gateway Port: ${GATEWAY_PORT} (--port or OMNI_PORT to change)
Python API:   http://127.0.0.1:${PYTHON_PORT} (auto-managed)
${EVOLUTION_PORT ? `Evolution:    http://127.0.0.1:${EVOLUTION_PORT} (auto-managed)` : 'Evolution:    (not allocated)'}
${DEV_MODE && VITE_PORT ? `Vite Dev:     http://127.0.0.1:${VITE_PORT} (auto-managed)` : ''}
${PROXY_ONLY ? '(Proxy-only mode: not spawning processes, connecting to existing services)' : ''}
`);

  // Initialize process manager with port registry
  const processManager = new ProcessManager(portRegistry, {
    devMode: DEV_MODE,
  });

  // Initialize health checker with port registry
  const healthChecker = new HealthChecker(portRegistry, ROOT_DIR);

  // Start backend services (unless proxy-only mode)
  if (!PROXY_ONLY) {
    console.log('\n[Gateway] Starting backend services...\n');

    // Start Python API first (critical)
    await processManager.startPython();

    // Start standalone MCP server (eliminates double proxy layer)
    await processManager.startMCP();

    // Channel startup behavior: on-demand by default, eager if EAGER_CHANNELS=true
    if (processManager.isLazyModeEnabled()) {
      console.log('[Gateway] On-demand mode (default) - channels start when user enables them');
      console.log('[Gateway] Set EAGER_CHANNELS=true to auto-start channels at boot');
    } else {
      console.log('[Gateway] Eager mode enabled - auto-starting all channels...');
      // Start Evolution API (WhatsApp channel - optional, soft-fail like Discord)
      try {
        await processManager.startEvolution();
      } catch (error) {
        console.warn('[Gateway] Evolution/WhatsApp service failed to start, continuing without it');
        console.warn('[Gateway] WhatsApp functionality will be unavailable');
        console.warn('[Gateway] Error:', error instanceof Error ? error.message : error);
      }

      // Start Discord service manager (optional but recommended)
      try {
        await processManager.startDiscord();
      } catch (error) {
        console.warn('[Gateway] Discord service failed to start, continuing without it');
        console.warn('[Gateway] Install Discord support: uv pip install -e ".[discord]"');
      }
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
  // Route: /api/logs/* - Log streaming endpoints
  // ============================================================

  // GET /api/logs/services - List available log services
  fastify.get('/api/logs/services', async () => {
    return getAvailableServices();
  });

  // GET /api/logs/recent - Get recent log entries
  fastify.get<{
    Querystring: { services?: string; limit?: string };
  }>('/api/logs/recent', async (request) => {
    const { services: servicesParam, limit: limitParam } = request.query;

    const limit = Math.min(Math.max(parseInt(limitParam ?? '100', 10), 1), 500);
    const services = servicesParam
      ? servicesParam.split(',').filter((s): s is ServiceName => s in LOG_SERVICES)
      : Object.keys(LOG_SERVICES) as ServiceName[];

    const tailer = getLogTailer();
    return tailer.getRecentLogs(services, limit);
  });

  // GET /api/logs/stream - SSE endpoint for real-time logs
  fastify.get<{
    Querystring: { services?: string };
  }>('/api/logs/stream', async (request, reply) => {
    const { services: servicesParam } = request.query;

    const services = servicesParam
      ? servicesParam.split(',').filter((s): s is ServiceName => s in LOG_SERVICES)
      : Object.keys(LOG_SERVICES) as ServiceName[];

    // Set SSE headers
    reply.raw.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'X-Accel-Buffering': 'no', // Disable nginx buffering
    });

    // Send initial connection message
    reply.raw.write(`event: connected\ndata: ${JSON.stringify({ services, timestamp: new Date().toISOString() })}\n\n`);

    const tailer = getLogTailer();

    // Start tailing requested services and track listener counts
    for (const service of services) {
      await tailer.startTailing(service);
      tailer.incrementListeners(service);
    }

    // Handler for new log entries
    const logHandler = (entry: LogEntry) => {
      if (services.includes(entry.service)) {
        reply.raw.write(`event: log\ndata: ${JSON.stringify(entry)}\n\n`);
      }
    };

    tailer.on('log', logHandler);

    // Heartbeat to keep connection alive
    const heartbeatInterval = setInterval(() => {
      reply.raw.write(`: heartbeat ${Date.now()}\n\n`);
    }, 30000);

    // Cleanup on close - decrement listener counts (stops tailing when no listeners)
    request.raw.on('close', () => {
      clearInterval(heartbeatInterval);
      tailer.off('log', logHandler);
      for (const service of services) {
        tailer.decrementListeners(service);
      }
    });

    // Don't end the response - SSE keeps connection open
    return reply;
  });

  // POST /api/logs/restart/:service - Restart a PM2 service
  // Security: Only allow from localhost to prevent unauthorized service restarts
  fastify.post<{
    Params: { service: string };
  }>('/api/logs/restart/:service', async (request, reply) => {
    // Only allow from localhost
    const clientIp = request.ip;
    if (!['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(clientIp)) {
      return reply.status(403).send({
        success: false,
        message: 'Restart endpoint only accessible from localhost',
      });
    }

    const { service } = request.params;

    if (!(service in LOG_SERVICES)) {
      return reply.status(400).send({
        success: false,
        message: `Invalid service: ${service}. Valid services: ${Object.keys(LOG_SERVICES).join(', ')}`,
      });
    }

    const result = await restartPm2Service(service as ServiceName);
    return reply.status(result.success ? 200 : 500).send(result);
  });

  // GET /api/logs/status/:service - Get PM2 status for a service
  fastify.get<{
    Params: { service: string };
  }>('/api/logs/status/:service', async (request, reply) => {
    const { service } = request.params;

    if (!(service in LOG_SERVICES)) {
      return reply.status(400).send({
        error: `Invalid service: ${service}`,
      });
    }

    const status = await getPm2Status(service as ServiceName);
    return status || { online: false, message: 'Service not found in PM2' };
  });

  // GET /api/logs/status - Get PM2 status for all services
  fastify.get('/api/logs/status', async () => {
    const statuses: Record<string, Awaited<ReturnType<typeof getPm2Status>> | { online: false }> = {};

    await Promise.all(
      (Object.keys(LOG_SERVICES) as ServiceName[]).map(async (service) => {
        statuses[service] = await getPm2Status(service) || { online: false };
      })
    );

    return statuses;
  });

  // ============================================================
  // Route: /api/gateway/discord-* - Discord setup endpoints
  // ============================================================

  // GET /api/gateway/discord-status - Check if Discord dependencies are installed
  fastify.get('/api/gateway/discord-status', async () => {
    try {
      // Check if discord.py is importable
      const result = await execa('uv', ['run', 'python', '-c', 'import discord; print(discord.__version__)'], {
        cwd: ROOT_DIR,
        timeout: 10000,
      });
      return {
        installed: true,
        version: result.stdout.trim(),
      };
    } catch {
      return {
        installed: false,
        version: null,
      };
    }
  });

  // GET /api/gateway/install-discord - Install Discord dependencies with SSE streaming
  // Note: Using GET because EventSource API only supports GET requests
  // Public endpoint (no auth) - used during onboarding before authentication is configured
  // Matches WhatsApp setup endpoints pattern in /setup/channels/*
  fastify.get('/api/gateway/install-discord', async (request, reply) => {
    // Set SSE headers
    reply.raw.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'X-Accel-Buffering': 'no',
    });

    // Send initial message
    reply.raw.write(`event: status\ndata: ${JSON.stringify({ phase: 'starting', message: 'Installing Discord dependencies...' })}\n\n`);

    try {
      const proc = execa('uv', ['sync', '--extra', 'discord'], {
        cwd: ROOT_DIR,
        all: true, // Combine stdout and stderr
      });

      // Stream output
      proc.all?.on('data', (chunk: Buffer) => {
        const lines = chunk.toString().split('\n').filter(Boolean);
        for (const line of lines) {
          reply.raw.write(`event: log\ndata: ${JSON.stringify({ timestamp: new Date().toISOString(), message: line })}\n\n`);
        }
      });

      await proc;

      // Verify installation
      try {
        const verify = await execa('uv', ['run', 'python', '-c', 'import discord; print(discord.__version__)'], {
          cwd: ROOT_DIR,
          timeout: 10000,
        });
        reply.raw.write(`event: status\ndata: ${JSON.stringify({ phase: 'complete', message: 'Discord installed successfully', version: verify.stdout.trim() })}\n\n`);
      } catch {
        reply.raw.write(`event: status\ndata: ${JSON.stringify({ phase: 'complete', message: 'Installation completed' })}\n\n`);
      }

      reply.raw.write(`event: done\ndata: ${JSON.stringify({ success: true })}\n\n`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Installation failed';
      reply.raw.write(`event: error\ndata: ${JSON.stringify({ message })}\n\n`);
      reply.raw.write(`event: done\ndata: ${JSON.stringify({ success: false })}\n\n`);
    }

    reply.raw.end();
    return reply;
  });

  // ============================================================
  // Route: /api/v1/* - Proxy to Python FastAPI
  // ============================================================
  await fastify.register(proxy, {
    upstream: `http://127.0.0.1:${PYTHON_PORT}`,
    prefix: '/api/v1',
    rewritePrefix: '/api/v1',
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
  // Route: /mcp - Proxy to standalone MCP server (eliminates double proxy layer)
  // ============================================================
  await fastify.register(proxy, {
    upstream: 'http://127.0.0.1:18880',  // Direct to standalone MCP server
    prefix: '/mcp',
    rewritePrefix: '/',  // MCP server serves at root
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
  if (EVOLUTION_PORT) {
    await fastify.register(proxy, {
      upstream: `http://127.0.0.1:${EVOLUTION_PORT}`,
      prefix: '/evolution',
      rewritePrefix: '',
      http2: false,
    });
  } else {
    // Evolution not available - return 503
    fastify.all('/evolution/*', async (_request, reply) => {
      return reply.status(503).send({
        error: 'Evolution API not available',
        message: 'Evolution API port was not allocated. Check gateway logs.',
      });
    });
  }

  // ============================================================
  // Route: /* - UI (static files in prod, Vite proxy in dev)
  // ============================================================
  const uiDistDir = join(ROOT_DIR, 'resources', 'ui', 'dist');

  if (DEV_MODE && VITE_PORT) {
    // Development: Proxy to Vite dev server (with WebSocket for HMR)
    await fastify.register(proxy, {
      upstream: `http://127.0.0.1:${VITE_PORT}`,
      prefix: '/',
      rewritePrefix: '/',
      websocket: true,
      http2: false,
    });
  } else if (existsSync(uiDistDir)) {
    // Production: Serve static files (in its own plugin context)
    await fastify.register(async (fastify) => {
      await fastify.register(fastifyStatic, {
        root: uiDistDir,
        prefix: '/',
      });
    });

    // SPA fallback - serve index.html for unmatched routes
    fastify.setNotFoundHandler(async (request, reply) => {
      // Don't serve index.html for API routes
      if (request.url.startsWith('/api/v1') ||
          request.url.startsWith('/api/gateway') ||
          request.url.startsWith('/api/logs') ||
          request.url.startsWith('/api/setup') ||
          request.url.startsWith('/webhook') ||
          request.url.startsWith('/evolution') ||
          request.url.startsWith('/health') ||
          request.url.startsWith('/docs') ||
          request.url.startsWith('/redoc') ||
          request.url.startsWith('/openapi.json') ||
          request.url.startsWith('/mcp')) {
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
        proxyOnly: PROXY_ONLY,
        lazyChannels: processManager.isLazyModeEnabled(),
        uptime: process.uptime(),
      },
      ports: portRegistry.toJSON(),
      processes: processManager.getStatus(),
    };
  });

  // ============================================================
  // Channel management endpoints (for on-demand startup)
  // ============================================================

  // List available channels and their status
  fastify.get('/gateway/channels', async () => {
    const channels = ['evolution', 'discord'];
    return {
      lazyMode: processManager.isLazyModeEnabled(),
      channels: channels.map(channel => ({
        name: channel,
        enabled: processManager.isChannelEnabled(channel),
        running: processManager.isChannelRunning(channel),
      })),
    };
  });

  // Start a channel on-demand
  fastify.post<{ Params: { channel: string } }>('/gateway/channels/:channel/start', async (request, reply) => {
    const { channel } = request.params;
    const validChannels = ['evolution', 'discord'];

    if (!validChannels.includes(channel.toLowerCase())) {
      reply.status(400);
      return { error: `Invalid channel: ${channel}. Valid channels: ${validChannels.join(', ')}` };
    }

    if (!processManager.isChannelEnabled(channel)) {
      reply.status(400);
      return { error: `Channel ${channel} is disabled via ${channel.toUpperCase()}_ENABLED=false` };
    }

    if (processManager.isChannelRunning(channel)) {
      return { status: 'already_running', channel };
    }

    try {
      await processManager.ensureChannelRunning(channel);
      return { status: 'started', channel };
    } catch (error) {
      reply.status(500);
      return { error: `Failed to start ${channel}: ${error instanceof Error ? error.message : error}` };
    }
  });

  // Stop a channel
  fastify.post<{ Params: { channel: string } }>('/gateway/channels/:channel/stop', async (request, reply) => {
    const { channel } = request.params;
    const validChannels = ['evolution', 'discord'];

    if (!validChannels.includes(channel.toLowerCase())) {
      reply.status(400);
      return { error: `Invalid channel: ${channel}. Valid channels: ${validChannels.join(', ')}` };
    }

    try {
      const stopped = await processManager.stopChannel(channel);
      return { status: stopped ? 'stopped' : 'not_running', channel };
    } catch (error) {
      reply.status(500);
      return { error: `Failed to stop ${channel}: ${error instanceof Error ? error.message : error}` };
    }
  });

  // Restart a channel
  fastify.post<{ Params: { channel: string } }>('/gateway/channels/:channel/restart', async (request, reply) => {
    const { channel } = request.params;
    const validChannels = ['evolution', 'discord'];

    if (!validChannels.includes(channel.toLowerCase())) {
      reply.status(400);
      return { error: `Invalid channel: ${channel}. Valid channels: ${validChannels.join(', ')}` };
    }

    try {
      await processManager.stopChannel(channel);
      await new Promise(resolve => setTimeout(resolve, 2000)); // Cleanup delay
      await processManager.ensureChannelRunning(channel);
      return { status: 'restarted', channel };
    } catch (error) {
      reply.status(500);
      return { error: `Failed to restart ${channel}: ${error instanceof Error ? error.message : error}` };
    }
  });

  // Get detailed status for a channel
  fastify.get<{ Params: { channel: string } }>('/gateway/channels/:channel/status', async (request, reply) => {
    const { channel } = request.params;
    const validChannels = ['evolution', 'discord'];

    if (!validChannels.includes(channel.toLowerCase())) {
      reply.status(400);
      return { error: `Invalid channel: ${channel}` };
    }

    const managed = processManager.getProcessInfo(channel);

    return {
      channel,
      running: processManager.isChannelRunning(channel),
      enabled: processManager.isChannelEnabled(channel),
      healthy: managed?.healthy ?? false,
      pid: managed?.process?.pid,
      port: managed?.port,
    };
  });

  // Cleanup on shutdown (idempotent - safe to call multiple times)
  let cleanupInProgress = false;
  const cleanup = async () => {
    if (cleanupInProgress) return;
    cleanupInProgress = true;

    console.log('[Gateway] Starting graceful shutdown...');

    // Shutdown process manager (stops all subprocesses)
    await processManager.shutdown();

    // Release all port allocations
    portRegistry.releaseAll();

    console.log('[Gateway] Cleanup complete');
  };

  // Register signal handlers (deduplicated - only here, not in ProcessManager)
  process.on('SIGTERM', async () => {
    await cleanup();
    process.exit(0);
  });
  process.on('SIGINT', async () => {
    await cleanup();
    process.exit(0);
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

    return fastify;
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
