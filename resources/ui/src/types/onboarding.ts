export interface DatabaseConfig {
  // PostgreSQL storage mode: 'embedded' (pgserve) or 'external' (existing PostgreSQL)
  storage_mode?: 'embedded' | 'external';

  // Embedded PostgreSQL options (pgserve)
  data_dir?: string; // Path for filesystem storage
  memory_mode?: boolean; // true = RAM only, false = disk storage
  replication_enabled?: boolean; // Enable replication (optional)
  replication_url?: string; // PostgreSQL URL for replication target

  // External PostgreSQL options
  external_database_url?: string; // PostgreSQL connection URL

  // Redis cache (optional)
  redis_enabled?: boolean;
  redis_url?: string;
  redis_prefix_key?: string;
  redis_ttl?: number;
  redis_save_instances?: boolean;
}

export interface SetupStatusResponse {
  requires_setup: boolean;
  // db_type removed - PostgreSQL-only now
}

export interface SetupCompleteResponse {
  success: boolean;
  message: string;
}
