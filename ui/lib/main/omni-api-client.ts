/**
 * Omni API Client
 * HTTP client for communicating with Automagik Omni FastAPI backend
 */

export interface OmniConfig {
  baseUrl: string
  apiKey: string
  timeout?: number
}

export interface Instance {
  id: string
  name: string
  channel_type: string
  is_default: boolean
  created_at: string
  updated_at: string

  // Channel-specific fields
  evolution_url?: string
  whatsapp_instance?: string
  discord_bot_token?: string
  discord_guild_id?: string

  // Agent configuration
  agent_api_url: string
  agent_api_key: string
  default_agent?: string
  agent_timeout: number

  // Connection status
  status?: 'connected' | 'disconnected' | 'connecting' | 'error'
  qr_code?: string
}

export interface Contact {
  id: string
  name: string
  phone_number?: string
  profile_picture_url?: string
  status?: string
  channel_type: string
}

export interface Chat {
  id: string
  name: string
  chat_type: 'direct' | 'group' | 'channel' | 'thread'
  unread_count: number
  last_message?: string
  last_message_timestamp?: string
  archived: boolean
  channel_type: string
}

export interface Message {
  id: string
  from: string
  to: string
  content: string
  timestamp: string
  message_type: 'text' | 'media' | 'audio' | 'sticker' | 'contact' | 'reaction'
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed'
}

export interface Trace {
  id: string
  instance_name: string
  phone_number: string
  message_type: string
  status: 'received' | 'processing' | 'completed' | 'failed'
  created_at: string
  payload?: any
  error?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total_count: number
  page: number
  page_size: number
  has_more: boolean
}

/**
 * Omni API Client for backend communication
 */
export class OmniApiClient {
  private config: OmniConfig

  constructor(config: OmniConfig) {
    this.config = {
      timeout: 30000,
      ...config,
    }
  }

  /**
   * Make HTTP request to API
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`
    const headers = {
      'Content-Type': 'application/json',
      'x-api-key': this.config.apiKey,
      ...options.headers,
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout)

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      clearTimeout(timeoutId)
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout')
      }
      throw error
    }
  }

  // ============================================================================
  // INSTANCES
  // ============================================================================

  /**
   * Get all instances
   */
  async getInstances(): Promise<Instance[]> {
    return this.request<Instance[]>('/api/v1/instances')
  }

  /**
   * Get instance by name
   */
  async getInstance(name: string): Promise<Instance> {
    return this.request<Instance>(`/api/v1/instances/${name}`)
  }

  /**
   * Create new instance
   */
  async createInstance(data: Partial<Instance>): Promise<Instance> {
    return this.request<Instance>('/api/v1/instances', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  /**
   * Update instance
   */
  async updateInstance(name: string, data: Partial<Instance>): Promise<Instance> {
    return this.request<Instance>(`/api/v1/instances/${name}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  /**
   * Delete instance
   */
  async deleteInstance(name: string): Promise<void> {
    return this.request<void>(`/api/v1/instances/${name}`, {
      method: 'DELETE',
    })
  }

  /**
   * Get instance QR code (WhatsApp)
   */
  async getInstanceQR(name: string): Promise<{ qr_code: string; base64: string }> {
    return this.request(`/api/v1/instances/${name}/qr`)
  }

  /**
   * Get instance connection status
   */
  async getInstanceStatus(name: string): Promise<{ status: string; connected: boolean }> {
    return this.request(`/api/v1/instances/${name}/status`)
  }

  /**
   * Connect instance
   */
  async connectInstance(name: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/api/v1/instances/${name}/connect`, {
      method: 'POST',
    })
  }

  /**
   * Disconnect instance
   */
  async disconnectInstance(name: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/api/v1/instances/${name}/disconnect`, {
      method: 'POST',
    })
  }

  /**
   * Restart instance
   */
  async restartInstance(name: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/api/v1/instances/${name}/restart`, {
      method: 'POST',
    })
  }

  // ============================================================================
  // CONTACTS
  // ============================================================================

  /**
   * Get contacts for instance
   */
  async getContacts(
    instanceName: string,
    page = 1,
    pageSize = 50,
    searchQuery?: string
  ): Promise<PaginatedResponse<Contact>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    })
    if (searchQuery) params.append('search_query', searchQuery)

    const response = await this.request<any>(
      `/api/v1/omni/${instanceName}/contacts?${params}`
    )

    return {
      data: response.contacts || [],
      total_count: response.total_count || 0,
      page: response.page || page,
      page_size: response.page_size || pageSize,
      has_more: response.has_more || false,
    }
  }

  // ============================================================================
  // CHATS
  // ============================================================================

  /**
   * Get chats for instance
   */
  async getChats(
    instanceName: string,
    page = 1,
    pageSize = 50,
    chatTypeFilter?: string
  ): Promise<PaginatedResponse<Chat>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    })
    if (chatTypeFilter) params.append('chat_type_filter', chatTypeFilter)

    const response = await this.request<any>(
      `/api/v1/omni/${instanceName}/chats?${params}`
    )

    return {
      data: response.chats || [],
      total_count: response.total_count || 0,
      page: response.page || page,
      page_size: response.page_size || pageSize,
      has_more: response.has_more || false,
    }
  }

  // ============================================================================
  // MESSAGES
  // ============================================================================

  /**
   * Send text message
   */
  async sendTextMessage(
    instanceName: string,
    phone: string,
    message: string,
    quotedMessageId?: string
  ): Promise<Message> {
    return this.request(`/api/v1/messages/${instanceName}/send-text`, {
      method: 'POST',
      body: JSON.stringify({
        phone,
        message,
        quoted_message_id: quotedMessageId,
      }),
    })
  }

  /**
   * Send media message
   */
  async sendMediaMessage(
    instanceName: string,
    phone: string,
    mediaUrl: string,
    mediaType: 'image' | 'video' | 'document',
    caption?: string
  ): Promise<Message> {
    return this.request(`/api/v1/messages/${instanceName}/send-media`, {
      method: 'POST',
      body: JSON.stringify({
        phone,
        media_url: mediaUrl,
        media_type: mediaType,
        caption,
      }),
    })
  }

  /**
   * Send audio message
   */
  async sendAudioMessage(
    instanceName: string,
    phone: string,
    audioUrl: string
  ): Promise<Message> {
    return this.request(`/api/v1/messages/${instanceName}/send-audio`, {
      method: 'POST',
      body: JSON.stringify({
        phone,
        audio_url: audioUrl,
      }),
    })
  }

  /**
   * Send reaction
   */
  async sendReaction(
    instanceName: string,
    phone: string,
    messageId: string,
    emoji: string
  ): Promise<Message> {
    return this.request(`/api/v1/messages/${instanceName}/send-reaction`, {
      method: 'POST',
      body: JSON.stringify({
        phone,
        message_id: messageId,
        emoji,
      }),
    })
  }

  // ============================================================================
  // TRACES
  // ============================================================================

  /**
   * Get message traces
   */
  async getTraces(
    instanceName?: string,
    page = 1,
    pageSize = 50,
    statusFilter?: string
  ): Promise<PaginatedResponse<Trace>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    })
    if (instanceName) params.append('instance_name', instanceName)
    if (statusFilter) params.append('status_filter', statusFilter)

    return this.request(`/api/v1/traces?${params}`)
  }

  /**
   * Get trace by ID
   */
  async getTrace(traceId: string): Promise<Trace> {
    return this.request(`/api/v1/traces/${traceId}`)
  }
}
