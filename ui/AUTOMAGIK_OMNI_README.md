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

### Phase 1: Foundation ✅ COMPLETE

**Backend Integration:**
- ✅ Complete FastAPI client with HTTP communication
- ✅ Backend monitoring with PM2 process management
- ✅ Health check system for FastAPI, Discord bot, and Database
- ✅ Auto-configuration from parent `.env` file
- ✅ Support for both PM2-managed and direct processes
- ✅ Service control (start/stop/restart via PM2)

**Type-Safe Communication:**
- ✅ Conveyor IPC system with Zod validation
- ✅ Full TypeScript types end-to-end
- ✅ Runtime validation on IPC boundaries
- ✅ Compile-time type checking

**Dashboard UI:**
- ✅ Real-time status cards (API, Discord, PM2)
- ✅ System health monitoring with 10s polling
- ✅ Process manager with status display
- ✅ Responsive layout with Tailwind CSS
- ✅ Backend control buttons with proper state management
- ✅ Dismissible info banners
- ✅ Clean app lifecycle (proper quit handling)

**Omni API Integration:**
- ✅ Complete REST client for all backend endpoints
- ✅ Instance management (CRUD operations)
- ✅ Contacts & Chats (paginated listing)
- ✅ Messages (text, media, audio, reactions)
- ✅ Traces (list, filter, analytics)
- ✅ Connection management (QR codes, status)

### Phase 2: In Progress

- [ ] Navigation layout with routing
- [ ] Instances page (CRUD, QR codes, status)
- [ ] Messages page (composer, history)
- [ ] Contacts page (search, details)
- [ ] Chats page (list, filters)
- [ ] Traces page (analytics, debugging)

### Phase 3: Planned

- [ ] Configuration editor
- [ ] Log viewer with real-time tailing
- [ ] Auto-update system
- [ ] System tray integration

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

### Environment Variables

Configuration is automatically loaded from the parent directory's `.env` file:

- `AUTOMAGIK_OMNI_API_HOST`: API host (default: localhost)
- `AUTOMAGIK_OMNI_API_PORT`: API port (default: 8882)
- `AUTOMAGIK_OMNI_API_KEY`: API authentication key
- `AUTOMAGIK_OMNI_DATABASE_URL`: Database connection string
- `AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH`: SQLite database path
- `AUTOMAGIK_OMNI_ENABLE_TRACING`: Enable telemetry (true/false)
- `LOG_LEVEL`: Logging level (default: INFO)

### Configuration Loading

The UI automatically:
1. Reads `../.env` file from parent directory
2. Parses key=value pairs (handles quotes)
3. Converts `0.0.0.0` → `localhost` for client requests
4. Initializes Omni API client with URL and key
5. Priority: Environment variables > .env file > defaults

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

## Implementation Details

### Phase 1 Development Summary

**Total Commits**: 8
**Development Time**: Day 1
**Branch**: `feature/electron-desktop-ui`

#### Commit History

1. **`03a29ae` - Phase 1 Foundation**
   - Cloned electron-react-app boilerplate
   - Created BackendMonitor class for PM2 management
   - Implemented health check system
   - Built Dashboard with real-time polling
   - Integrated backend IPC handlers

2. **`84d260a` - .env Loading Fix**
   - Added .env file parser in BackendMonitor
   - Fixed port detection (8882 instead of 8000)
   - Changed stop command: `make stop` → `make stop-local`
   - Added configuration priority system

3. **`fa44d6d` - Non-PM2 Process Detection**
   - Enhanced backend detection for direct processes
   - Updated Dashboard UI to show process type
   - Added info banner for non-PM2 processes
   - Improved button state logic

4. **`247befb` - Complete Omni API Integration**
   - Created OmniApiClient (HTTP layer)
   - Implemented all Omni IPC schemas with Zod
   - Built omni-handler for main process
   - Created OmniApi for renderer process
   - Integrated into main app initialization

5. **`49587e8` - PM2 Startup Delay & Layout Fix**
   - Added 2s delay after start for PM2 spawn
   - Fixed horizontal scroll from info banner
   - Changed container to `h-screen overflow-auto`
   - Added `max-w-full` and `break-words`

6. **`6b68057` - Backend Controls & App Cleanup**
   - Added × dismiss button to info banner
   - Fixed Stop/Restart button enabling logic
   - Removed blocking `before-quit` handler
   - Moved cleanup to `window-all-closed`

7. **`4ce8c88` - PM2 Start Command Fix**
   - Changed `make dev` → `make start-local`
   - Fixed root cause of disabled buttons
   - Now creates actual PM2 processes
   - Consistent with `make stop-local`

8. **`f37bba2` - Layout Improvements**
   - Stripped 'automagik-omni-' prefix from names
   - Added monospace font for process names
   - Fixed card grid with equal heights
   - Improved text truncation

### Key Technical Decisions

#### 1. Why Conveyor IPC?
- Type-safe IPC with Zod validation
- Runtime validation prevents invalid data
- Matches Pydantic philosophy from backend
- Auto-completion in IDE

#### 2. Why PM2 Over Direct Process?
- Process management (start/stop/restart)
- Auto-restart on crash
- Resource monitoring (CPU/memory)
- Log management
- Production-ready

#### 3. Why Custom .env Parser?
- No dependency on dotenv package
- Full control over parsing logic
- Handles edge cases (quotes, comments)
- Works in both dev and production

#### 4. Why 2-Second Delay After Start?
- PM2 takes time to spawn processes
- Immediate check returns empty list
- Health check needs running processes
- Better UX than instant "failed" message

### Architecture Patterns

```
┌─────────────────────────────────────────────────────┐
│                  Renderer Process                    │
│  ┌────────────────────────────────────────────────┐ │
│  │  React Components (Dashboard.tsx)              │ │
│  │  • useState for local state                    │ │
│  │  • useEffect for polling (10s interval)        │ │
│  │  • Event handlers for user actions             │ │
│  └────────────────────────────────────────────────┘ │
│                      ↓                               │
│  ┌────────────────────────────────────────────────┐ │
│  │  useConveyor Hook                               │ │
│  │  • Provides typed API clients                  │ │
│  │  • backend, omni, app, window                  │ │
│  └────────────────────────────────────────────────┘ │
│                      ↓                               │
│  ┌────────────────────────────────────────────────┐ │
│  │  API Clients (conveyor/api/)                   │ │
│  │  • BackendApi, OmniApi                         │ │
│  │  • Type-safe method calls                      │ │
│  │  • Returns Promise<T>                          │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                       ↓ IPC (contextBridge)
┌─────────────────────────────────────────────────────┐
│                   Main Process                       │
│  ┌────────────────────────────────────────────────┐ │
│  │  IPC Handlers (conveyor/handlers/)             │ │
│  │  • backend-handler, omni-handler               │ │
│  │  • Zod validation on boundaries                │ │
│  │  • handle() wrapper for type safety            │ │
│  └────────────────────────────────────────────────┘ │
│                      ↓                               │
│  ┌────────────────────────────────────────────────┐ │
│  │  Business Logic                                 │ │
│  │  • BackendMonitor (PM2, health)                │ │
│  │  • OmniApiClient (HTTP to FastAPI)             │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                       ↓ HTTP
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                │
│  • Instance management                              │
│  • Message routing                                  │
│  • Contact/Chat queries                             │
│  • Trace management                                 │
└─────────────────────────────────────────────────────┘
```

### Lessons Learned

1. **Always Use PM2 for Managed Processes**
   - Direct processes can't be controlled programmatically
   - PM2 provides consistent interface
   - Lesson: Start with process manager from day 1

2. **Add Delays for Async Operations**
   - PM2 spawn isn't instant
   - Immediate checks give false negatives
   - Lesson: Always wait for async operations to complete

3. **Parse .env Carefully**
   - Handle quotes, comments, multi-line
   - Don't assume clean input
   - Lesson: Test with real .env files

4. **Test Layout on Real Content**
   - Long process names broke layout
   - Needed real PM2 processes to see issue
   - Lesson: Use realistic test data

## Contributing

1. Create feature branch from `dev`
2. Follow existing code patterns (Conveyor IPC, React hooks)
3. Run lint before committing: `pnpm run lint`
4. Test on all platforms when possible
5. Update documentation for new features

## License

See parent repository LICENSE file.
