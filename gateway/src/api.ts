/**
 * Programmatic API for embedding Omni in Node.js applications
 *
 * @example
 * ```typescript
 * import { OmniServer } from '@automagik/omni';
 *
 * const server = new OmniServer({ port: 8882, dev: true });
 * await server.start();
 *
 * // ... your app logic
 *
 * await server.stop();
 * ```
 */

import type { FastifyInstance } from 'fastify';

export interface OmniServerOptions {
  /** Port to listen on (default: 8882) */
  port?: number;
  /** Development mode (enables Vite dev server, auto-reload) */
  dev?: boolean;
  /** Proxy-only mode (connect to external services instead of spawning) */
  proxyOnly?: boolean;
}

export interface OmniServerInfo {
  port: number;
  mode: 'development' | 'production';
  proxyOnly: boolean;
  uptime: number;
}

/**
 * Programmatic Omni server instance
 *
 * This class allows you to embed the Omni gateway in your Node.js application
 * and control its lifecycle programmatically.
 */
export class OmniServer {
  private serverInstance: FastifyInstance | null = null;
  private originalEnv: Record<string, string | undefined> = {};

  constructor(private options: OmniServerOptions = {}) {}

  /**
   * Start the Omni server
   *
   * @throws Error if server is already running
   */
  async start(): Promise<void> {
    if (this.serverInstance) {
      throw new Error('Server is already running');
    }

    // Save original env vars
    this.originalEnv = {
      OMNI_PORT: process.env.OMNI_PORT,
      NODE_ENV: process.env.NODE_ENV,
      PROXY_ONLY: process.env.PROXY_ONLY,
    };

    // Set environment variables
    if (this.options.port) {
      process.env.OMNI_PORT = this.options.port.toString();
    }
    if (this.options.dev) {
      process.env.NODE_ENV = 'development';
    }
    if (this.options.proxyOnly) {
      process.env.PROXY_ONLY = 'true';
    }

    // Dynamically import and start the gateway
    const { main: startGateway } = await import('./index.js');
    const instance = await startGateway();
    if (instance) {
      this.serverInstance = instance;
    } else {
      throw new Error('Failed to start gateway - no instance returned');
    }
  }

  /**
   * Stop the Omni server
   *
   * @throws Error if server is not running
   */
  async stop(): Promise<void> {
    if (!this.serverInstance) {
      throw new Error('Server is not running');
    }

    // Gracefully close the server
    await this.serverInstance.close();
    this.serverInstance = null;

    // Restore original env vars
    for (const [key, value] of Object.entries(this.originalEnv)) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }

  /**
   * Get server information
   *
   * @throws Error if server is not running
   */
  getInfo(): OmniServerInfo {
    if (!this.serverInstance) {
      throw new Error('Server is not running');
    }

    return {
      port: parseInt(process.env.OMNI_PORT || '8882', 10),
      mode: process.env.NODE_ENV === 'development' ? 'development' : 'production',
      proxyOnly: process.env.PROXY_ONLY === 'true',
      uptime: process.uptime(),
    };
  }

  /**
   * Check if server is running
   */
  isRunning(): boolean {
    return this.serverInstance !== null;
  }
}

// Re-export main for direct use (advanced users)
export { main as startGateway } from './index.js';
