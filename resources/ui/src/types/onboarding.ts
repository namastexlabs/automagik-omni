export interface DatabaseConfig {
  // NEW: Flag to determine if embedded pgserve should be used
  use_pgserve?: boolean;

  // Pgserve options (only when use_pgserve=true)
  memory_mode?: boolean;
  data_dir?: string;

  // External PostgreSQL (only when use_pgserve=false)
  postgres_url?: string;

  // Redis (available for ALL modes)
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
