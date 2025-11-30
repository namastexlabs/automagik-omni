/**
 * Database URL construction utilities.
 * Frontend-only - constructs URLs from individual fields before sending to backend.
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
