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
  contact_id: string
  name?: string
  phone_number?: string
  avatar_url?: string
  status?: string
  instance_name: string
  channel_type: 'whatsapp' | 'discord'
  is_group?: boolean
  is_business?: boolean
  business_description?: string
  last_seen?: string
  created_at?: string
  updated_at?: string
}

export interface Chat {
  chat_id: string
  name?: string
  chat_type?: 'direct' | 'group' | 'channel' | 'thread'
  avatar_url?: string
  unread_count?: number
  last_message_text?: string
  last_message_time?: string
  archived?: boolean
  muted?: boolean
  instance_name: string
  channel_type: 'whatsapp' | 'discord'
  participant_count?: number
  description?: string
  created_at?: string
  updated_at?: string
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
  trace_id: string
  instance_name: string
  sender_phone: string
  sender_name?: string
  message_type: string
  trace_status: string
  received_at: string
  completed_at?: string
  session_name?: string
  agent_session_id?: string
  whatsapp_message_id?: string
  has_media?: boolean
  has_quoted_message?: boolean
  agent_processing_time_ms?: number
  total_processing_time_ms?: number
  evolution_success?: boolean
  agent_response_success?: boolean
  error_message?: string
  error_stage?: string
  message_text?: string
  media_url?: string
  updated_at?: string
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
      `/api/v1/instances/${instanceName}/contacts?${params}`
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
      `/api/v1/instances/${instanceName}/chats?${params}`
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

  /**
   * Get trace analytics
   */
  async getTraceAnalytics(params?: {
    instanceName?: string
    startDate?: string
    endDate?: string
  }): Promise<{
    total_messages: number
    success_rate: number
    average_duration: number
    failed_count: number
    messages_over_time: Array<{ date: string; count: number }>
    success_vs_failed: Array<{ name: string; value: number }>
    message_types: Array<{ type: string; count: number }>
    top_contacts: Array<{ phone: string; count: number }>
  }> {
    const queryParams = new URLSearchParams()
    if (params?.instanceName) queryParams.append('instance_name', params.instanceName)
    if (params?.startDate) queryParams.append('start_date', params.startDate)
    if (params?.endDate) queryParams.append('end_date', params.endDate)

    return this.request(`/api/v1/traces/analytics/summary?${queryParams}`)
  }
}
