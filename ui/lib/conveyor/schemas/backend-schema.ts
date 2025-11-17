import { z } from 'zod'

// Backend process status enum
export const BackendProcessStatusSchema = z.enum([
  'stopped',
  'starting',
  'running',
  'stopping',
  'error',
])

// Backend process information
export const BackendProcessInfoSchema = z.object({
  status: BackendProcessStatusSchema,
  pid: z.number().optional(),
  uptime: z.number().optional(),
  lastError: z.string().optional(),
  restartCount: z.number(),
})

// Backend manager configuration
export const BackendManagerConfigSchema = z.object({
  host: z.string(),
  port: z.number(),
  apiKey: z.string().optional(),
  healthCheckUrl: z.string().optional(),
  startupTimeoutMs: z.number().optional(),
  healthCheckIntervalMs: z.number().optional(),
  maxRestartAttempts: z.number().optional(),
})

// Backend service status (legacy PM2-based)
export const BackendStatusSchema = z.object({
  api: z.object({
    running: z.boolean(),
    healthy: z.boolean(),
    port: z.number(),
    url: z.string(),
  }),
  discord: z.object({
    running: z.boolean(),
    healthy: z.boolean(),
  }),
  pm2: z.object({
    running: z.boolean(),
    processes: z.array(
      z.object({
        name: z.string(),
        status: z.string(),
        cpu: z.number(),
        memory: z.number(),
      })
    ),
    mode: z.enum(['pm2', 'direct']).optional(),
  }),
})

// Backend health check result
export const HealthCheckSchema = z.object({
  healthy: z.boolean(),
  timestamp: z.string(),
  services: z.object({
    api: z.boolean(),
    discord: z.boolean(),
    database: z.boolean(),
  }),
  error: z.string().optional(),
})

// Backend configuration
export const BackendConfigSchema = z.object({
  apiHost: z.string(),
  apiPort: z.number(),
  apiKey: z.string(),
  databaseUrl: z.string().optional(),
  sqlitePath: z.string().optional(),
  enableTracing: z.boolean(),
  logLevel: z.string(),
})

// Backend logs
export const BackendLogsSchema = z.object({
  service: z.enum(['api', 'discord', 'pm2', 'all']),
  lines: z.number().optional(),
  tail: z.boolean().optional(),
})

export const BackendLogResultSchema = z.object({
  service: z.string(),
  output: z.string(),
  error: z.string().optional(),
})

export type BackendProcessStatus = z.infer<typeof BackendProcessStatusSchema>
export type BackendProcessInfo = z.infer<typeof BackendProcessInfoSchema>
export type BackendManagerConfig = z.infer<typeof BackendManagerConfigSchema>
export type BackendStatus = z.infer<typeof BackendStatusSchema>
export type HealthCheck = z.infer<typeof HealthCheckSchema>
export type BackendConfig = z.infer<typeof BackendConfigSchema>
export type BackendLogs = z.infer<typeof BackendLogsSchema>
export type BackendLogResult = z.infer<typeof BackendLogResultSchema>
