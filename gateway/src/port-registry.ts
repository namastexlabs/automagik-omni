/**
 * Port Registry for Automagik Omni Gateway
 * Centralized port allocation and tracking for internal services
 *
 * Each service gets a dedicated non-overlapping port range:
 * - PostgreSQL: 8432-8449 (embedded pgserve)
 * - Python API: 18881-18899
 * - Evolution API: 18901-18919
 * - Vite Dev: 19881-19899
 *
 * All services bind to 127.0.0.1 (internal only).
 * Gateway remains the only externally accessible port (configurable via OMNI_PORT).
 */

import { EventEmitter } from 'node:events';
import { createServer, type Server } from 'node:net';

export type ServiceId = 'python' | 'evolution' | 'vite' | 'postgres';

export interface PortAllocation {
  serviceId: ServiceId;
  port: number;
  allocatedAt: Date;
  reservationSocket?: Server; // Keep socket bound until subprocess confirms
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
  postgres: { min: 8432, max: 8449 },
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
   * Scans the service's dedicated port range with randomized starting point
   * to distribute ports across the range (better for multiple instances).
   * If the service already has an allocation, returns the existing one.
   */
  async allocate(serviceId: ServiceId): Promise<PortAllocation> {
    // Check if already allocated and validate it's still in use
    const existing = this.allocations.get(serviceId);
    if (existing) {
      const isValid = await this.validateAllocation(serviceId);
      if (isValid) {
        console.log(`[PortRegistry] Reusing validated allocation for ${serviceId} (port ${existing.port})`);
        return existing;
      }
      // Stale allocation was cleared by validateAllocation, continue to allocate new port
      console.log(`[PortRegistry] Stale allocation cleared, allocating new port for ${serviceId}`);
    }

    const range = PORT_RANGES[serviceId];
    const rangeSize = range.max - range.min + 1;

    // Start at random offset for better distribution across range
    const startOffset = Math.floor(Math.random() * rangeSize);

    // Scan range starting from random offset (wraps around)
    for (let i = 0; i < rangeSize; i++) {
      const port = range.min + ((startOffset + i) % rangeSize);
      const socket = await this.tryReservePort(port);
      if (socket) {
        // Release socket IMMEDIATELY after confirming port is free (FIX: prevents subprocess binding conflict)
        socket.close();

        const allocation: PortAllocation = {
          serviceId,
          port,
          allocatedAt: new Date(),
          // No reservationSocket - already released
        };
        this.allocations.set(serviceId, allocation);
        this.emit('allocated', allocation);
        console.log(`[PortRegistry] Allocated ${serviceId} -> ${port} (ready for subprocess)`);

        return allocation;
      }
    }

    throw new Error(`No available port for ${serviceId} in range ${range.min}-${range.max}`);
  }

  /**
   * Try to reserve a port by binding a socket (kept open for atomic handoff).
   * Returns the bound socket on success, null if port is unavailable.
   */
  private tryReservePort(port: number): Promise<Server | null> {
    return new Promise((resolve) => {
      const server: Server = createServer();

      server.once('error', () => {
        resolve(null);
      });

      server.once('listening', () => {
        // Keep socket open! Don't close it yet
        // This prevents TOCTOU race condition
        resolve(server);
      });

      server.listen(port, this.host);
    });
  }

  /**
   * Confirm allocation and release the reservation socket.
   * Call this after the subprocess successfully binds to the port.
   */
  confirmAllocation(serviceId: ServiceId): void {
    const allocation = this.allocations.get(serviceId);
    if (allocation?.reservationSocket) {
      allocation.reservationSocket.close();
      allocation.reservationSocket = undefined;
      console.log(`[PortRegistry] Released reservation socket for ${serviceId} (port ${allocation.port})`);
    }
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
   * Validate that an existing allocation's port is still in use.
   * If port is free (zombie process), clears the stale allocation.
   * Returns true if allocation is valid, false if it was stale.
   */
  async validateAllocation(serviceId: ServiceId): Promise<boolean> {
    const allocation = this.allocations.get(serviceId);
    if (!allocation) {
      return false; // No allocation exists
    }

    // Try to bind to the port - if successful, it's free (stale allocation)
    const socket = await this.tryReservePort(allocation.port);
    if (socket) {
      // Port is free! This is a stale allocation (zombie process)
      socket.close();
      this.allocations.delete(serviceId);
      console.warn(`[PortRegistry] Cleared stale allocation for ${serviceId} (port ${allocation.port} was free)`);
      return false;
    }

    // Port is in use - allocation is valid
    return true;
  }

  /**
   * Release the port allocation for a service.
   */
  release(serviceId: ServiceId): boolean {
    const allocation = this.allocations.get(serviceId);
    if (allocation) {
      // Close reservation socket if still held
      if (allocation.reservationSocket) {
        allocation.reservationSocket.close();
      }
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
      postgres: this.getPort('postgres'),
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
