export interface DatabaseConfig {
  db_type: 'sqlite' | 'postgresql';
  postgres_url?: string;
  redis_enabled: boolean;
  redis_url?: string;
  redis_prefix_key?: string;
  redis_ttl?: number;
  redis_save_instances?: boolean;
}

export interface SetupStatusResponse {
  requires_setup: boolean;
  db_type: string | null;
}

export interface SetupCompleteResponse {
  success: boolean;
  message: string;
}
