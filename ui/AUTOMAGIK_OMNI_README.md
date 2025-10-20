# Automagik Omni Desktop UI

Native cross-platform desktop application for managing Automagik Omni messaging instances.

## Technology Stack

- **Framework**: Electron 37.7.0
- **UI Library**: React 19.2.0
- **Build Tool**: Vite 7.1.11 with electron-vite
- **Styling**: Tailwind CSS 4.1.15
- **Components**: Shadcn UI (50+ components)
- **Type Safety**: TypeScript 5.9.3 + Zod 4.1.12
- **IPC**: Conveyor (type-safe with runtime validation)

## Features

### Phase 1: Foundation ✅

- ✅ Backend monitoring with PM2 integration
- ✅ Health check system for FastAPI, Discord, and Database
- ✅ Type-safe IPC communication using Conveyor
- ✅ Dashboard with real-time status updates
- ✅ Service control (start/stop/restart)
- ✅ Electron main process integration

### Planned Features

- Instance management (create, edit, delete)
- Message composer with all message types support
- Message trace viewer with analytics
- Contact and chat management
- Configuration editor
- Log viewer with real-time tailing
- Auto-update system
- System tray integration

## Project Structure

```
ui/
├── app/                      # React application
│   ├── pages/                # Application pages
│   │   └── Dashboard.tsx     # Main dashboard
│   ├── components/           # Reusable components
│   │   └── ui/               # Shadcn UI components
│   ├── hooks/                # Custom React hooks
│   └── styles/               # Global styles
├── lib/                      # Core libraries
│   ├── conveyor/             # IPC system
│   │   ├── api/              # Renderer API clients
│   │   │   ├── app-api.ts
│   │   │   ├── window-api.ts
│   │   │   └── backend-api.ts
│   │   ├── handlers/         # Main process handlers
│   │   │   ├── app-handler.ts
│   │   │   ├── window-handler.ts
│   │   │   └── backend-handler.ts
│   │   └── schemas/          # Zod validation schemas
│   │       ├── app-schema.ts
│   │       ├── window-schema.ts
│   │       ├── backend-schema.ts
│   │       └── backend-ipc-schema.ts
│   ├── main/                 # Main process
│   │   ├── main.ts           # Entry point
│   │   ├── app.ts            # Window creation
│   │   ├── backend-monitor.ts # PM2 & health monitoring
│   │   └── shared.ts         # IPC utilities
│   └── preload/              # Preload scripts
└── resources/                # Application resources

Backend (Python):
../src/                       # FastAPI backend
../Makefile                   # Commands: make dev, make stop, make logs
```

## Development

### Prerequisites

- Node.js 20+
- pnpm 10+
- Python 3.11+ (for backend)
- PM2 (for process management)

### Setup

```bash
# Install dependencies
pnpm install

# Start development mode (with hot reload)
pnpm run dev
```

### Available Scripts

```bash
pnpm run dev          # Start Electron + Vite dev server with HMR
pnpm run start        # Preview production build
pnpm run lint         # Run ESLint with auto-fix
pnpm run format       # Format code with Prettier
```

### Build Commands

```bash
# Build Vite app
pnpm run vite:build:app

# Build for specific platforms
pnpm run build:win     # Windows
pnpm run build:mac     # macOS
pnpm run build:linux   # Linux

# Build unpacked (for testing)
pnpm run build:unpack
```

## Backend Integration

The UI integrates with Automagik Omni backend services through:

### Backend Monitor

The `BackendMonitor` class (`lib/main/backend-monitor.ts`) manages:

- **PM2 Process Management**: Start/stop/restart services via `make dev` and `make stop`
- **Health Checks**: Periodic polling of API, Discord bot, and database
- **Configuration**: Environment variable management
- **Log Retrieval**: Access to service logs

### IPC Communication

Type-safe communication between main and renderer processes:

```typescript
// Renderer process (React components)
import { useConveyor } from '@/app/hooks/use-conveyor'

const { backend } = useConveyor()

// Get backend status
const status = await backend.status()

// Start backend services
const result = await backend.start()

// Health check
const health = await backend.health()

// Get logs
const logs = await backend.getLogs('api', 100, false)
```

### Main Process Handlers

```typescript
// lib/conveyor/handlers/backend-handler.ts
registerBackendHandlers()

// Available IPC channels:
// - backend:status
// - backend:start
// - backend:stop
// - backend:restart
// - backend:health
// - backend:config:get
// - backend:config:set
// - backend:logs
```

## Conveyor IPC System

Conveyor provides type-safe IPC with runtime validation:

### Schema Definition

```typescript
// lib/conveyor/schemas/backend-ipc-schema.ts
export const backendIpcSchema = {
  'backend:status': {
    args: z.tuple([]),
    return: BackendStatusSchema,
  },
  // ... more channels
}
```

### Handler Registration

```typescript
// lib/conveyor/handlers/backend-handler.ts
handle('backend:status', async () => {
  return await getMonitor().getStatus()
})
```

### API Client

```typescript
// lib/conveyor/api/backend-api.ts
export class BackendApi extends ConveyorApi {
  status = (): Promise<BackendStatus> => {
    return this.invoke('backend:status')
  }
}
```

## Configuration

Backend configuration is loaded from environment variables:

- `AUTOMAGIK_OMNI_API_HOST`: API host (default: localhost)
- `AUTOMAGIK_OMNI_API_PORT`: API port (default: 8000)
- `AUTOMAGIK_OMNI_API_KEY`: API authentication key
- `AUTOMAGIK_OMNI_DATABASE_URL`: Database connection string
- `AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH`: SQLite database path
- `AUTOMAGIK_OMNI_ENABLE_TRACING`: Enable telemetry (true/false)
- `LOG_LEVEL`: Logging level (default: INFO)

## Troubleshooting

### Backend Not Starting

1. Ensure PM2 is installed: `npm install -g pm2`
2. Check backend is not already running: `make stop` in parent directory
3. Verify Python environment: `uv sync` in parent directory
4. Check logs: `make logs` or use UI log viewer

### Build Errors

1. Clear build cache: `rm -rf node_modules dist out`
2. Reinstall dependencies: `pnpm install`
3. Rebuild native modules: `pnpm run postinstall`

### TypeScript Errors

1. Check tsconfig.json paths are correct
2. Verify all schemas are exported from `lib/conveyor/schemas/index.ts`
3. Run type check: `tsc --noEmit`

## Contributing

1. Create feature branch from `dev`
2. Follow existing code patterns (Conveyor IPC, React hooks)
3. Run lint before committing: `pnpm run lint`
4. Test on all platforms when possible
5. Update documentation for new features

## License

See parent repository LICENSE file.
