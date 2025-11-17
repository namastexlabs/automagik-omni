import { z } from 'zod'

// Evolution API process status
export const EvolutionProcessStatusSchema = z.enum([
  'stopped',
  'starting',
  'running',
  'stopping',
  'error',
])

// Evolution API process information
export const EvolutionProcessInfoSchema = z.object({
  status: EvolutionProcessStatusSchema,
  pid: z.number().optional(),
  uptime: z.number().optional(),
  lastError: z.string().optional(),
  restartCount: z.number(),
  port: z.number(),
  apiKey: z.string(),
})
