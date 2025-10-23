# Electron + FastAPI Implementation Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│         Automagik Omni Desktop Application              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐          ┌──────────────────┐   │
│  │  Renderer        │          │  Main Process    │   │
│  │  (React UI)      │◄────────►│  (Node.js)       │   │
│  │                  │   IPC    │  Electron        │   │
│  │ Shadcn Components│          │                  │   │
│  │ useConveyor()    │          │ IPC Handlers     │   │
│  └──────────────────┘          └──────────────────┘   │
│           │                              │             │
│           │                              │ HTTP fetch  │
│           │                              │             │
│           └──────────────────┬───────────┘             │
│                              │                         │
│                    localhost:8000                      │
│                              │                         │
└──────────────────────────────┼─────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   FastAPI Backend   │
                    │   (Python)          │
                    │   localhost:8000    │
                    └─────────────────────┘
```

## Step-by-Step Implementation

### Phase 1: Base Setup (Day 1)

#### 1.1 Clone Boilerplate
```bash
git clone https://github.com/guasam/electron-react-app my-desktop-app
cd my-desktop-app
npm install
npm run dev
```

#### 1.2 Explore Conveyor System
- Read `/lib/conveyor/README.md`
- Check `/lib/conveyor/schemas/app-schema.ts` (example)
- Review `/lib/conveyor/api/app-api.ts` (pattern)
- Look at `/lib/conveyor/handlers/app-handler.ts` (implementation)

#### 1.3 Test Hot Reload
```bash
npm run dev
# Open app, edit a component in app/, see instant reload
```

### Phase 2: FastAPI Integration (Day 2-3)

#### 2.1 Create Backend Schema
**File: `lib/conveyor/schemas/backend-schema.ts`**

```typescript
import { z } from 'zod'

export const backendIpcSchema = {
  // Message operations
  'send-message': {
    args: z.tuple([
      z.object({
        chatId: z.string(),
        text: z.string(),
        channelId: z.string(), // whatsapp_123, discord_456
      }),
    ]),
    return: z.object({
      success: z.boolean(),
      messageId: z.string(),
      timestamp: z.string(),
      error: z.string().optional(),
    }),
  },

  // Chat operations
  'get-chats': {
    args: z.tuple([]),
    return: z.array(
      z.object({
        id: z.string(),
        name: z.string(),
        channelType: z.enum(['whatsapp', 'discord']),
        unreadCount: z.number(),
      })
    ),
  },

  'get-chat-messages': {
    args: z.tuple([
      z.object({
        chatId: z.string(),
        limit: z.number().default(50),
      }),
    ]),
    return: z.array(
      z.object({
        id: z.string(),
        text: z.string(),
        sender: z.string(),
        timestamp: z.string(),
        channelType: z.enum(['whatsapp', 'discord']),
      })
    ),
  },

  // Instance operations
  'get-instances': {
    args: z.tuple([]),
    return: z.array(
      z.object({
        id: z.string(),
        name: z.string(),
        platform: z.enum(['whatsapp', 'discord']),
        status: z.enum(['active', 'inactive', 'error']),
      })
    ),
  },
} as const
```

#### 2.2 Create Backend API Class
**File: `lib/conveyor/api/backend-api.ts`**

```typescript
import type { ElectronAPI } from '@electron-toolkit/preload'
import { ConveyorApi } from './shared'
import type { ChannelName, ChannelArgs, ChannelReturn } from '@/lib/conveyor/schemas'

export class BackendApi extends ConveyorApi {
  // Message methods
  sendMessage = (chatId: string, text: string, channelId: string) =>
    this.invoke('send-message', { chatId, text, channelId })

  // Chat methods
  getChats = () =>
    this.invoke('get-chats')

  getChatMessages = (chatId: string, limit?: number) =>
    this.invoke('get-chat-messages', { chatId, limit })

  // Instance methods
  getInstances = () =>
    this.invoke('get-instances')
}

// Export factory function
export const createBackendApi = (electronApi: ElectronAPI) => {
  return new BackendApi(electronApi)
}
```

#### 2.3 Create IPC Handlers
**File: `lib/conveyor/handlers/backend-handler.ts`**

```typescript
import { handle } from '@/lib/main/shared'

const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

export const registerBackendHandlers = () => {
  // Send message
  handle('send-message', async ({ chatId, text, channelId }) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chatId, text, channelId }),
      })

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Failed to send message:', error)
      return {
        success: false,
        messageId: '',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  })

  // Get chats
  handle('get-chats', async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/chats`)
      if (!response.ok) throw new Error('Failed to fetch chats')
      return await response.json()
    } catch (error) {
      console.error('Failed to get chats:', error)
      return []
    }
  })

  // Get chat messages
  handle('get-chat-messages', async ({ chatId, limit = 50 }) => {
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/chats/${chatId}/messages?limit=${limit}`
      )
      if (!response.ok) throw new Error('Failed to fetch messages')
      return await response.json()
    } catch (error) {
      console.error('Failed to get messages:', error)
      return []
    }
  })

  // Get instances
  handle('get-instances', async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/instances`)
      if (!response.ok) throw new Error('Failed to fetch instances')
      return await response.json()
    } catch (error) {
      console.error('Failed to get instances:', error)
      return []
    }
  })
}
```

#### 2.4 Register Handlers in Main Process
**File: `lib/main/app.ts` (or similar startup file)**

```typescript
import { registerAppHandlers } from '@/lib/conveyor/handlers/app-handler'
import { registerWindowHandlers } from '@/lib/conveyor/handlers/window-handler'
import { registerBackendHandlers } from '@/lib/conveyor/handlers/backend-handler'

export function setupIpcHandlers() {
  registerAppHandlers()
  registerWindowHandlers()
  registerBackendHandlers()  // Add this
}

// Call during app initialization
setupIpcHandlers()
```

### Phase 3: Backend Startup Integration (Day 3)

#### 3.1 Create Startup Script
**File: `lib/main/backend-launcher.ts`**

```typescript
import { spawn } from 'child_process'
import path from 'path'
import { app } from 'electron'

let backendProcess: any = null

export async function startBackend(): Promise<void> {
  if (backendProcess) return

  const isPackaged = app.isPackaged
  const backendScript = isPackaged
    ? path.join(process.resourcesPath, 'backend', 'main.py')
    : path.join(__dirname, '../../backend/main.py')

  console.log(`Starting backend from: ${backendScript}`)

  return new Promise((resolve, reject) => {
    try {
      backendProcess = spawn('python', [backendScript], {
        cwd: isPackaged
          ? path.join(process.resourcesPath, 'backend')
          : path.join(__dirname, '../../backend'),
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: process.platform !== 'win32',
      })

      backendProcess.stdout?.on('data', (data: Buffer) => {
        console.log(`[Backend] ${data}`)
      })

      backendProcess.stderr?.on('data', (data: Buffer) => {
        console.error(`[Backend Error] ${data}`)
      })

      // Give backend time to start
      setTimeout(() => resolve(), 2000)
    } catch (error) {
      console.error('Failed to start backend:', error)
      reject(error)
    }
  })
}

export function stopBackend(): void {
  if (backendProcess) {
    if (process.platform === 'win32') {
      backendProcess.kill()
    } else {
      process.kill(-backendProcess.pid)
    }
    backendProcess = null
  }
}
```

#### 3.2 Integrate into App Lifecycle
**File: `lib/main/app.ts` (update)**

```typescript
import { startBackend, stopBackend } from './backend-launcher'

// On app ready
app.on('ready', async () => {
  try {
    await startBackend()
    setupIpcHandlers()
    createWindow()
  } catch (error) {
    console.error('Failed to start app:', error)
    app.quit()
  }
})

// On app quit
app.on('before-quit', () => {
  stopBackend()
})
```

### Phase 4: Create UI Components (Day 3-4)

#### 4.1 Create Chat Component
**File: `app/components/chat/chat-view.tsx`**

```typescript
import { useEffect, useState } from 'react'
import { useConveyor } from '@/app/hooks/use-conveyor'
import { Button } from '@/app/components/ui/button'
import { Input } from '@/app/components/ui/input'

interface Message {
  id: string
  text: string
  sender: string
  timestamp: string
}

export function ChatView({ chatId }: { chatId: string }) {
  const { sendMessage, getChatMessages } = useConveyor('backend')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadMessages()
  }, [chatId])

  const loadMessages = async () => {
    setLoading(true)
    const msgs = await getChatMessages(chatId, 50)
    setMessages(msgs)
    setLoading(false)
  }

  const handleSend = async () => {
    if (!input.trim()) return

    setLoading(true)
    const result = await sendMessage(chatId, input, 'whatsapp_default')

    if (result.success) {
      setInput('')
      await loadMessages()
    } else {
      console.error('Failed to send:', result.error)
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className="mb-2 p-2 bg-gray-100 rounded-lg"
          >
            <div className="text-sm font-semibold">{msg.sender}</div>
            <div>{msg.text}</div>
            <div className="text-xs text-gray-500">{msg.timestamp}</div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t space-x-2 flex">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
          disabled={loading}
        />
        <Button onClick={handleSend} disabled={loading}>
          Send
        </Button>
      </div>
    </div>
  )
}
```

### Phase 5: GitHub Actions (Day 4)

#### 5.1 Copy Multi-Platform Build Workflow
Copy `.github/workflows/compile-and-test.yml` from vite-electron-builder and adapt:

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest, ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
          cache: npm
      
      - name: Install dependencies
        run: npm install
      
      - name: Build
        run: npm run build:win || npm run build:linux || npm run build:mac
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.os }}-build
          path: dist
```

#### 5.2 Add Auto-Update Configuration
Copy `/packages/main/src/modules/AutoUpdater.ts` from vite-electron-builder and integrate into ERA.

### Phase 6: Testing (Day 4-5)

#### 6.1 Test Locally
```bash
# Terminal 1: FastAPI
cd backend
python main.py

# Terminal 2: Electron
npm run dev
```

#### 6.2 Test Built App
```bash
npm run build:win  # or build:mac, build:linux
```

#### 6.3 Test Multi-Platform with GitHub Actions
- Push to GitHub
- Watch workflows run on all platforms
- Download artifacts

---

## File Structure After Implementation

```
my-desktop-app/
├── app/
│   ├── components/
│   │   ├── chat/
│   │   │   └── chat-view.tsx          (NEW)
│   │   ├── ui/
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── lib/
│   ├── conveyor/
│   │   ├── schemas/
│   │   │   ├── app-schema.ts
│   │   │   ├── window-schema.ts
│   │   │   └── backend-schema.ts      (NEW)
│   │   ├── api/
│   │   │   ├── app-api.ts
│   │   │   ├── window-api.ts
│   │   │   └── backend-api.ts         (NEW)
│   │   ├── handlers/
│   │   │   ├── app-handler.ts
│   │   │   ├── window-handler.ts
│   │   │   └── backend-handler.ts     (NEW)
│   │   └── ...
│   ├── main/
│   │   ├── app.ts                     (UPDATED)
│   │   ├── backend-launcher.ts        (NEW)
│   │   └── ...
│   └── ...
├── .github/
│   └── workflows/
│       ├── compile-and-test.yml       (NEW)
│       ├── deploy.yml                 (NEW)
│       └── ...
├── backend/                            (Symlink or copy your FastAPI)
│   └── main.py
└── package.json
```

---

## Troubleshooting

### Issue: Backend won't start
```bash
# Check Python path
which python3
# Update backend-launcher.ts with correct path
```

### Issue: IPC channel not found
```bash
# Ensure registerBackendHandlers() is called
# Check lib/main/app.ts setupIpcHandlers()
```

### Issue: GitHub Actions fails on macOS
```yaml
# Add notarization secrets
# See electron-react-boilerplate for reference
```

### Issue: Auto-update not working
```bash
# Check GitHub releases are created
# Verify electron-builder config
# Test with VITE_DISTRIBUTION_CHANNEL env var
```

---

## Production Checklist

- [ ] Backend runs stable for 24+ hours
- [ ] Messages send/receive reliably
- [ ] UI components render properly
- [ ] Hot reload works during development
- [ ] Built app works on Windows/macOS/Linux
- [ ] Auto-updates download and install
- [ ] GitHub Actions passes on all platforms
- [ ] Error handling implemented
- [ ] Logging configured
- [ ] Performance acceptable (< 1s first launch)
- [ ] Icons and branding applied
- [ ] Installer tested on each platform

---

## Next: Advanced Features

Once basic integration works:

1. **Real-time updates** - WebSocket from FastAPI → Electron
2. **Message persistence** - SQLite in Electron for offline support
3. **Multi-window** - Support multiple chats
4. **Settings** - Store user preferences
5. **Notifications** - Native OS notifications on new messages
6. **Tray menu** - Minimize to system tray

