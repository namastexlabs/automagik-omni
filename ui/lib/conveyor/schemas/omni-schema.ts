import { z } from 'zod'

// ============================================================================
// SHARED SCHEMAS
// ============================================================================

export const InstanceSchema = z.object({
  id: z.union([z.string(), z.number()]).transform(val => String(val)),
  name: z.string(),
  channel_type: z.string(),
  is_default: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
  evolution_url: z.string().optional().nullable(),
  whatsapp_instance: z.string().optional().nullable(),
  discord_bot_token: z.string().optional().nullable(),
  discord_guild_id: z.string().optional().nullable(),
  agent_api_url: z.string(),
  agent_api_key: z.string(),
  default_agent: z.string().optional().nullable(),
  agent_timeout: z.number(),
  status: z.enum(['connected', 'disconnected', 'connecting', 'error']).optional().nullable(),
  qr_code: z.string().optional().nullable(),
}).passthrough()

export const ContactSchema = z.object({
  id: z.string(),
  name: z.string(),
  phone_number: z.string().optional(),
  profile_picture_url: z.string().optional(),
  status: z.string().optional(),
  channel_type: z.string(),
})

export const ChatSchema = z.object({
  id: z.string(),
  name: z.string(),
  chat_type: z.enum(['direct', 'group', 'channel', 'thread']),
  unread_count: z.number(),
  last_message: z.string().optional(),
  last_message_timestamp: z.string().optional(),
  archived: z.boolean(),
  channel_type: z.string(),
})

export const MessageSchema = z.object({
  id: z.string(),
  from: z.string(),
  to: z.string(),
  content: z.string(),
  timestamp: z.string(),
  message_type: z.enum(['text', 'media', 'audio', 'sticker', 'contact', 'reaction']),
  status: z.enum(['pending', 'sent', 'delivered', 'read', 'failed']),
})

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
