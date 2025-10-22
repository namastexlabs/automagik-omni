import { ConveyorApi } from '@/lib/preload/shared'
import type {
  Instance,
  Contact,
  Chat,
  Message,
  Trace,
  AccessRule,
  CreateAccessRule,
  CheckAccessResponse,
} from '@/lib/conveyor/schemas/omni-schema'

export interface PaginatedResponse<T> {
  data?: T[]
  total_count: number
  page: number
  page_size: number
  has_more: boolean
}

export interface MessagesResponse {
  messages: Message[]
  total_count: number
  page: number
  page_size: number
  has_more: boolean
  instance_name: string
  chat_id: string
  channel_type?: 'whatsapp' | 'discord'
}

/**
 * Omni API
 * Type-safe client for Omni backend operations
 */
export class OmniApi extends ConveyorApi {
  // ========== INSTANCES ==========

  listInstances = (): Promise<Instance[]> => {
    return this.invoke('omni:instances:list')
  }

  getInstance = (name: string): Promise<Instance> => {
    return this.invoke('omni:instances:get', name)
  }

  createInstance = (data: Partial<Instance>): Promise<Instance> => {
    return this.invoke('omni:instances:create', data)
  }

  updateInstance = (name: string, data: Partial<Instance>): Promise<Instance> => {
    return this.invoke('omni:instances:update', name, data)
  }

  deleteInstance = (name: string): Promise<{ success: boolean; message: string }> => {
    return this.invoke('omni:instances:delete', name)
  }

  getInstanceQR = (name: string): Promise<{ qr_code: string; base64: string }> => {
    return this.invoke('omni:instances:qr', name)
  }

  getInstanceStatus = (name: string): Promise<{ status: string; connected: boolean }> => {
    return this.invoke('omni:instances:status', name)
  }

  connectInstance = (name: string): Promise<{ success: boolean; message: string }> => {
    return this.invoke('omni:instances:connect', name)
  }

  disconnectInstance = (name: string): Promise<{ success: boolean; message: string }> => {
    return this.invoke('omni:instances:disconnect', name)
  }

  restartInstance = (name: string): Promise<{ success: boolean; message: string }> => {
    return this.invoke('omni:instances:restart', name)
  }

  // ========== CONTACTS ==========

  listContacts = (
    instanceName: string,
    page?: number,
    pageSize?: number,
    searchQuery?: string
  ): Promise<PaginatedResponse<Contact>> => {
    return this.invoke('omni:contacts:list', instanceName, page, pageSize, searchQuery)
  }

  // ========== CHATS ==========

  listChats = (
    instanceName: string,
    page?: number,
    pageSize?: number,
    chatTypeFilter?: string
  ): Promise<PaginatedResponse<Chat>> => {
    return this.invoke('omni:chats:list', instanceName, page, pageSize, chatTypeFilter)
  }

  // ========== MESSAGES ==========

  listMessages = (
    instanceName: string,
    chatId: string,
    page?: number,
    pageSize?: number
  ): Promise<MessagesResponse> => {
    return this.invoke('omni:messages:list', instanceName, chatId, page, pageSize)
  }

  sendTextMessage = (
    instanceName: string,
    phone: string,
    message: string,
    quotedMessageId?: string
  ): Promise<Message> => {
    return this.invoke('omni:messages:send-text', instanceName, phone, message, quotedMessageId)
  }

  sendMediaMessage = (
    instanceName: string,
    phone: string,
    mediaUrl: string,
    mediaType: 'image' | 'video' | 'document',
    caption?: string
  ): Promise<Message> => {
    return this.invoke('omni:messages:send-media', instanceName, phone, mediaUrl, mediaType, caption)
  }

  sendAudioMessage = (
    instanceName: string,
    phone: string,
    audioUrl: string
  ): Promise<Message> => {
    return this.invoke('omni:messages:send-audio', instanceName, phone, audioUrl)
  }

  sendReaction = (
    instanceName: string,
    phone: string,
    messageId: string,
    emoji: string
  ): Promise<Message> => {
    return this.invoke('omni:messages:send-reaction', instanceName, phone, messageId, emoji)
  }

  // ========== TRACES ==========

  listTraces = (
    instanceName?: string,
    offset?: number,
    limit?: number,
    statusFilter?: string,
    phone?: string,
    messageType?: string
  ): Promise<Trace[]> => {
    return this.invoke('omni:traces:list', instanceName, offset, limit, statusFilter, phone, messageType)
  }

  getTrace = (traceId: string): Promise<Trace> => {
    return this.invoke('omni:traces:get', traceId)
  }

  getTraceAnalytics = (params?: {
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
  }> => {
    return this.invoke('omni:traces:analytics', params)
  }

  // ========== ACCESS RULES ==========

  listAccessRules = (
    instanceName?: string,
    ruleType?: 'allow' | 'block'
  ): Promise<AccessRule[]> => {
    return this.invoke('omni:access:list', instanceName, ruleType)
  }

  createAccessRule = (data: CreateAccessRule): Promise<AccessRule> => {
    return this.invoke('omni:access:create', data)
  }

  deleteAccessRule = (ruleId: number): Promise<{ success: boolean; message: string }> => {
    return this.invoke('omni:access:delete', ruleId)
  }

  checkPhoneAccess = (
    phoneNumber: string,
    instanceName?: string
  ): Promise<CheckAccessResponse> => {
    return this.invoke('omni:access:check', phoneNumber, instanceName)
  }
}
