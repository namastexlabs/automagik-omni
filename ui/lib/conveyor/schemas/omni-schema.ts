import { z } from 'zod'

// ============================================================================
// SHARED SCHEMAS
// ============================================================================

export const InstanceSchema = z.object({
  id: z.union([z.string(), z.number()]).transform(val => String(val)),
  name: z.string(),
  channel_type: z.enum(['whatsapp', 'discord']),
  is_default: z.boolean().optional(),
  is_active: z.boolean().optional(),

  // WhatsApp fields
  evolution_url: z.string().nullable().optional(),
  evolution_key: z.string().nullable().optional(),
  whatsapp_instance: z.string().nullable().optional(),

  // Discord fields
  discord_bot_token: z.string().nullable().optional(),
  discord_client_id: z.string().nullable().optional(),
  discord_guild_id: z.string().nullable().optional(),

  // Agent configuration
  agent_api_url: z.string().optional(),
  agent_api_key: z.string().optional(),
  default_agent: z.string().nullable().optional(),
  agent_timeout: z.number().nullable().optional(),

  // Evolution status (WhatsApp only)
  evolution_status: z.object({
    state: z.string().nullable().optional(),
    owner_jid: z.string().nullable().optional(),
    profile_name: z.string().nullable().optional(),
    profile_picture_url: z.string().nullable().optional(),
    last_updated: z.string().nullable().optional(),
    error: z.string().nullable().optional(),
  }).nullable().optional(),

  // Timestamps
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),

  // Settings
  reject_call: z.boolean().nullable().optional(),
  msg_call: z.string().nullable().optional(),
  groups_ignore: z.boolean().nullable().optional(),
  always_online: z.boolean().nullable().optional(),
  read_messages: z.boolean().nullable().optional(),
  read_status: z.boolean().nullable().optional(),
  sync_full_history: z.boolean().nullable().optional(),

  // Webhooks
  webhook_url: z.string().nullable().optional(),
  webhook_by_events: z.boolean().nullable().optional(),
  webhook_base64: z.boolean().nullable().optional(),
  webhook_events: z.array(z.string()).nullable().optional(),

  // Proxy and Rabbit
  proxy_host: z.string().nullable().optional(),
  proxy_port: z.string().nullable().optional(),
  proxy_protocol: z.string().nullable().optional(),
  proxy_username: z.string().nullable().optional(),
  proxy_password: z.string().nullable().optional(),
  rabbitmq_enabled: z.boolean().nullable().optional(),
  rabbitmq_events: z.array(z.string()).nullable().optional(),

  // SQS and Websocket
  sqs_enabled: z.boolean().nullable().optional(),
  sqs_events: z.array(z.string()).nullable().optional(),
  websocket_enabled: z.boolean().nullable().optional(),
  websocket_events: z.array(z.string()).nullable().optional(),

  // Chatwoot
  chatwoot_account_id: z.string().nullable().optional(),
  chatwoot_token: z.string().nullable().optional(),
  chatwoot_url: z.string().nullable().optional(),
  chatwoot_sign_msg: z.boolean().nullable().optional(),
  chatwoot_reopen_conversation: z.boolean().nullable().optional(),
  chatwoot_conversation_pending: z.boolean().nullable().optional(),
  chatwoot_import_contacts: z.boolean().nullable().optional(),
  chatwoot_name_inbox: z.string().nullable().optional(),
  chatwoot_merge_brazil_contacts: z.boolean().nullable().optional(),
  chatwoot_import_messages: z.boolean().nullable().optional(),
  chatwoot_days_limit_import_messages: z.number().nullable().optional(),
  chatwoot_organization: z.string().nullable().optional(),
  chatwoot_logo: z.string().nullable().optional(),
}).passthrough().transform((data) => {
  // Derive status from evolution_status.state for WhatsApp
  let status: 'connected' | 'disconnected' | 'connecting' | 'error' = 'disconnected'

  if (data.channel_type === 'whatsapp' && data.evolution_status) {
    const state = data.evolution_status.state
    const statusMap: Record<string, 'connected' | 'disconnected' | 'connecting' | 'error'> = {
      'open': 'connected',
      'close': 'disconnected',
      'connecting': 'connecting',
    }
    status = statusMap[state || ''] || 'error'
  } else if (data.channel_type === 'discord') {
    // For Discord, check is_active
    status = data.is_active ? 'connected' : 'disconnected'
  }

  return {
    ...data,
    status,
  }
})

export const ContactSchema = z.object({
  id: z.string(),
  name: z.string().optional(),
  channel_type: z.enum(['whatsapp', 'discord']),
  instance_name: z.string(),
  avatar_url: z.string().nullable().optional(),
  status: z.enum(['unknown', 'online', 'offline', 'away', 'dnd']).optional(),
  is_verified: z.boolean().nullable().optional(),
  is_business: z.boolean().nullable().optional(),
  channel_data: z.record(z.any()).optional(),  // Contains phone_number
  created_at: z.string().nullable().optional(),
  last_seen: z.string().nullable().optional(),
}).passthrough()

export const ChatSchema = z.object({
  id: z.string(),
  name: z.string().optional(),
  chat_type: z.enum(['direct', 'group', 'channel', 'thread']).optional(),
  avatar_url: z.string().nullable().optional(),
  unread_count: z.number().nullable().optional(),
  last_message_text: z.string().nullable().optional(),
  last_message_at: z.string().nullable().optional(),  // NOT last_message_time
  is_archived: z.boolean().optional(),  // NOT archived
  is_muted: z.boolean().optional(),     // NOT muted
  is_pinned: z.boolean().optional(),
  instance_name: z.string(),
  channel_type: z.enum(['whatsapp', 'discord']),
  participant_count: z.number().nullable().optional(),
  description: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  channel_data: z.record(z.any()).optional(),
}).passthrough()

export const MessageSchema = z.object({
  id: z.string(),
  from: z.string(),
  to: z.string(),
  content: z.string(),
  timestamp: z.string(),
  message_type: z.enum(['text', 'media', 'audio', 'sticker', 'contact', 'reaction']),
  status: z.enum(['pending', 'sent', 'delivered', 'read', 'failed']),
}).passthrough()

export const TraceSchema = z.object({
  trace_id: z.string(),
  instance_name: z.string(),
  whatsapp_message_id: z.string().nullable(),
  sender_phone: z.string().nullable(),
  sender_name: z.string().nullable(),
  message_type: z.string().nullable(),
  has_media: z.boolean(),
  has_quoted_message: z.boolean(),
  session_name: z.string().nullable().optional(),
  agent_session_id: z.string().nullable().optional(),
  status: z.string(),  // NOT trace_status
  error_message: z.string().nullable(),
  error_stage: z.string().nullable(),
  received_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  agent_processing_time_ms: z.number().nullable(),
  total_processing_time_ms: z.number().nullable(),
  agent_response_success: z.boolean().nullable(),
  evolution_success: z.boolean().nullable(),
}).passthrough()

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    data: z.array(itemSchema),
    total_count: z.number(),
    page: z.number(),
    page_size: z.number(),
    has_more: z.boolean(),
  })

// Specific response schemas that match backend API
// Using z.any() for contacts/chats arrays to avoid Zod circular reference cache issues
export const ContactsResponseSchema = z.object({
  contacts: z.array(z.any()),
  total_count: z.number(),
  page: z.number(),
  page_size: z.number(),
  has_more: z.boolean(),
  instance_name: z.string().optional(),
  channel_type: z.enum(['whatsapp', 'discord']).optional(),
  partial_errors: z.array(z.any()).optional(),
}).passthrough()

export const ChatsResponseSchema = z.object({
  chats: z.array(z.any()),
  total_count: z.number(),
  page: z.number(),
  page_size: z.number(),
  has_more: z.boolean(),
  instance_name: z.string().optional(),
  channel_type: z.enum(['whatsapp', 'discord']).optional(),
  partial_errors: z.array(z.any()).optional(),
}).passthrough()

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type Instance = z.infer<typeof InstanceSchema>
export type Contact = z.infer<typeof ContactSchema>
export type Chat = z.infer<typeof ChatSchema>
export type Message = z.infer<typeof MessageSchema>
export type Trace = z.infer<typeof TraceSchema>
