/**
 * Trusted Origins Validator
 *
 * Validates if requests come from trusted sources:
 * 1. Localhost IPs (127.0.0.1, ::1, ::ffff:127.0.0.1)
 * 2. Configured domain (omni_public_url matches Host header)
 */

interface TrustedOriginsConfig {
  publicUrl: string | null;
  lastFetched: number;
  ttlMs: number;
}

const LOCALHOST_IPS = ['127.0.0.1', '::1', '::ffff:127.0.0.1'];

export class TrustedOriginsValidator {
  private config: TrustedOriginsConfig = {
    publicUrl: null,
    lastFetched: 0,
    ttlMs: 60000, // 1 minute cache
  };

  private pythonPort: number | undefined;
  private fetchPromise: Promise<void> | null = null;

  constructor(pythonPort?: number) {
    this.pythonPort = pythonPort;
  }

  /**
   * Set Python port (called after port allocation)
   */
  setPythonPort(port: number): void {
    this.pythonPort = port;
  }

  /**
   * Force refresh the cached public URL
   */
  async invalidateCache(): Promise<void> {
    this.config.lastFetched = 0;
    await this.fetchPublicUrl();
  }

  /**
   * Fetch public URL from Python API with deduplication
   */
  private async fetchPublicUrl(): Promise<void> {
    if (!this.pythonPort) return;

    // Avoid duplicate fetches
    if (this.fetchPromise) {
      await this.fetchPromise;
      return;
    }

    this.fetchPromise = (async () => {
      try {
        const response = await fetch(`http://127.0.0.1:${this.pythonPort}/api/v1/setup/public-url`, {
          signal: AbortSignal.timeout(5000),
        });

        if (response.ok) {
          const data = (await response.json()) as { url?: string };
          this.config.publicUrl = data.url || null;
          this.config.lastFetched = Date.now();
          console.log(`[TrustedOrigins] Cached public URL: ${this.config.publicUrl || '(none)'}`);
        }
      } catch (err) {
        console.warn(`[TrustedOrigins] Failed to fetch public URL: ${err}`);
      } finally {
        this.fetchPromise = null;
      }
    })();

    await this.fetchPromise;
  }

  /**
   * Check if cache needs refresh
   */
  private needsRefresh(): boolean {
    return Date.now() - this.config.lastFetched > this.config.ttlMs;
  }

  /**
   * Extract domain from URL (removes protocol and port)
   */
  private extractDomain(url: string): string | null {
    if (!url) return null;
    try {
      // Add protocol if missing
      const fullUrl = url.startsWith('http') ? url : `http://${url}`;
      const parsed = new URL(fullUrl);
      return parsed.hostname.toLowerCase();
    } catch {
      return null;
    }
  }

  /**
   * Extract domain from Host header (handles port)
   */
  private extractHostDomain(host: string): string {
    // Remove port if present (e.g., "example.com:8882" -> "example.com")
    return host.split(':')[0].toLowerCase();
  }

  /**
   * Check if request is from a trusted origin
   *
   * Trusted means:
   * 1. Request IP is localhost (127.0.0.1, ::1, ::ffff:127.0.0.1)
   * 2. OR Host header matches configured omni_public_url domain
   */
  async isTrustedRequest(clientIp: string, hostHeader: string | undefined): Promise<boolean> {
    // Always trust localhost IPs
    if (LOCALHOST_IPS.includes(clientIp)) {
      return true;
    }

    // No host header = not trusted
    if (!hostHeader) {
      return false;
    }

    // Refresh cache if stale
    if (this.needsRefresh()) {
      await this.fetchPublicUrl();
    }

    // No public URL configured = only localhost allowed
    if (!this.config.publicUrl) {
      return false;
    }

    // Compare domains (case-insensitive, without port)
    const configuredDomain = this.extractDomain(this.config.publicUrl);
    const requestDomain = this.extractHostDomain(hostHeader);

    if (!configuredDomain) {
      return false;
    }

    const trusted = requestDomain === configuredDomain;

    if (trusted) {
      console.log(`[TrustedOrigins] Request trusted via domain match: ${requestDomain}`);
    }

    return trusted;
  }

  /**
   * Get current cached public URL (for debugging)
   */
  getCachedPublicUrl(): string | null {
    return this.config.publicUrl;
  }
}
