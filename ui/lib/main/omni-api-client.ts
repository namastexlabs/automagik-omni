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
  name?: string
  channel_type: 'whatsapp' | 'discord'
  instance_name: string
  avatar_url?: string | null
  status?: 'unknown' | 'online' | 'offline' | 'away' | 'dnd'
  is_verified?: boolean | null
  is_business?: boolean | null
  channel_data?: Record<string, any>
  created_at?: string | null
  last_seen?: string | null
}

export interface Chat {
  id: string
  name?: string
  chat_type?: 'direct' | 'group' | 'channel' | 'thread'
  avatar_url?: string | null
  unread_count?: number | null
  last_message_text?: string | null
  last_message_at?: string | null
  is_archived?: boolean
  is_muted?: boolean
  is_pinned?: boolean
  instance_name: string
  channel_type: 'whatsapp' | 'discord'
  participant_count?: number | null
  description?: string | null
  created_at?: string | null
  channel_data?: Record<string, any>
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
  whatsapp_message_id: string | null
  sender_phone: string | null
  sender_name: string | null
  message_type: string | null
  has_media: boolean
  has_quoted_message: boolean
  session_name: string | null
  agent_session_id: string | null
  status: string
  error_message: string | null
  error_stage: string | null
  received_at: string | null
  completed_at: string | null
  agent_processing_time_ms: number | null
  total_processing_time_ms: number | null
  agent_response_success: boolean | null
  evolution_success: boolean | null
}

export interface AccessRule {
  id: number
  phone_number: string
  rule_type: 'allow' | 'block'
  instance_name: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface CreateAccessRule {
  phone_number: string
  rule_type: 'allow' | 'block'
  instance_name?: string
}

export interface CheckAccessResponse {
  allowed: boolean
  rule_type?: 'allow' | 'block' | null
  rule_id?: number | null
  phone_number: string
  instance_name?: string | null
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

      // Handle 204 No Content responses (like DELETE operations)
      if (response.status === 204 || response.headers.get('content-length') === '0') {
        return undefined as T
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
    const response = await this.request<{
      success: boolean
      message_id?: string
      status: string
      error?: string
    }>(`/api/v1/instance/${instanceName}/send-text`, {
      method: 'POST',
      body: JSON.stringify({
        phone_number: phone,
        text: message,
        quoted_message_id: quotedMessageId,
      }),
    })

    // Transform API response to Message format for UI
    return {
      id: response.message_id || crypto.randomUUID(),
      from: 'me',
      to: phone,
      content: message,
      timestamp: new Date().toISOString(),
      message_type: 'text',
      status: response.success ? 'sent' : 'failed',
    }
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
    // Determine MIME type based on media type
    const mimeTypeMap: Record<string, string> = {
      image: 'image/jpeg',
      video: 'video/mp4',
      document: 'application/pdf',
    }

    const response = await this.request<{
      success: boolean
      message_id?: string
      status: string
      error?: string
    }>(`/api/v1/instance/${instanceName}/send-media`, {
      method: 'POST',
      body: JSON.stringify({
        phone_number: phone,
        media_url: mediaUrl,
        media_type: mediaType,
        mime_type: mimeTypeMap[mediaType] || 'application/octet-stream',
        caption,
      }),
    })

    // Transform API response to Message format for UI
    return {
      id: response.message_id || crypto.randomUUID(),
      from: 'me',
      to: phone,
      content: caption || `[${mediaType}]`,
      timestamp: new Date().toISOString(),
      message_type: 'media',
      status: response.success ? 'sent' : 'failed',
    }
  }

  /**
   * Send audio message
   */
  async sendAudioMessage(
    instanceName: string,
    phone: string,
    audioUrl: string
  ): Promise<Message> {
    const response = await this.request<{
      success: boolean
      message_id?: string
      status: string
      error?: string
    }>(`/api/v1/instance/${instanceName}/send-audio`, {
      method: 'POST',
      body: JSON.stringify({
        phone_number: phone,
        audio_url: audioUrl,
      }),
    })

    // Transform API response to Message format for UI
    return {
      id: response.message_id || crypto.randomUUID(),
      from: 'me',
      to: phone,
      content: '[audio]',
      timestamp: new Date().toISOString(),
      message_type: 'audio',
      status: response.success ? 'sent' : 'failed',
    }
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
    const response = await this.request<{
      success: boolean
      message_id?: string
      status: string
      error?: string
    }>(`/api/v1/instance/${instanceName}/send-reaction`, {
      method: 'POST',
      body: JSON.stringify({
        phone_number: phone,
        message_id: messageId,
        reaction: emoji,
      }),
    })

    // Transform API response to Message format for UI
    return {
      id: response.message_id || crypto.randomUUID(),
      from: 'me',
      to: phone,
      content: emoji,
      timestamp: new Date().toISOString(),
      message_type: 'reaction',
      status: response.success ? 'sent' : 'failed',
    }
  }

  // ============================================================================
  // TRACES
  // ============================================================================

  /**
   * Get message traces
   */
  async getTraces(
    instanceName?: string,
    limit = 50,
    offset = 0,
    traceStatus?: string,
    phone?: string,
    messageType?: string
  ): Promise<Trace[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    if (instanceName) params.append('instance_name', instanceName)
    if (traceStatus) params.append('trace_status', traceStatus)
    if (phone) params.append('phone', phone)
    if (messageType) params.append('message_type', messageType)

    return this.request<Trace[]>(`/api/v1/traces?${params}`)
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

    const response = await this.request<{
      total_messages: number
      successful_messages: number
      failed_messages: number
      success_rate: number
      avg_processing_time_ms: number | null
      avg_agent_time_ms: number | null
      message_types: Record<string, number>
      error_stages: Record<string, number>
      instances: Record<string, number>
    }>(`/api/v1/traces/analytics/summary?${queryParams}`)

    // Transform backend response to UI format
    return {
      total_messages: response.total_messages || 0,
      success_rate: response.success_rate || 0,
      average_duration: response.avg_processing_time_ms || 0,
      failed_count: response.failed_messages || 0,
      messages_over_time: [], // Not provided by current API
      success_vs_failed: [
        { name: 'Success', value: response.successful_messages || 0 },
        { name: 'Failed', value: response.failed_messages || 0 },
      ],
      message_types: Object.entries(response.message_types || {}).map(([type, count]) => ({
        type,
        count,
      })),
      top_contacts: [], // Not provided by current API
    }
  }

  // ============================================================================
  // ACCESS RULES
  // ============================================================================

  /**
   * List access rules with optional filters
   */
  async listAccessRules(filters?: {
    instance_name?: string
    rule_type?: 'allow' | 'block'
  }): Promise<AccessRule[]> {
    const params = new URLSearchParams()
    if (filters?.instance_name) params.append('instance_name', filters.instance_name)
    if (filters?.rule_type) params.append('rule_type', filters.rule_type)

    const queryString = params.toString()
    return this.request<AccessRule[]>(
      `/api/v1/access/rules${queryString ? `?${queryString}` : ''}`
    )
  }

  /**
   * Create new access rule
   */
  async createAccessRule(data: CreateAccessRule): Promise<AccessRule> {
    return this.request<AccessRule>('/api/v1/access/rules', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  /**
   * Delete access rule
   */
  async deleteAccessRule(ruleId: number): Promise<void> {
    return this.request<void>(`/api/v1/access/rules/${ruleId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Check if phone number is allowed
   */
  async checkPhoneAccess(
    phoneNumber: string,
    instanceName?: string
  ): Promise<CheckAccessResponse> {
    const params = new URLSearchParams()
    if (instanceName) params.append('instance_name', instanceName)

    const queryString = params.toString()
    return this.request<CheckAccessResponse>(
      `/api/v1/access/check/${phoneNumber}${queryString ? `?${queryString}` : ''}`
    )
  }
}
