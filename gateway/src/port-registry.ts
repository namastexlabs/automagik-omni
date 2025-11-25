/**
 * Port Registry for Automagik Omni Gateway
 * Centralized port allocation and tracking for internal services
 *
 * Each service gets a dedicated non-overlapping port range:
 * - Python API: 18881-18899
 * - Evolution API: 18901-18919
 * - Vite Dev: 19881-19899
 *
 * All services bind to 127.0.0.1 (internal only).
 * Gateway remains the only externally accessible port (configurable via OMNI_PORT).
 */

import { EventEmitter } from 'node:events';
import { createServer, type Server } from 'node:net';

export type ServiceId = 'python' | 'evolution' | 'vite';

export interface PortAllocation {
  serviceId: ServiceId;
  port: number;
  allocatedAt: Date;
}

interface PortRange {
  min: number;
  max: number;
}

/**
 * Non-overlapping port ranges for each service.
 * This ensures services can never conflict with each other.
 */
const PORT_RANGES: Record<ServiceId, PortRange> = {
  python: { min: 18881, max: 18899 },
  evolution: { min: 18901, max: 18919 },
  vite: { min: 19881, max: 19899 },
};

export class PortRegistry extends EventEmitter {
  private allocations = new Map<ServiceId, PortAllocation>();
  private host: string;

  constructor(host = '127.0.0.1') {
    super();
    this.host = host;
  }

  /**
   * Allocate a port for a service.
   * Scans the service's dedicated port range and returns the first available port.
   * If the service already has an allocation, returns the existing one.
   */
  async allocate(serviceId: ServiceId): Promise<PortAllocation> {
    // Check if already allocated
    const existing = this.allocations.get(serviceId);
    if (existing) {
      return existing;
    }

    const range = PORT_RANGES[serviceId];

    // Scan range for available port
    for (let port = range.min; port <= range.max; port++) {
      if (await this.isPortAvailable(port)) {
        const allocation: PortAllocation = {
          serviceId,
          port,
          allocatedAt: new Date(),
        };
        this.allocations.set(serviceId, allocation);
        this.emit('allocated', allocation);
        console.log(`[PortRegistry] Allocated ${serviceId} -> ${port}`);
        return allocation;
      }
    }

    throw new Error(
      `No available port for ${serviceId} in range ${range.min}-${range.max}`
    );
  }

  /**
   * Check if a port is available by attempting to bind to it.
   */
  private isPortAvailable(port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const server: Server = createServer();

      server.once('error', () => {
        resolve(false);
      });

      server.once('listening', () => {
        server.close(() => resolve(true));
      });

      server.listen(port, this.host);
    });
  }

  /**
   * Get the allocated port for a service.
   * Returns undefined if the service has no allocation.
   */
  getPort(serviceId: ServiceId): number | undefined {
    return this.allocations.get(serviceId)?.port;
  }

  /**
   * Get the full allocation details for a service.
   */
  getAllocation(serviceId: ServiceId): PortAllocation | undefined {
    return this.allocations.get(serviceId);
  }

  /**
   * Release the port allocation for a service.
   */
  release(serviceId: ServiceId): boolean {
    const allocation = this.allocations.get(serviceId);
    if (allocation) {
      this.allocations.delete(serviceId);
      this.emit('released', allocation);
      console.log(`[PortRegistry] Released ${serviceId} (was port ${allocation.port})`);
      return true;
    }
    return false;
  }

  /**
   * Release all port allocations.
   */
  releaseAll(): void {
    for (const serviceId of [...this.allocations.keys()]) {
      this.release(serviceId);
    }
  }

  /**
   * Get all allocations as a Map.
   */
  getAllAllocations(): Map<ServiceId, PortAllocation> {
    return new Map(this.allocations);
  }

  /**
   * Get port allocations as a simple JSON object.
   * Useful for status endpoints.
   */
  toJSON(): Record<string, number | undefined> {
    return {
      python: this.getPort('python'),
      evolution: this.getPort('evolution'),
      vite: this.getPort('vite'),
    };
  }

  /**
   * Get the port range configuration for a service.
   */
  static getRange(serviceId: ServiceId): PortRange {
    return { ...PORT_RANGES[serviceId] };
  }
}
