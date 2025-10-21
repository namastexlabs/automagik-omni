import { z } from 'zod'

// ============================================================================
// SHARED SCHEMAS
// ============================================================================

export const InstanceSchema = z.object({
  id: z.union([z.string(), z.number()]).transform(val => String(val)),
  name: z.string(),
  channel_type: z.enum(['whatsapp', 'discord']),

  // WhatsApp fields
  evolution_api_url: z.string().nullable().optional(),
  evolution_api_key: z.string().nullable().optional(),
  evolution_instance_name: z.string().nullable().optional(),

  // Discord fields
  discord_bot_token: z.string().nullable().optional(),
  discord_application_id: z.string().nullable().optional(),

  // Status fields from Evolution API (when include_status=true)
  instance: z.object({
    instanceName: z.string().optional(),
    status: z.string().optional(),
  }).nullable().optional(),

  // Connection status
  state: z.string().nullable().optional(),

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
}).passthrough()

export const ContactSchema = z.object({
  contact_id: z.string(),
  name: z.string().nullable().optional(),
  phone_number: z.string().nullable().optional(),
  avatar_url: z.string().nullable().optional(),
  status: z.string().nullable().optional(),
  instance_name: z.string(),
  channel_type: z.enum(['whatsapp', 'discord']),
  is_group: z.boolean().nullable().optional(),
  is_business: z.boolean().nullable().optional(),
  business_description: z.string().nullable().optional(),
  last_seen: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough()

export const ChatSchema = z.object({
  chat_id: z.string(),
  name: z.string().nullable().optional(),
  chat_type: z.enum(['direct', 'group', 'channel', 'thread']).nullable().optional(),
  avatar_url: z.string().nullable().optional(),
  unread_count: z.number().nullable().optional(),
  last_message_text: z.string().nullable().optional(),
  last_message_time: z.string().nullable().optional(),
  archived: z.boolean().nullable().optional(),
  muted: z.boolean().nullable().optional(),
  instance_name: z.string(),
  channel_type: z.enum(['whatsapp', 'discord']),
  participant_count: z.number().nullable().optional(),
  description: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
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
  sender_phone: z.string(),
  sender_name: z.string().optional().nullable(),
  message_type: z.string(),
  status: z.string(),
  received_at: z.string(),
  completed_at: z.string().optional().nullable(),
  session_name: z.string().optional().nullable(),
  agent_session_id: z.string().optional().nullable(),
  whatsapp_message_id: z.string().optional().nullable(),
  has_media: z.boolean().optional().nullable(),
  has_quoted_message: z.boolean().optional().nullable(),
  agent_processing_time_ms: z.number().optional().nullable(),
  total_processing_time_ms: z.number().optional().nullable(),
  evolution_success: z.boolean().optional().nullable(),
  agent_response_success: z.boolean().optional().nullable(),
  error_message: z.string().optional().nullable(),
  error_stage: z.string().optional().nullable(),
}).passthrough()

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    data: z.array(itemSchema),
    total_count: z.number(),
    page: z.number(),
    page_size: z.number(),
    has_more: z.boolean(),
  })

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type Instance = z.infer<typeof InstanceSchema>
export type Contact = z.infer<typeof ContactSchema>
export type Chat = z.infer<typeof ChatSchema>
export type Message = z.infer<typeof MessageSchema>
export type Trace = z.infer<typeof TraceSchema>
