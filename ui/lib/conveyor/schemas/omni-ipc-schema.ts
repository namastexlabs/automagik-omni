import { z } from 'zod'
import {
  InstanceSchema,
  ContactSchema,
  ChatSchema,
  MessageSchema,
  TraceSchema,
  PaginatedResponseSchema,
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
    return: z.object({ qr_code: z.string(), base64: z.string() }),
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
    return: PaginatedResponseSchema(ContactSchema),
  },

  // ========== CHATS ==========
  'omni:chats:list': {
    args: z.tuple([
      z.string(), // instance_name
      z.number().optional(), // page
      z.number().optional(), // page_size
      z.string().optional(), // chat_type_filter
    ]),
    return: PaginatedResponseSchema(ChatSchema),
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
      z.number().optional(), // page
      z.number().optional(), // page_size
      z.string().optional(), // status_filter
    ]),
    return: PaginatedResponseSchema(TraceSchema),
  },

  'omni:traces:get': {
    args: z.tuple([z.string()]), // trace_id
    return: TraceSchema,
  },
} as const
