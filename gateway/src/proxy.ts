/**
 * Bun-native HTTP proxy using fetch()
 * Replaces @fastify/http-proxy which uses undici Pool (not supported in Bun)
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';

interface ProxyOptions {
  prefix: string;
  upstream: string;
  rewritePrefix?: string;
  websocket?: boolean;
}

type ProxyBody =
  | string
  | ArrayBuffer
  | Uint8Array
  | Blob
  | FormData
  | URLSearchParams
  | ReadableStream
  | null
  | undefined;

/**
 * Register a proxy route that forwards requests to an upstream server
 * Uses Bun's native fetch() for HTTP proxying
 */
export async function registerProxy(fastify: FastifyInstance, opts: ProxyOptions): Promise<void> {
  const { prefix, upstream, rewritePrefix = prefix } = opts;

  // Handler for proxying requests
  const proxyHandler = async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      // Build upstream URL
      const originalUrl = request.url;
      const path = originalUrl.replace(new RegExp(`^${prefix}`), rewritePrefix);
      const url = `${upstream}${path}`;

      // Build headers - filter out undefined values and hop-by-hop headers
      const hopByHopHeaders = new Set([
        'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
        'te', 'trailers', 'transfer-encoding', 'upgrade', 'host'
      ]);

      const headers: Record<string, string> = {};
      for (const [key, value] of Object.entries(request.headers)) {
        if (value !== undefined && !hopByHopHeaders.has(key.toLowerCase())) {
          headers[key] = Array.isArray(value) ? value.join(', ') : value;
        }
      }

      // Handle body for non-GET/HEAD requests
      let body: ProxyBody;
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method)) {
        const candidate = request.body as unknown;
        if (
          typeof candidate === 'string' ||
          candidate instanceof ArrayBuffer ||
          candidate instanceof Uint8Array ||
          candidate instanceof Blob ||
          candidate instanceof FormData ||
          candidate instanceof URLSearchParams ||
          candidate instanceof ReadableStream ||
          candidate === null ||
          candidate === undefined
        ) {
          body = candidate;
        } else {
          body = JSON.stringify(candidate);
          const hasContentType = Object.keys(headers).some(
            (key) => key.toLowerCase() === 'content-type'
          );
          if (!hasContentType) {
            headers['content-type'] = 'application/json';
          }
        }
      }

      // Forward the request
      const response = await fetch(url, {
        method: request.method as string,
        headers,
        body,
      });

      // Set response status
      reply.code(response.status);

      // Forward response headers (excluding hop-by-hop headers)
      response.headers.forEach((value, key) => {
        const lowerKey = key.toLowerCase();
        if (!hopByHopHeaders.has(lowerKey)) {
          reply.header(key, value);
        }
      });

      // Stream the response body
      if (response.body) {
        return reply.send(response.body);
      } else {
        return reply.send();
      }
    } catch (error) {
      const err = error as Error;
      fastify.log.error({ err, url: request.url }, 'Proxy error');

      // Connection refused - upstream not available
      if (err.message?.includes('ECONNREFUSED') || err.message?.includes('fetch failed')) {
        return reply.code(502).send({
          statusCode: 502,
          error: 'Bad Gateway',
          message: `Upstream server unavailable: ${upstream}`,
        });
      }

      return reply.code(500).send({
        statusCode: 500,
        error: 'Internal Server Error',
        message: err.message || 'Proxy error',
      });
    }
  };

  // Register routes for the prefix
  // Handle /prefix/* (with path after prefix)
  fastify.all(`${prefix}/*`, proxyHandler);

  // Handle /prefix (exact match, no trailing content)
  fastify.all(prefix, proxyHandler);
}

/**
 * Register multiple proxy routes at once
 */
export async function registerProxies(
  fastify: FastifyInstance,
  proxies: ProxyOptions[]
): Promise<void> {
  for (const opts of proxies) {
    await registerProxy(fastify, opts);
  }
}
