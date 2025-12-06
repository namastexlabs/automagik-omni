const API_KEY_STORAGE_KEY = 'omni_api_key';
const API_BASE_URL = '/api/v1';

// localStorage + PostgreSQL sync pattern for preferences
// Fast reads from localStorage (0ms), persistent writes to PostgreSQL (survives cache clear)

// Trace Analytics Types
export interface TraceAnalytics {
  total_messages: number;
  successful_messages: number;
  failed_messages: number;
  success_rate: number;
  avg_processing_time_ms: number | null;
  avg_agent_time_ms: number | null;
  message_types: Record<string, number>;
  error_stages: Record<string, number>;
  instances: Record<string, number>;
}

export interface Trace {
  trace_id: string;
  instance_name: string;
  whatsapp_message_id: string | null;
  sender_phone: string | null;
  sender_name: string | null;
  message_type: string | null;
  message_type_display: string | null;
  has_media: boolean;
  has_quoted_message: boolean;
  session_name: string | null;
  agent_session_id: string | null;
  status: 'received' | 'processing' | 'completed' | 'failed' | 'access_denied';
  error_message: string | null;
  error_stage: string | null;
  received_at: string | null;
  completed_at: string | null;
  agent_processing_time_ms: number | null;
  total_processing_time_ms: number | null;
  agent_response_success: boolean | null;
  evolution_success: boolean | null;
}

// Health Types
export interface ServerStats {
  memory: {
    total: number;       // GB
    used: number;        // GB
    free: number;        // GB
    usedPercent: number; // %
  };
  cpu: {
    cores: number;
    model: string;
    usagePercent: number; // %
  };
  disk: {
    total: number;       // GB
    used: number;        // GB
    free: number;        // GB
    usedPercent: number; // %
    mountPoint: string;
  };
  loadAverage: [number, number, number];
  uptime: number;        // seconds
  platform: string;
  hostname: string;
}

export interface HealthResponse {
  status: 'up' | 'down' | 'degraded';
  timestamp: string;
  server?: ServerStats;
  services: {
    gateway: ServiceHealth;
    python: ServiceHealth;
    evolution: ServiceHealth;
  };
}

export interface ServiceHealth {
  status: 'up' | 'down' | 'degraded';
  latency?: number;
  details?: Record<string, unknown>;
}

// Log Types
export type LogServiceName = 'api' | 'discord' | 'evolution' | 'gateway';

export interface LogEntry {
  timestamp: string;
  service: LogServiceName;
  level: 'debug' | 'info' | 'warn' | 'error' | 'unknown';
  message: string;
  raw: string;
}

export interface LogService {
  id: LogServiceName;
  name: string;
  color: string;
  available: boolean;
}

export interface Pm2Status {
  online: boolean;
  pm2_id?: number;
  name?: string;
  pid?: number;
  uptime?: number;
  restarts?: number;
  memory?: number;
  cpu?: number;
  message?: string;
}

export interface RestartResult {
  success: boolean;
  message: string;
}

// Database Configuration Types

/** @deprecated Use DatabaseConfigurationState instead */
export interface DatabaseConfigResponse {
  db_type: string;
  use_postgres: boolean;
  postgres_url_configured: boolean;
  table_prefix: string;
  pool_size: number;
  pool_max_overflow: number;
}

// New models for runtime vs saved state separation

/** Runtime configuration from frozen config object (set at startup from env vars) */
export interface RuntimeDatabaseConfig {
  db_type: string;
  use_postgres: boolean;
  postgres_url_masked: string | null;
  sqlite_path: string;
  table_prefix: string;
  pool_size: number;
  pool_max_overflow: number;
}

/** Saved configuration from omni_global_settings table */
export interface SavedDatabaseConfig {
  db_type: string | null;
  postgres_url_masked: string | null;
  postgres_host: string | null;
  postgres_port: string | null;
  postgres_database: string | null;
  redis_enabled: boolean | null;
  redis_url_masked: string | null;
  redis_prefix_key: string | null;
  redis_ttl: number | null;
  redis_save_instances: boolean | null;
  last_updated_at: string | null;
}

/**
 * Complete database configuration state showing both runtime and saved config.
 * Allows UI to show what's running vs what's saved, and display restart warnings.
 */
export interface DatabaseConfigurationState {
  // New structured response
  runtime: RuntimeDatabaseConfig;
  saved: SavedDatabaseConfig | null;
  requires_restart: boolean;
  restart_required_reason: string | null;
  is_configured: boolean;
  is_locked: boolean;

  // Backward compatibility fields (deprecated - use runtime.* instead)
  db_type: string;
  use_postgres: boolean;
  postgres_url_configured: boolean;
  table_prefix: string;
  pool_size: number;
  pool_max_overflow: number;
}

export interface TestResult {
  ok: boolean;
  message: string;
  latency_ms?: number;
}

export interface DatabaseTestResponse {
  success: boolean;
  tests: Record<string, TestResult>;
  total_latency_ms: number;
}

export interface DatabaseApplyResponse {
  success: boolean;
  message: string;
  requires_restart: boolean;
}

export interface DetectedPostgresFields {
  host: string;
  port: string;
  username: string;
  database: string;
}

export interface DetectedRedisFields {
  host: string;
  port: string;
  dbNumber: string;
  tls: boolean;
}

export interface EvolutionDetectResponse {
  found: boolean;
  source: string | null;
  message: string;
  postgresql: DetectedPostgresFields | null;
  redis: DetectedRedisFields | null;
}

export interface RedisTestResponse {
  success: boolean;
  tests: Record<string, TestResult>;
  total_latency_ms: number;
}

export interface RedisConfig {
  enabled: boolean;
  url?: string;
  prefixKey?: string;
  ttl?: number;
  saveInstances?: boolean;
}

// Global auth error handler
let authErrorHandler: (() => void) | null = null;

// localStorage + PostgreSQL sync helpers
async function syncToPostgreSQL(preferences: Record<string, string>): Promise<void> {
  // Get API key from localStorage (needed for auth)
  const apiKey = localStorage.getItem(API_KEY_STORAGE_KEY);
  if (!apiKey) {
    return; // Can't sync without API key
  }

  try {
    await fetch(`${API_BASE_URL}/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
      },
      body: JSON.stringify({ preferences }),
    });
  } catch (error) {
    console.error('[API] Failed to sync preferences to PostgreSQL:', error);
    // Non-fatal: localStorage write succeeded, sync can retry later
  }
}

async function restoreFromPostgreSQL(): Promise<void> {
  // Get API key from localStorage (needed for auth)
  const apiKey = localStorage.getItem(API_KEY_STORAGE_KEY);
  if (!apiKey) {
    return; // Can't restore without API key
  }

  try {
    const response = await fetch(`${API_BASE_URL}/sync`, {
      headers: { 'x-api-key': apiKey },
    });

    if (response.ok) {
      const data = await response.json();
      for (const [key, value] of Object.entries<string>(data.preferences)) {
        if (!localStorage.getItem(key)) {
          localStorage.setItem(key, value);
        }
      }
    }
  } catch (error) {
    console.error('[API] Failed to restore preferences from PostgreSQL:', error);
  }
}

// API Key management (localStorage + PostgreSQL sync pattern)
export async function getApiKey(): Promise<string | null> {
  return localStorage.getItem(API_KEY_STORAGE_KEY);
}

export async function setApiKey(key: string): Promise<void> {
  // Fast write to localStorage
  localStorage.setItem(API_KEY_STORAGE_KEY, key);

  // Async sync to PostgreSQL (non-blocking)
  syncToPostgreSQL({ [API_KEY_STORAGE_KEY]: key });
}

export async function removeApiKey(): Promise<void> {
  localStorage.removeItem(API_KEY_STORAGE_KEY);
}

export async function isAuthenticated(): Promise<boolean> {
  const key = await getApiKey();
  return !!key;
}

// Restore preferences from PostgreSQL on app startup (call once)
export async function restorePreferences(): Promise<void> {
  return restoreFromPostgreSQL();
}

// API client helper
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const apiKey = await getApiKey();

  if (!apiKey) {
    throw new Error('No API key found. Please login.');
  }

  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      await removeApiKey();

      if (authErrorHandler) {
        authErrorHandler();
      } else {
        // Default behavior: redirect to login
        window.location.replace('/login');
      }

      throw new Error('Authentication failed');
    }

    const error = await response.text();
    throw new Error(error || `Request failed with status ${response.status}`);
  }

  return response.json();
}

// API methods
export const api = {
  // Configuration
  setAuthErrorHandler(handler: () => void) {
    authErrorHandler = handler;
  },

  // Test authentication
  async testAuth(): Promise<boolean> {
    try {
      await apiRequest('/instances');
      return true;
    } catch (error) {
      console.error('[API] Auth test failed:', error);
      return false;
    }
  },

  // Instances API
  instances: {
    async list(params?: { limit?: number; include_status?: boolean; include_live_status?: boolean }): Promise<any[]> {
      const queryParams = new URLSearchParams();
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.include_status) queryParams.append('include_status', params.include_status.toString());
      if (params?.include_live_status) queryParams.append('include_live_status', 'true');

      const query = queryParams.toString();
      return apiRequest(`/instances${query ? `?${query}` : ''}`);
    },

    async get(name: string): Promise<any> {
      return apiRequest(`/instances/${name}`);
    },

    async create(data: any): Promise<any> {
      return apiRequest('/instances', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async update(name: string, data: any): Promise<any> {
      return apiRequest(`/instances/${name}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    async delete(name: string): Promise<void> {
      return apiRequest(`/instances/${name}`, {
        method: 'DELETE',
      });
    },

    async getQR(name: string): Promise<{ qr_code?: string; status?: string }> {
      return apiRequest(`/instances/${name}/qr`);
    },

    async getQRCode(name: string): Promise<{ qr_code?: string; status?: string }> {
      return apiRequest(`/instances/${name}/qr`);
    },

    async restart(name: string): Promise<any> {
      return apiRequest(`/instances/${name}/restart`, {
        method: 'POST',
      });
    },

    async getStatus(name: string): Promise<any> {
      return apiRequest(`/instances/${name}/status`);
    },

    async logout(name: string): Promise<any> {
      return apiRequest(`/instances/${name}/logout`, {
        method: 'POST',
      });
    },

    async discover(): Promise<{
      message: string;
      instances: Array<{
        name: string;
        whatsapp_instance: string;
        profile_name?: string;
        evolution_key: string;
        evolution_url: string;
      }>;
      total: number;
    }> {
      return apiRequest('/instances/discover', { method: 'POST' });
    },
  },

  // Contacts API
  contacts: {
    async list(instanceId: string, params?: {
      page?: number;
      page_size?: number;
      search_query?: string;
      status_filter?: string;
    }): Promise<any> {
      const queryParams = new URLSearchParams();
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params?.search_query) queryParams.append('search_query', params.search_query);
      if (params?.status_filter) queryParams.append('status_filter', params.status_filter);

      const query = queryParams.toString();
      return apiRequest(`/instances/${instanceId}/contacts${query ? `?${query}` : ''}`);
    },
  },

  // Chats API
  chats: {
    async list(instanceId: string, params?: {
      page?: number;
      page_size?: number;
      search_query?: string;
      chat_type?: string;
      include_archived?: boolean;
    }): Promise<any> {
      const queryParams = new URLSearchParams();
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.page_size) queryParams.append('page_size', params.page_size.toString());
      if (params?.search_query) queryParams.append('search_query', params.search_query);
      if (params?.chat_type) queryParams.append('chat_type', params.chat_type);
      if (params?.include_archived !== undefined) {
        queryParams.append('include_archived', params.include_archived.toString());
      }

      const query = queryParams.toString();
      return apiRequest(`/instances/${instanceId}/chats${query ? `?${query}` : ''}`);
    },
  },

  // Legacy flat methods for backward compatibility
  async getInstances(): Promise<any[]> {
    return apiRequest('/instances');
  },

  async getInstance(instanceId: string): Promise<any> {
    return apiRequest(`/instances/${instanceId}`);
  },

  async createInstance(data: any): Promise<any> {
    return apiRequest('/instances', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateInstance(instanceId: string, data: any): Promise<any> {
    return apiRequest(`/instances/${instanceId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteInstance(instanceId: string): Promise<void> {
    return apiRequest(`/instances/${instanceId}`, {
      method: 'DELETE',
    });
  },

  async getQRCode(instanceId: string): Promise<{ qr_code?: string; status?: string }> {
    return apiRequest(`/instances/${instanceId}/qr`);
  },

  async restartInstance(instanceId: string): Promise<any> {
    return apiRequest(`/instances/${instanceId}/restart`, {
      method: 'POST',
    });
  },

  async getInstanceStatus(instanceId: string): Promise<any> {
    return apiRequest(`/instances/${instanceId}/status`);
  },

  async getContacts(instanceId: string, params?: {
    page?: number;
    limit?: number;
    search?: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.search) queryParams.append('search', params.search);

    const query = queryParams.toString();
    return apiRequest(`/instances/${instanceId}/contacts${query ? `?${query}` : ''}`);
  },

  async getChats(instanceId: string, params?: {
    page?: number;
    limit?: number;
    search?: string;
  }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.search) queryParams.append('search', params.search);

    const query = queryParams.toString();
    return apiRequest(`/instances/${instanceId}/chats${query ? `?${query}` : ''}`);
  },

  // Health check
  async health(): Promise<any> {
    try {
      const response = await fetch('/health');
      if (!response.ok) {
        return { status: 'down' };
      }
      return response.json();
    } catch (error) {
      console.error('[API] Health check failed:', error);
      return { status: 'down' };
    }
  },

  // Trace Analytics API
  traces: {
    async getAnalytics(params?: {
      start_date?: string;
      end_date?: string;
      instance_name?: string;
      all_time?: boolean;
    }): Promise<TraceAnalytics> {
      const queryParams = new URLSearchParams();
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);
      if (params?.instance_name) queryParams.append('instance_name', params.instance_name);
      if (params?.all_time) queryParams.append('all_time', 'true');

      const query = queryParams.toString();
      return apiRequest(`/traces/analytics/summary${query ? `?${query}` : ''}`);
    },

    async list(params?: {
      limit?: number;
      offset?: number;
      start_date?: string;
      end_date?: string;
      instance_name?: string;
      trace_status?: string;
      message_type?: string;
      all_time?: boolean;
    }): Promise<Trace[]> {
      const queryParams = new URLSearchParams();
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.offset) queryParams.append('offset', params.offset.toString());
      if (params?.start_date) queryParams.append('start_date', params.start_date);
      if (params?.end_date) queryParams.append('end_date', params.end_date);
      if (params?.instance_name) queryParams.append('instance_name', params.instance_name);
      if (params?.trace_status) queryParams.append('trace_status', params.trace_status);
      if (params?.message_type) queryParams.append('message_type', params.message_type);
      if (params?.all_time) queryParams.append('all_time', 'true');

      const query = queryParams.toString();
      return apiRequest(`/traces${query ? `?${query}` : ''}`);
    },

    async get(traceId: string): Promise<Trace> {
      return apiRequest(`/traces/${traceId}`);
    },
  },

  // Logs API (direct to gateway, no auth needed)
  logs: {
    async getServices(): Promise<LogService[]> {
      try {
        const response = await fetch('/api/logs/services');
        if (!response.ok) throw new Error('Failed to fetch log services');
        return response.json();
      } catch (error) {
        console.error('[API] Failed to get log services:', error);
        return [];
      }
    },

    async getRecent(params?: { services?: LogServiceName[]; limit?: number }): Promise<LogEntry[]> {
      try {
        const queryParams = new URLSearchParams();
        if (params?.services?.length) queryParams.append('services', params.services.join(','));
        if (params?.limit) queryParams.append('limit', params.limit.toString());

        const query = queryParams.toString();
        const response = await fetch(`/api/logs/recent${query ? `?${query}` : ''}`);
        if (!response.ok) throw new Error('Failed to fetch recent logs');
        return response.json();
      } catch (error) {
        console.error('[API] Failed to get recent logs:', error);
        return [];
      }
    },

    createStream(services?: LogServiceName[]): EventSource {
      const queryParams = new URLSearchParams();
      if (services?.length) queryParams.append('services', services.join(','));

      const query = queryParams.toString();
      return new EventSource(`/api/logs/stream${query ? `?${query}` : ''}`);
    },

    async restart(service: LogServiceName): Promise<RestartResult> {
      try {
        const response = await fetch(`/api/logs/restart/${service}`, {
          method: 'POST',
        });
        return response.json();
      } catch (error) {
        return {
          success: false,
          message: error instanceof Error ? error.message : 'Failed to restart service',
        };
      }
    },

    async getStatus(service: LogServiceName): Promise<Pm2Status> {
      try {
        const response = await fetch(`/api/logs/status/${service}`);
        if (!response.ok) throw new Error('Failed to get status');
        return response.json();
      } catch (error) {
        return { online: false, message: 'Failed to get status' };
      }
    },

    async getAllStatuses(): Promise<Record<LogServiceName, Pm2Status>> {
      try {
        const response = await fetch('/api/logs/status');
        if (!response.ok) throw new Error('Failed to get statuses');
        return response.json();
      } catch (error) {
        return {
          api: { online: false },
          discord: { online: false },
          evolution: { online: false },
          gateway: { online: false },
        };
      }
    },
  },

  // WhatsApp Web API (direct access via gateway, uses Evolution protocol)
  whatsappWeb: {
    // Settings
    async getSettings(instanceName: string): Promise<any> {
      return evolutionRequest(`/settings/find/${instanceName}`);
    },

    async setSettings(instanceName: string, settings: any): Promise<any> {
      return evolutionRequest(`/settings/set/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(settings),
      });
    },

    // Connection
    async getConnectionState(instanceName: string): Promise<any> {
      return evolutionRequest(`/instance/connectionState/${instanceName}`, {}, instanceName);
    },

    async restart(instanceName: string): Promise<any> {
      return evolutionRequest(`/instance/restart/${instanceName}`, {
        method: 'POST',
      }, instanceName);
    },

    async logout(instanceName: string): Promise<any> {
      return evolutionRequest(`/instance/logout/${instanceName}`, {
        method: 'DELETE',
      }, instanceName);
    },

    async connect(instanceName: string): Promise<any> {
      return evolutionRequest(`/instance/connect/${instanceName}`, {}, instanceName);
    },

    // Webhook
    async getWebhook(instanceName: string): Promise<any> {
      return evolutionRequest(`/webhook/find/${instanceName}`);
    },

    async setWebhook(instanceName: string, config: any): Promise<any> {
      return evolutionRequest(`/webhook/set/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(config),
      });
    },

    // WebSocket
    async getWebSocket(instanceName: string): Promise<any> {
      return evolutionRequest(`/websocket/find/${instanceName}`);
    },

    async setWebSocket(instanceName: string, config: any): Promise<any> {
      return evolutionRequest(`/websocket/set/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(config),
      });
    },

    // RabbitMQ
    async getRabbitMQ(instanceName: string): Promise<any> {
      return evolutionRequest(`/rabbitmq/find/${instanceName}`);
    },

    async setRabbitMQ(instanceName: string, config: any): Promise<any> {
      return evolutionRequest(`/rabbitmq/set/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(config),
      });
    },

    // Chats
    async findChats(instanceName: string, params?: any): Promise<any> {
      return evolutionRequest(`/chat/findChats/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(params || {}),
      }, instanceName);
    },

    async findMessages(instanceName: string, params: { where: { key: { remoteJid: string } }; limit?: number }): Promise<any> {
      return evolutionRequest(`/chat/findMessages/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(params),
      }, instanceName);
    },

    async findContacts(instanceName: string, params?: any): Promise<any> {
      return evolutionRequest(`/chat/findContacts/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(params || {}),
      }, instanceName);
    },

    // Groups
    async fetchAllGroups(instanceName: string): Promise<any[]> {
      return evolutionRequest(`/group/fetchAllGroups/${instanceName}?getParticipants=false`, {}, instanceName);
    },

    // Messages
    async sendText(instanceName: string, data: { number: string; text: string }): Promise<any> {
      return evolutionRequest(`/message/sendText/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async sendMedia(instanceName: string, data: any): Promise<any> {
      return evolutionRequest(`/message/sendMedia/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async sendWhatsAppAudio(instanceName: string, data: { number: string; audio: string; encoding?: boolean }): Promise<any> {
      return evolutionRequest(`/message/sendWhatsAppAudio/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async markAsRead(instanceName: string, data: { readMessages: Array<{ remoteJid: string; id: string }> }): Promise<any> {
      return evolutionRequest(`/chat/markMessageAsRead/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    // Presence
    async sendPresence(instanceName: string, data: { number: string; presence: string }): Promise<any> {
      return evolutionRequest(`/chat/sendPresence/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    // Media
    async getBase64FromMediaMessage(instanceName: string, data: { message: { key: { id: string; remoteJid: string } }; convertToMp4?: boolean }): Promise<{
      mediaType: string;
      fileName: string;
      caption?: string;
      mimetype: string;
      base64: string;
    }> {
      return evolutionRequest(`/chat/getBase64FromMediaMessage/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },
  },

  // Global Settings API
  settings: {
    async list(category?: string): Promise<any[]> {
      const queryParams = category ? `?category=${encodeURIComponent(category)}` : '';
      return apiRequest(`/settings${queryParams}`);
    },

    async get(key: string): Promise<any> {
      return apiRequest(`/settings/${encodeURIComponent(key)}`);
    },

    async create(data: any): Promise<any> {
      return apiRequest('/settings', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async update(key: string, data: any): Promise<any> {
      return apiRequest(`/settings/${encodeURIComponent(key)}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
    },

    async delete(key: string): Promise<void> {
      return apiRequest(`/settings/${encodeURIComponent(key)}`, {
        method: 'DELETE',
      });
    },

    async getHistory(key: string, limit: number = 50): Promise<any[]> {
      return apiRequest(`/settings/${encodeURIComponent(key)}/history?limit=${limit}`);
    },
  },

  // Database Configuration API
  database: {
    async getConfig(): Promise<DatabaseConfigurationState> {
      return apiRequest('/database/config');
    },

    async testConnection(url: string): Promise<DatabaseTestResponse> {
      return apiRequest('/database/test', {
        method: 'POST',
        body: JSON.stringify({ url }),
      });
    },

    async testRedisConnection(url: string): Promise<RedisTestResponse> {
      return apiRequest('/database/redis/test', {
        method: 'POST',
        body: JSON.stringify({ url }),
      });
    },

    async apply(
      dbType: string,
      postgresUrl?: string,
      redisConfig?: RedisConfig
    ): Promise<DatabaseApplyResponse> {
      return apiRequest('/database/apply', {
        method: 'POST',
        body: JSON.stringify({
          db_type: dbType,
          postgres_url: postgresUrl,
          redis_enabled: redisConfig?.enabled ?? false,
          redis_url: redisConfig?.url,
          redis_prefix_key: redisConfig?.prefixKey ?? 'evolution',
          redis_ttl: redisConfig?.ttl ?? 604800,
          redis_save_instances: redisConfig?.saveInstances ?? true,
        }),
      });
    },

    async detectEvolution(): Promise<EvolutionDetectResponse> {
      return apiRequest('/database/detect-evolution');
    },
  },

  // Setup API (unauthenticated endpoints for onboarding)
  setup: {
    async status(): Promise<{ requires_setup: boolean; db_type: string | null }> {
      const response = await fetch(`${API_BASE_URL}/setup/status`);
      if (!response.ok) {
        throw new Error('Failed to check setup status');
      }
      return response.json();
    },

    async initialize(config: {
      db_type: 'sqlite' | 'postgresql';
      postgres_url?: string;
      redis_enabled: boolean;
      redis_url?: string;
      redis_prefix_key?: string;
      redis_ttl?: number;
      redis_save_instances?: boolean;
    }): Promise<{ success: boolean; message: string }> {
      const response = await fetch(`${API_BASE_URL}/setup/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Setup initialization failed' }));
        throw new Error(error.detail || 'Setup initialization failed');
      }
      return response.json();
    },

    async complete(): Promise<{ success: boolean; message: string }> {
      const response = await fetch(`${API_BASE_URL}/setup/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to complete setup' }));
        throw new Error(error.detail || 'Failed to complete setup');
      }
      return response.json();
    },

    // Database testing methods for onboarding (no auth required)
    async testPostgresConnection(url: string): Promise<DatabaseTestResponse> {
      const response = await fetch(`${API_BASE_URL}/database/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to test PostgreSQL connection');
      }
      return response.json();
    },

    async testRedisConnection(url: string): Promise<RedisTestResponse> {
      const response = await fetch(`${API_BASE_URL}/database/redis/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to test Redis connection');
      }
      return response.json();
    },

    async detectEvolution(): Promise<EvolutionDetectResponse> {
      const response = await fetch(`${API_BASE_URL}/database/detect-evolution`);
      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Failed to detect Evolution configuration');
      }
      return response.json();
    },

    async getApiKey(): Promise<{ api_key: string; message: string }> {
      const response = await fetch(`${API_BASE_URL}/setup/api-key`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to get API key' }));
        throw new Error(error.detail || 'Failed to get API key');
      }
      return response.json();
    },

    // Channel configuration methods
    async getChannelsStatus(): Promise<{
      whatsapp: { enabled: boolean; configured: boolean; status: string; message?: string };
      discord: { enabled: boolean; configured: boolean; status: string; message?: string };
    }> {
      const response = await fetch(`${API_BASE_URL}/setup/channels/status`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to get channels status' }));
        throw new Error(error.detail || 'Failed to get channels status');
      }
      return response.json();
    },

    async configureChannels(config: {
      whatsapp_enabled: boolean;
      discord_enabled: boolean;
      // WhatsApp instance name only - everything else is automatic
      whatsapp_instance_name?: string;
    }): Promise<{
      success: boolean;
      message: string;
      whatsapp_status: string;
      discord_status: string;
      // WhatsApp instance creation results
      whatsapp_qr_code?: string;
      whatsapp_instance_name?: string;
    }> {
      const response = await fetch(`${API_BASE_URL}/setup/channels/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to configure channels' }));
        throw new Error(error.detail || 'Failed to configure channels');
      }
      return response.json();
    },

    async validateDiscordToken(bot_token: string, client_id: string): Promise<{
      valid: boolean;
      bot_name?: string;
      bot_id?: string;
      message: string;
    }> {
      const response = await fetch(`${API_BASE_URL}/setup/channels/validate-discord`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_token, client_id }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to validate Discord token' }));
        throw new Error(error.detail || 'Failed to validate Discord token');
      }
      return response.json();
    },
  },

  // Recovery API (localhost-only, no auth required)
  recovery: {
    async getApiKey(): Promise<{ api_key: string; message: string }> {
      const response = await fetch(`${API_BASE_URL}/recovery/api-key`);
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to recover API key' }));
        throw new Error(error.detail || 'Failed to recover API key');
      }
      return response.json();
    },
  },

  // Gateway Channel Management API (no auth required for channel control)
  gateway: {
    async getChannels(): Promise<{
      lazyMode: boolean;
      channels: Array<{
        name: string;
        enabled: boolean;
        running: boolean;
      }>;
    }> {
      const response = await fetch('/gateway/channels');
      if (!response.ok) {
        throw new Error('Failed to get gateway channels');
      }
      return response.json();
    },

    async startChannel(channel: string): Promise<{
      status: 'started' | 'already_running';
      channel: string;
    }> {
      const response = await fetch(`/gateway/channels/${channel}/start`, {
        method: 'POST',
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Failed to start channel' }));
        throw new Error(error.error || 'Failed to start channel');
      }
      return response.json();
    },

    async getStatus(): Promise<{
      gateway: {
        port: number;
        mode: string;
        proxyOnly: boolean;
        lazyChannels: boolean;
        uptime: number;
      };
      ports: Record<string, number>;
      processes: Record<string, {
        port: number;
        healthy: boolean;
        pid?: number;
      }>;
    }> {
      const response = await fetch('/gateway/status');
      if (!response.ok) {
        throw new Error('Failed to get gateway status');
      }
      return response.json();
    },

    // Poll until a channel is running and healthy
    async waitForChannel(channel: string, timeoutMs: number = 60000): Promise<boolean> {
      const startTime = Date.now();
      while (Date.now() - startTime < timeoutMs) {
        try {
          const status = await this.getStatus();
          const proc = status.processes[channel];
          if (proc && proc.healthy) {
            return true;
          }
        } catch (e) {
          // Keep polling
        }
        await new Promise(r => setTimeout(r, 1000));
      }
      return false;
    },

    // Check if Discord dependencies are installed
    async checkDiscordInstalled(): Promise<{ installed: boolean; version: string | null }> {
      const response = await fetch('/api/gateway/discord-status');
      if (!response.ok) {
        return { installed: false, version: null };
      }
      return response.json();
    },

    // Install Discord dependencies - returns the SSE endpoint URL
    // Note: The actual installation streams via SSE at /api/gateway/install-discord (GET)
    // Use EventSource to connect to this endpoint for live logs
    getInstallDiscordUrl(): string {
      return '/api/gateway/install-discord';
    },
  },

  // Backward compatibility alias - use api.whatsappWeb for new code
  get evolution() {
    return this.whatsappWeb;
  },
};

// WhatsApp Web API helper (uses Evolution protocol under the hood)
const EVOLUTION_BASE_URL = '/evolution';

// DEPRECATED: Instance keys are no longer used (Option A: Bootstrap Key Only)
// Kept for backwards compatibility only
let instanceKeys: Map<string, string> = new Map();

export function setInstanceKey(instanceName: string, evolutionKey: string) {
  // No-op: Instance keys are deprecated, always use bootstrap key
  instanceKeys.set(instanceName, evolutionKey);
}

async function evolutionRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  instanceName?: string
): Promise<T> {
  const apiKey = await getApiKey();

  if (!apiKey) {
    throw new Error('No API key found. Please login.');
  }

  const url = `${EVOLUTION_BASE_URL}${endpoint}`;

  // Use unified API key (same key for Omni and Evolution)
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'apikey': apiKey,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `Evolution API request failed with status ${response.status}`);
  }

  return response.json();
}
