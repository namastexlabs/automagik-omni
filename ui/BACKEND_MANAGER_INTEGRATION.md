# BackendManager Integration Guide

## Overview

The `BackendManager` class manages the Python backend subprocess lifecycle for the Electron desktop application. It provides a clean alternative to PM2-based process management, with direct subprocess control, health monitoring, and automatic restart capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Main Process                     │
│                                                               │
│  ┌────────────────┐         ┌──────────────────┐            │
│  │  main.ts       │────────▶│ backend-handler  │            │
│  │  (startup)     │         │  (IPC handlers)  │            │
│  └────────────────┘         └────────┬─────────┘            │
│                                      │                        │
│                                      ▼                        │
│                          ┌───────────────────────┐           │
│                          │  BackendManager       │           │
│                          │  - subprocess spawn   │           │
│                          │  - health checks      │           │
│                          │  - auto-restart       │           │
│                          │  - graceful shutdown  │           │
│                          └───────────┬───────────┘           │
│                                      │                        │
└──────────────────────────────────────┼────────────────────────┘
                                       │ spawn
                                       ▼
                        ┌──────────────────────────────┐
                        │  Python Backend Process      │
                        │  (Automagik Omni API)        │
                        │  http://localhost:8882       │
                        └──────────────────────────────┘
```

## File Structure

```
ui/
├── lib/
│   ├── main/
│   │   ├── main.ts                    # Main entry point (startup integration)
│   │   ├── backend-manager.ts         # NEW: BackendManager class
│   │   └── backend-monitor.ts         # Legacy PM2-based monitor
│   └── conveyor/
│       ├── handlers/
│       │   └── backend-handler.ts     # IPC handlers (updated)
│       └── schemas/
│           └── backend-schema.ts      # TypeScript types (updated)
```

## Key Features

### 1. **Development vs Production Paths**

- **Development**: Uses `uv run python -m src.cli.main_cli start --host localhost --port 8882`
- **Production**: Uses bundled executable from `resources/backend/automagik-omni[.exe]`

### 2. **Health Monitoring**

- Polls `/health` endpoint every 10 seconds
- 30-second startup timeout
- Automatic process restart on crash (max 3 attempts)

### 3. **Process Management**

- Graceful SIGTERM shutdown
- Force SIGKILL after 10s timeout
- Stdout/stderr logging
- Process status tracking (stopped, starting, running, stopping, error)

### 4. **Environment Variables**

The manager automatically configures:
- `AUTOMAGIK_OMNI_API_HOST`
- `AUTOMAGIK_OMNI_API_PORT`
- `AUTOMAGIK_OMNI_API_KEY`
- `PYTHONUNBUFFERED=1` (ensures real-time logging)

## Usage

### Basic Usage (from Renderer Process)

```typescript
// Using IPC from renderer process
import { useConveyor } from '@/app/hooks/use-conveyor'

function BackendControl() {
  const { invoke } = useConveyor()

  const startBackend = async () => {
    const result = await invoke('backend:manager:start')
    console.log(result) // { success: true, message: "Backend started successfully" }
  }

  const stopBackend = async () => {
    const result = await invoke('backend:manager:stop')
    console.log(result) // { success: true, message: "Backend stopped successfully" }
  }

  const restartBackend = async () => {
    const result = await invoke('backend:manager:restart')
    console.log(result)
  }

  const getStatus = async () => {
    const status = await invoke('backend:manager:status')
    console.log(status)
    // {
    //   status: 'running',
    //   pid: 12345,
    //   uptime: 60000,
    //   restartCount: 0
    // }
  }

  return (
    <div>
      <button onClick={startBackend}>Start</button>
      <button onClick={stopBackend}>Stop</button>
      <button onClick={restartBackend}>Restart</button>
      <button onClick={getStatus}>Status</button>
    </div>
  )
}
```

### Advanced Usage (Main Process)

```typescript
import { BackendManager, BackendProcessStatus } from '@/lib/main/backend-manager'

// Create manager instance
const manager = new BackendManager({
  host: 'localhost',
  port: 8882,
  apiKey: 'your-api-key',
  healthCheckUrl: 'http://localhost:8882/health',
  startupTimeoutMs: 30000,
  healthCheckIntervalMs: 10000,
  maxRestartAttempts: 3
})

// Register event listeners
manager.onStatusChangeListener((status: BackendProcessStatus) => {
  console.log('Backend status changed:', status)
  // 'stopped' | 'starting' | 'running' | 'stopping' | 'error'
})

manager.onLogListener((type: 'stdout' | 'stderr', data: string) => {
  if (type === 'stdout') {
    console.log('[Backend]', data)
  } else {
    console.error('[Backend Error]', data)
  }
})

// Start backend
await manager.start()

// Get process info
const info = manager.getStatus()
console.log(`Backend is ${info.status}, PID: ${info.pid}`)

// Stop backend
await manager.stop()
```

### Integration in main.ts (Already Done)

```typescript
import { startBackendOnStartup, cleanupBackendMonitor } from '@/lib/conveyor/handlers/backend-handler'

app.whenReady().then(async () => {
  try {
    // Start backend before creating window
    console.log('Starting backend...')
    await startBackendOnStartup()
    console.log('Backend started successfully')
  } catch (error) {
    console.error('Failed to start backend:', error)
    // Continue anyway - user can manually start backend from UI
  }

  // Create app window
  createAppWindow()
})

app.on('window-all-closed', async () => {
  // Cleanup before quitting
  await cleanupBackendMonitor()

  if (process.platform !== 'darwin') {
    app.quit()
  }
})
```

## IPC Handlers

### BackendManager Handlers (New)

| IPC Channel                | Description                      | Returns                                    |
|----------------------------|----------------------------------|--------------------------------------------|
| `backend:manager:start`    | Start backend subprocess         | `{ success: boolean, message: string }`    |
| `backend:manager:stop`     | Stop backend subprocess          | `{ success: boolean, message: string }`    |
| `backend:manager:restart`  | Restart backend subprocess       | `{ success: boolean, message: string }`    |
| `backend:manager:status`   | Get backend process info         | `BackendProcessInfo`                       |

### BackendMonitor Handlers (Legacy PM2)

| IPC Channel              | Description                      | Returns                                    |
|--------------------------|----------------------------------|--------------------------------------------|
| `backend:start`          | Start via PM2                    | `{ success: boolean, message: string }`    |
| `backend:stop`           | Stop via PM2                     | `{ success: boolean, message: string }`    |
| `backend:restart`        | Restart via PM2                  | `{ success: boolean, message: string }`    |
| `backend:status`         | Get PM2 status                   | `BackendStatus`                            |
| `backend:health`         | Health check                     | `HealthCheck`                              |
| `backend:logs`           | Get PM2 logs                     | `BackendLogResult`                         |

## TypeScript Types

```typescript
// Backend process status
export enum BackendProcessStatus {
  STOPPED = 'stopped',
  STARTING = 'starting',
  RUNNING = 'running',
  STOPPING = 'stopping',
  ERROR = 'error',
}

// Backend manager configuration
export interface BackendManagerConfig {
  host: string
  port: number
  apiKey?: string
  healthCheckUrl?: string
  startupTimeoutMs?: number
  healthCheckIntervalMs?: number
  maxRestartAttempts?: number
}

// Backend process information
export interface BackendProcessInfo {
  status: BackendProcessStatus
  pid?: number
  uptime?: number
  lastError?: string
  restartCount: number
}
```

## Error Handling

### Common Failure Modes

#### 1. **Backend Executable Not Found (Production)**

```typescript
Error: Backend executable not found at: /path/to/resources/backend/automagik-omni
```

**Solution**: Ensure backend is properly bundled during electron-builder packaging.

#### 2. **Health Check Timeout**

```typescript
Error: Backend did not become healthy within 30000ms
```

**Solutions**:
- Check if port 8882 is already in use
- Verify backend dependencies are installed
- Check backend logs for startup errors
- Increase `startupTimeoutMs` if needed

#### 3. **Process Exit Before Healthy**

```typescript
Error: Backend process exited before becoming healthy
```

**Solutions**:
- Check stderr logs for Python errors
- Verify database is accessible
- Ensure .env configuration is correct

#### 4. **Max Restart Attempts Reached**

```
Max restart attempts reached, giving up
```

**Solution**: Backend is crashing repeatedly. Check logs and fix underlying issue.

## Splash Screen Integration (Optional)

```typescript
// In main.ts
import { BrowserWindow } from 'electron'

let splashWindow: BrowserWindow | null = null

app.whenReady().then(async () => {
  // Show splash screen
  splashWindow = new BrowserWindow({
    width: 400,
    height: 300,
    frame: false,
    transparent: true,
    alwaysOnTop: true
  })
  splashWindow.loadFile('splash.html')

  try {
    // Start backend with splash visible
    await startBackendOnStartup()
  } catch (error) {
    console.error('Failed to start backend:', error)
  }

  // Hide splash and show main window
  splashWindow.close()
  splashWindow = null
  createAppWindow()
})
```

## Production Bundling

### electron-builder Configuration

Update `electron-builder.yml` to bundle the backend executable:

```yaml
files:
  - '!**/.vscode/*'
  - '!src/*'
  # ... other exclusions

extraResources:
  - from: '../dist/backend/'
    to: 'backend/'
    filter:
      - '**/*'

asarUnpack:
  - resources/**
```

### Build Backend Executable

```bash
# From project root (not ui/)
cd /home/cezar/automagik/automagik-omni

# Create standalone executable using PyInstaller or similar
uv run pyinstaller \
  --name automagik-omni \
  --onefile \
  --add-data "src:src" \
  src/cli/main_cli.py

# Copy to ui build resources
mkdir -p ui/dist/backend
cp dist/automagik-omni ui/dist/backend/
```

## Testing

### Manual Testing

```bash
# From ui directory
cd /home/cezar/automagik/automagik-omni/ui

# Run in development mode
pnpm dev

# Check logs
# Backend logs will appear in Electron console output
```

### Verify Backend is Running

```bash
# In another terminal
curl http://localhost:8882/health

# Expected response:
# {"status":"ok","database":"ok"}
```

## Migration from BackendMonitor (PM2) to BackendManager

If you want to fully migrate from PM2-based `BackendMonitor` to subprocess-based `BackendManager`:

1. **Update all IPC calls** in renderer components:
   ```typescript
   // Old (PM2)
   await invoke('backend:start')

   // New (subprocess)
   await invoke('backend:manager:start')
   ```

2. **Remove PM2 handlers** from `backend-handler.ts` if no longer needed

3. **Update electron-builder** to bundle Python executable

4. **Test thoroughly** in both development and production modes

## Troubleshooting

### Enable Verbose Logging

```typescript
// In backend-manager.ts constructor
constructor(config: BackendManagerConfig) {
  // Add verbose logging
  this.onLogListener((type, data) => {
    console.log(`[Backend ${type}]:`, data)
  })

  this.onStatusChangeListener((status) => {
    console.log('[Backend Status]:', status)
  })
}
```

### Check Process Status

```typescript
const info = await invoke('backend:manager:status')
console.log('Backend status:', info)
// {
//   status: 'running',
//   pid: 12345,
//   uptime: 60000,
//   restartCount: 0
// }
```

### Monitor Health Checks

The manager polls `/health` every 10 seconds. Check console for warnings:

```
Backend health check failed
```

## Performance Considerations

- **Startup Time**: Typically 2-5 seconds in development, 1-2 seconds in production
- **Memory**: Backend process ~100-200MB depending on configuration
- **CPU**: Minimal when idle, spikes during API requests
- **Health Checks**: Negligible overhead (1 HTTP request every 10 seconds)

## Security Notes

1. **API Key**: Stored in `.env` file, never hardcoded
2. **Process Isolation**: Backend runs as separate subprocess with own memory space
3. **Graceful Shutdown**: SIGTERM allows backend to close connections properly
4. **Health Endpoint**: Publicly accessible on localhost only

## Future Enhancements

- [ ] Add backend update mechanism
- [ ] Implement backend version checking
- [ ] Add metrics collection (CPU, memory, request count)
- [ ] Support for multiple backend instances
- [ ] Add backend configuration UI in renderer
- [ ] Implement backend log viewer in UI
- [ ] Add backend performance monitoring dashboard

---

**Last Updated**: 2025-10-22
**Author**: Automagik Team
**Version**: 1.0.0
