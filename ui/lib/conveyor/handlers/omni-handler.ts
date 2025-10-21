import { handle } from '@/lib/main/shared'
import { OmniApiClient } from '@/lib/main/omni-api-client'
import type { Instance } from '@/lib/conveyor/schemas/omni-schema'

let apiClient: OmniApiClient | null = null

/**
 * Initialize Omni API client
 */
export const initOmniClient = (baseUrl: string, apiKey: string) => {
  apiClient = new OmniApiClient({ baseUrl, apiKey })
  return apiClient
}

/**
 * Get API client instance
 */
const getClient = (): OmniApiClient => {
  if (!apiClient) {
    throw new Error('Omni API client not initialized')
  }
  return apiClient
}

/**
 * Register Omni IPC handlers
 */
export const registerOmniHandlers = () => {
  // ========== INSTANCES ==========
  handle('omni:instances:list', async () => {
    return await getClient().getInstances()
  })

  handle('omni:instances:get', async (name: string) => {
    return await getClient().getInstance(name)
  })

  handle('omni:instances:create', async (data: Partial<Instance>) => {
    return await getClient().createInstance(data)
  })

  handle('omni:instances:update', async (name: string, data: Partial<Instance>) => {
    return await getClient().updateInstance(name, data)
  })

  handle('omni:instances:delete', async (name: string) => {
    await getClient().deleteInstance(name)
    return { success: true, message: `Instance ${name} deleted` }
  })

  handle('omni:instances:qr', async (name: string) => {
    return await getClient().getInstanceQR(name)
  })

  handle('omni:instances:status', async (name: string) => {
    return await getClient().getInstanceStatus(name)
  })

  handle('omni:instances:connect', async (name: string) => {
    return await getClient().connectInstance(name)
  })

  handle('omni:instances:disconnect', async (name: string) => {
    return await getClient().disconnectInstance(name)
  })

  handle('omni:instances:restart', async (name: string) => {
    return await getClient().restartInstance(name)
  })

  // ========== CONTACTS ==========
  handle('omni:contacts:list', async (name: string, page?: number, pageSize?: number, search?: string) => {
    const response = await getClient().getContacts(name, page, pageSize, search)
    // Transform PaginatedResponse to ContactsResponse format
    return {
      contacts: response.data || [],
      total_count: response.total_count || 0,
      page: response.page || 1,
      page_size: response.page_size || 50,
      has_more: response.has_more || false,
      instance_name: name,
      channel_type: response.data?.[0]?.channel_type as 'whatsapp' | 'discord' | undefined,
    }
  })

  // ========== CHATS ==========
  handle('omni:chats:list', async (name: string, page?: number, pageSize?: number, filter?: string) => {
    const response = await getClient().getChats(name, page, pageSize, filter)
    // Transform PaginatedResponse to ChatsResponse format
    return {
      chats: response.data || [],
      total_count: response.total_count || 0,
      page: response.page || 1,
      page_size: response.page_size || 50,
      has_more: response.has_more || false,
      instance_name: name,
      channel_type: response.data?.[0]?.channel_type as 'whatsapp' | 'discord' | undefined,
    }
  })

  // ========== MESSAGES ==========
  handle('omni:messages:send-text', async (name: string, phone: string, message: string, quotedId?: string) => {
    return await getClient().sendTextMessage(name, phone, message, quotedId)
  })

  handle('omni:messages:send-media', async (
    name: string,
    phone: string,
    mediaUrl: string,
    mediaType: 'image' | 'video' | 'document',
    caption?: string
  ) => {
    return await getClient().sendMediaMessage(name, phone, mediaUrl, mediaType, caption)
  })

  handle('omni:messages:send-audio', async (name: string, phone: string, audioUrl: string) => {
    return await getClient().sendAudioMessage(name, phone, audioUrl)
  })

  handle('omni:messages:send-reaction', async (name: string, phone: string, messageId: string, emoji: string) => {
    return await getClient().sendReaction(name, phone, messageId, emoji)
  })

  // ========== TRACES ==========
  handle('omni:traces:list', async (instanceName?: string, page?: number, pageSize?: number, statusFilter?: string) => {
    return await getClient().getTraces(instanceName, page, pageSize, statusFilter)
  })

  handle('omni:traces:get', async (traceId: string) => {
    return await getClient().getTrace(traceId)
  })

  handle('omni:traces:analytics', async (params?: { instanceName?: string; startDate?: string; endDate?: string }) => {
    return await getClient().getTraceAnalytics(params)
  })
}
