import { z } from 'zod'

// ============================================================================
// SHARED SCHEMAS
// ============================================================================

export const InstanceSchema = z.object({
  id: z.string(),
  name: z.string(),
  channel_type: z.string(),
  is_default: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
  evolution_url: z.string().optional(),
  whatsapp_instance: z.string().optional(),
  discord_bot_token: z.string().optional(),
  discord_guild_id: z.string().optional(),
  agent_api_url: z.string(),
  agent_api_key: z.string(),
  default_agent: z.string().optional(),
  agent_timeout: z.number(),
  status: z.enum(['connected', 'disconnected', 'connecting', 'error']).optional(),
  qr_code: z.string().optional(),
})

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
  id: z.string(),
  instance_name: z.string(),
  phone_number: z.string(),
  message_type: z.string(),
  status: z.enum(['received', 'processing', 'completed', 'failed']),
  created_at: z.string(),
  payload: z.any().optional(),
  error: z.string().optional(),
})

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
