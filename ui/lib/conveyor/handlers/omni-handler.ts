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
 * Wrap handler with error transformation for user-friendly messages
 */
const wrapHandler = <T extends (...args: any[]) => Promise<any>>(handler: T): T => {
  return (async (...args: any[]) => {
    try {
      return await handler(...args)
    } catch (error) {
      // Transform circuit breaker errors into user-friendly messages
      if (error instanceof Error) {
        const message = error.message.toLowerCase()

        if (message.includes('circuit breaker is open') || message.includes('backend is starting')) {
          throw new Error('Backend is starting up, please wait...')
        }

        if (message.includes('econnrefused') || message.includes('fetch failed')) {
          throw new Error('Cannot connect to backend. Please check if the backend is running.')
        }
      }

      // Re-throw original error
      throw error
    }
  }) as T
}

/**
 * Register Omni IPC handlers
 */
export const registerOmniHandlers = () => {
  // ========== INSTANCES ==========
  handle('omni:instances:list', wrapHandler(async () => {
    return await getClient().getInstances()
  }))

  handle('omni:instances:get', wrapHandler(async (name: string) => {
    return await getClient().getInstance(name)
  }))

  handle('omni:instances:create', wrapHandler(async (data: Partial<Instance>) => {
    return await getClient().createInstance(data)
  }))

  handle('omni:instances:update', wrapHandler(async (name: string, data: Partial<Instance>) => {
    return await getClient().updateInstance(name, data)
  }))

  handle('omni:instances:delete', wrapHandler(async (name: string) => {
    await getClient().deleteInstance(name)
    return { success: true, message: `Instance ${name} deleted` }
  }))

  handle('omni:instances:qr', wrapHandler(async (name: string) => {
    return await getClient().getInstanceQR(name)
  }))

  handle('omni:instances:status', wrapHandler(async (name: string) => {
    return await getClient().getInstanceStatus(name)
  }))

  handle('omni:instances:connect', wrapHandler(async (name: string) => {
    return await getClient().connectInstance(name)
  }))

  handle('omni:instances:disconnect', wrapHandler(async (name: string) => {
    return await getClient().disconnectInstance(name)
  }))

  handle('omni:instances:restart', wrapHandler(async (name: string) => {
    return await getClient().restartInstance(name)
  }))

  // ========== CONTACTS ==========
  handle('omni:contacts:list', wrapHandler(async (name: string, page?: number, pageSize?: number, search?: string) => {
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
  }))

  // ========== CHATS ==========
  handle('omni:chats:list', wrapHandler(async (name: string, page?: number, pageSize?: number, filter?: string) => {
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
  }))

  // ========== MESSAGES ==========
  handle('omni:messages:list', async (instanceName: string, chatId: string, page?: number, pageSize?: number) => {
    const response = await getClient().getMessages(instanceName, chatId, page, pageSize)
    // Transform PaginatedResponse to MessagesResponse format
    return {
      messages: response.data || [],
      total_count: response.total_count || 0,
      page: response.page || 1,
      page_size: response.page_size || 50,
      has_more: response.has_more || false,
      instance_name: instanceName,
      chat_id: chatId,
      channel_type: response.data?.[0]?.channel_type as 'whatsapp' | 'discord' | undefined,
    }
  })

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
  handle('omni:traces:list', async (
    instanceName?: string,
    offset?: number,
    limit?: number,
    statusFilter?: string,
    phone?: string,
    messageType?: string
  ) => {
    // API client signature: getTraces(instanceName, limit, offset, traceStatus, phone, messageType)
    return await getClient().getTraces(instanceName, limit, offset, statusFilter, phone, messageType)
  })

  handle('omni:traces:get', async (traceId: string) => {
    return await getClient().getTrace(traceId)
  })

  handle('omni:traces:analytics', async (params?: { instanceName?: string; startDate?: string; endDate?: string }) => {
    return await getClient().getTraceAnalytics(params)
  })

  handle('omni:traces:payloads', async (traceId: string, includePayload: boolean) => {
    return await getClient().getTracePayloads(traceId, includePayload)
  })

  // ========== ACCESS RULES ==========
  handle('omni:access:list', async (instanceName?: string, ruleType?: 'allow' | 'block') => {
    return await getClient().listAccessRules({ instance_name: instanceName, rule_type: ruleType })
  })

  handle('omni:access:create', async (data: { phone_number: string; rule_type: 'allow' | 'block'; instance_name?: string }) => {
    return await getClient().createAccessRule(data)
  })

  handle('omni:access:delete', async (ruleId: number) => {
    await getClient().deleteAccessRule(ruleId)
    return { success: true, message: `Access rule ${ruleId} deleted` }
  })

  handle('omni:access:check', async (phoneNumber: string, instanceName?: string) => {
    return await getClient().checkPhoneAccess(phoneNumber, instanceName)
  })
}
