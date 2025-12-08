export interface DatabaseConfig {
  // PostgreSQL storage options (embedded pgserve)
  data_dir?: string;        // Path for filesystem storage
  memory_mode?: boolean;    // true = RAM only, false = disk storage
  replication_enabled?: boolean;  // Enable replication (optional)

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
