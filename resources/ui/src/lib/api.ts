const API_KEY_STORAGE_KEY = 'omni_api_key';
const API_BASE_URL = '/api/v1';

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
export interface HealthResponse {
  status: 'up' | 'down' | 'degraded';
  timestamp: string;
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

// API Key management
export function getApiKey(): string | null {
  return localStorage.getItem(API_KEY_STORAGE_KEY);
}

export function setApiKey(key: string): void {
  localStorage.setItem(API_KEY_STORAGE_KEY, key);
}

export function removeApiKey(): void {
  localStorage.removeItem(API_KEY_STORAGE_KEY);
}

export function isAuthenticated(): boolean {
  return !!getApiKey();
}

// API client helper
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const apiKey = getApiKey();

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
      removeApiKey();
      window.location.href = '/login';
      throw new Error('Authentication failed');
    }

    const error = await response.text();
    throw new Error(error || `Request failed with status ${response.status}`);
  }

  return response.json();
}

// API methods
export const api = {
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
    async list(params?: { limit?: number; include_status?: boolean }): Promise<any[]> {
      const queryParams = new URLSearchParams();
      if (params?.limit) queryParams.append('limit', params.limit.toString());
      if (params?.include_status) queryParams.append('include_status', params.include_status.toString());

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

  // Evolution API (direct access via gateway)
  evolution: {
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
      return evolutionRequest(`/instance/connectionState/${instanceName}`);
    },

    async restart(instanceName: string): Promise<any> {
      return evolutionRequest(`/instance/restart/${instanceName}`, {
        method: 'POST',
      });
    },

    async logout(instanceName: string): Promise<any> {
      return evolutionRequest(`/instance/logout/${instanceName}`, {
        method: 'DELETE',
      });
    },

    async connect(instanceName: string): Promise<any> {
      return evolutionRequest(`/instance/connect/${instanceName}`);
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
      });
    },

    async findMessages(instanceName: string, params: { where: { key: { remoteJid: string } }; limit?: number }): Promise<any> {
      return evolutionRequest(`/chat/findMessages/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(params),
      });
    },

    async findContacts(instanceName: string, params?: any): Promise<any> {
      return evolutionRequest(`/chat/findContacts/${instanceName}`, {
        method: 'POST',
        body: JSON.stringify(params || {}),
      });
    },

    // Groups
    async fetchAllGroups(instanceName: string): Promise<any[]> {
      return evolutionRequest(`/group/fetchAllGroups/${instanceName}?getParticipants=false`);
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
};

// Evolution API helper (direct to Evolution via gateway)
const EVOLUTION_BASE_URL = '/evolution';

async function evolutionRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const apiKey = getApiKey();

  if (!apiKey) {
    throw new Error('No API key found. Please login.');
  }

  const url = `${EVOLUTION_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'apikey': localStorage.getItem('evolution_api_key') || '429683C4C977415CAAFCCE10F7D57E11',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `Evolution API request failed with status ${response.status}`);
  }

  return response.json();
}
