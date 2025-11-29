/**
 * Database URL construction and parsing utilities.
 * Frontend-only - constructs/parses URLs before sending to backend.
 */

export interface PostgresUrlComponents {
  host: string;
  port: string;
  username: string;
  password: string;
  database: string;
}

export interface RedisUrlComponents {
  host: string;
  port: string;
  password: string;
  dbNumber: string;
  tls: boolean;
}

/**
 * Construct PostgreSQL connection URL from individual components.
 * Always uses 'postgresql://' prefix (Evolution API requirement).
 */
export function buildPostgresUrl(components: PostgresUrlComponents): string {
  const { host, port, username, password, database } = components;

  // Validation
  if (!host || !port || !username || !password || !database) {
    throw new Error('All PostgreSQL fields are required');
  }

  // URL encode password to handle special characters
  const encodedPassword = encodeURIComponent(password);

  return `postgresql://${username}:${encodedPassword}@${host}:${port}/${database}`;
}

/**
 * Parse PostgreSQL URL into individual components.
 * Returns null if URL is invalid.
 */
export function parsePostgresUrl(url: string): PostgresUrlComponents | null {
  try {
    if (!url.startsWith('postgresql://')) {
      return null;
    }

    const parsed = new URL(url);

    return {
      host: parsed.hostname || '',
      port: parsed.port || '5432',
      username: parsed.username || '',
      password: decodeURIComponent(parsed.password || ''),
      database: parsed.pathname.substring(1) || '', // Remove leading '/'
    };
  } catch (e) {
    return null;
  }
}

/**
 * Construct Redis connection URL from individual components.
 * Uses 'redis://' or 'rediss://' prefix based on TLS setting.
 */
export function buildRedisUrl(components: RedisUrlComponents): string {
  const { host, port, password, dbNumber, tls } = components;

  // Validation
  if (!host || !port || dbNumber === undefined || dbNumber === null) {
    throw new Error('Redis host, port, and database number are required');
  }

  const protocol = tls ? 'rediss' : 'redis';
  const encodedPassword = password ? encodeURIComponent(password) : '';
  const auth = encodedPassword ? `${encodedPassword}@` : '';

  return `${protocol}://${auth}${host}:${port}/${dbNumber}`;
}

/**
 * Parse Redis URL into individual components.
 * Returns null if URL is invalid.
 */
export function parseRedisUrl(url: string): RedisUrlComponents | null {
  try {
    if (!url.startsWith('redis://') && !url.startsWith('rediss://')) {
      return null;
    }

    const parsed = new URL(url);
    const tls = url.startsWith('rediss://');

    // Redis URL format: redis://[password@]host:port/db
    // URL.username contains the password in this case
    return {
      host: parsed.hostname || '',
      port: parsed.port || '6379',
      password: parsed.username ? decodeURIComponent(parsed.username) : '',
      dbNumber: parsed.pathname.substring(1) || '0', // Remove leading '/'
      tls,
    };
  } catch (e) {
    return null;
  }
}

/**
 * Validate port number (1-65535).
 */
export function validatePort(port: string): boolean {
  const num = parseInt(port, 10);
  return !isNaN(num) && num > 0 && num <= 65535;
}

/**
 * Validate Redis database number (0-15).
 */
export function validateDbNumber(dbNumber: string): boolean {
  const num = parseInt(dbNumber, 10);
  return !isNaN(num) && num >= 0 && num <= 15;
}
