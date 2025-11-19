const API_KEY_STORAGE_KEY = 'omni_api_key';
const API_BASE_URL = '/api/v1';

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

  // Contacts
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
    return apiRequest(`/omni/${instanceId}/contacts${query ? `?${query}` : ''}`);
  },

  // Chats
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
    return apiRequest(`/omni/${instanceId}/chats${query ? `?${query}` : ''}`);
  },

  // Health check
  async health(): Promise<any> {
    const response = await fetch('/health');
    return response.json();
  },
};
