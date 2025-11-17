import { z } from 'zod'
import { EvolutionProcessInfoSchema } from './evolution-schema'

export const evolutionIpcSchema = {
  // Start Evolution API
  'evolution:start': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Stop Evolution API
  'evolution:stop': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Restart Evolution API
  'evolution:restart': {
    args: z.tuple([]),
    return: z.object({
      success: z.boolean(),
      message: z.string(),
    }),
  },

  // Get Evolution API status
  'evolution:status': {
    args: z.tuple([]),
    return: EvolutionProcessInfoSchema,
  },
} as const
