import { z } from 'zod'
import {
  InstanceSchema,
  MessageSchema,
  TraceSchema,
  ContactsResponseSchema,
  ChatsResponseSchema,
  AccessRuleSchema,
  AccessRuleListResponseSchema,
  CheckAccessResponseSchema,
} from './omni-schema'

export const omniIpcSchema = {
  // ========== INSTANCES ==========
  'omni:instances:list': {
    args: z.tuple([]),
    return: z.array(InstanceSchema),
  },

  'omni:instances:get': {
    args: z.tuple([z.string()]), // instance_name
    return: InstanceSchema,
  },

  'omni:instances:create': {
    args: z.tuple([z.object({}).passthrough()]), // instance data
    return: InstanceSchema,
  },

  'omni:instances:update': {
    args: z.tuple([z.string(), z.object({}).passthrough()]), // name, data
    return: InstanceSchema,
  },

  'omni:instances:delete': {
    args: z.tuple([z.string()]), // instance_name
    return: z.object({ success: z.boolean(), message: z.string() }),
  },

  'omni:instances:qr': {
    args: z.tuple([z.string()]), // instance_name
    return: z.object({
      instance_name: z.string(),
      channel_type: z.string(),
      qr_code: z.string().nullable(),
      base64: z.string().nullable().optional(),
      message: z.string().optional(),
    }),
  },

  'omni:instances:status': {
    args: z.tuple([z.string()]), // instance_name
    return: z.object({ status: z.string(), connected: z.boolean() }),
  },

  'omni:instances:connect': {
    args: z.tuple([z.string()]), // instance_name
    return: z.object({ success: z.boolean(), message: z.string() }),
  },

  'omni:instances:disconnect': {
    args: z.tuple([z.string()]), // instance_name
    return: z.object({ success: z.boolean(), message: z.string() }),
  },

  'omni:instances:restart': {
    args: z.tuple([z.string()]), // instance_name
    return: z.object({ success: z.boolean(), message: z.string() }),
  },

  // ========== CONTACTS ==========
  'omni:contacts:list': {
    args: z.tuple([
      z.string(), // instance_name
      z.number().optional(), // page
      z.number().optional(), // page_size
      z.string().optional(), // search_query
    ]),
    return: ContactsResponseSchema,  // Use specific schema with "contacts" field
  },

  // ========== CHATS ==========
  'omni:chats:list': {
    args: z.tuple([
      z.string(), // instance_name
      z.number().optional(), // page
      z.number().optional(), // page_size
      z.string().optional(), // chat_type_filter
    ]),
    return: ChatsResponseSchema,  // Use specific schema with "chats" field
  },

  // ========== MESSAGES ==========
  'omni:messages:send-text': {
    args: z.tuple([
      z.string(), // instance_name
      z.string(), // phone
      z.string(), // message
      z.string().optional(), // quoted_message_id
    ]),
    return: MessageSchema,
  },

  'omni:messages:send-media': {
    args: z.tuple([
      z.string(), // instance_name
      z.string(), // phone
      z.string(), // media_url
      z.enum(['image', 'video', 'document']), // media_type
      z.string().optional(), // caption
    ]),
    return: MessageSchema,
  },

  'omni:messages:send-audio': {
    args: z.tuple([
      z.string(), // instance_name
      z.string(), // phone
      z.string(), // audio_url
    ]),
    return: MessageSchema,
  },

  'omni:messages:send-reaction': {
    args: z.tuple([
      z.string(), // instance_name
      z.string(), // phone
      z.string(), // message_id
      z.string(), // emoji
    ]),
    return: MessageSchema,
  },

  // ========== TRACES ==========
  'omni:traces:list': {
    args: z.tuple([
      z.string().optional(), // instance_name
      z.number().optional(), // offset
      z.number().optional(), // limit
      z.string().optional(), // status_filter
      z.string().optional(), // phone
      z.string().optional(), // message_type
    ]),
    return: z.array(TraceSchema),
  },

  'omni:traces:get': {
    args: z.tuple([z.string()]), // trace_id
    return: TraceSchema,
  },

  'omni:traces:analytics': {
    args: z.tuple([
      z.object({
        instanceName: z.string().optional(),
        startDate: z.string().optional(),
        endDate: z.string().optional(),
      }).optional()
    ]),
    return: z.object({
      total_traces: z.number().optional().default(0),
      by_status: z.record(z.number()).optional().default({}),
      by_instance: z.record(z.number()).optional().default({}),
      by_message_type: z.record(z.number()).optional().default({}),
      total_messages: z.number().optional(),
      success_rate: z.number().optional(),
      average_duration: z.number().optional(),
      failed_count: z.number().optional(),
    }).passthrough(),
  },

  // ========== ACCESS RULES ==========
  'omni:access:list': {
    args: z.tuple([
      z.string().optional(), // instance_name
      z.enum(['allow', 'block']).optional(), // rule_type
    ]),
    return: AccessRuleListResponseSchema,
  },

  'omni:access:create': {
    args: z.tuple([
      z.object({
        phone_number: z.string(),
        rule_type: z.enum(['allow', 'block']),
        instance_name: z.string().optional(),
      })
    ]),
    return: AccessRuleSchema,
  },

  'omni:access:delete': {
    args: z.tuple([z.number()]), // rule_id
    return: z.object({ success: z.boolean(), message: z.string() }),
  },

  'omni:access:check': {
    args: z.tuple([
      z.string(), // phone_number
      z.string().optional(), // instance_name
    ]),
    return: CheckAccessResponseSchema,
  },
} as const
