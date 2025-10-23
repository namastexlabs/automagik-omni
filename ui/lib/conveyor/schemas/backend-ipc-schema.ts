import { z } from 'zod'
import {
  BackendStatusSchema,
  HealthCheckSchema,
  BackendConfigSchema,
  BackendLogsSchema,
  BackendLogResultSchema,
  BackendProcessInfoSchema,
} from './backend-schema'

export const backendIpcSchema = {
  // ==================== BackendManager (subprocess) handlers ====================

  // Start backend via BackendManager
  'backend:manager:start': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Stop backend via BackendManager
  'backend:manager:stop': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Restart backend via BackendManager
  'backend:manager:restart': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Get backend process info
  'backend:manager:status': {
    args: z.tuple([]),
    return: BackendProcessInfoSchema,
  },

  // ==================== BackendMonitor (PM2) handlers ====================

  // Get overall backend status
  'backend:status': {
    args: z.tuple([]),
    return: BackendStatusSchema,
  },

  // Start backend services
  'backend:start': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Stop backend services
  'backend:stop': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Restart backend services
  'backend:restart': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Health check
  'backend:health': {
    args: z.tuple([]),
    return: HealthCheckSchema,
  },

  // Get backend configuration
  'backend:config:get': {
    args: z.tuple([]),
    return: BackendConfigSchema,
  },

  // Update backend configuration
  'backend:config:set': {
    args: z.tuple([BackendConfigSchema.partial()]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Get logs from backend services
  'backend:logs': {
    args: z.tuple([BackendLogsSchema]),
    return: BackendLogResultSchema,
  },
} as const
