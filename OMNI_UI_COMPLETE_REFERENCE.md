# Automagik Omni - Complete UI & API Reference

**Version:** 1.0.0
**Generated:** 2025-11-08
**Status:** Production-Ready (95%+ complete)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Quick Start for Frontend Developers](#quick-start-for-frontend-developers)
3. [Desktop Application Features](#desktop-application-features)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [TypeScript Type Definitions](#typescript-type-definitions)
6. [Mock Data & Testing](#mock-data--testing)
7. [Known Issues & Workarounds](#known-issues--workarounds)
8. [Architecture & Design Patterns](#architecture--design-patterns)
9. [Production Deployment](#production-deployment)

---

## Executive Summary

### What is Automagik Omni?

Automagik Omni is a **multi-tenant messaging orchestration platform** that unifies WhatsApp and Discord communication channels through a single REST API. The platform consists of:

- **FastAPI Backend** (Python) - REST API server on port 8882
- **Evolution API** - WhatsApp Web integration via Baileys (Node.js)
- **Electron Desktop App** - Complete management UI for Windows/macOS/Linux
- **Discord Integration** - Native Discord bot support

### Key Capabilities

✅ **Multi-Channel Support**: WhatsApp + Discord (extensible to other channels)
✅ **Unified API**: Single interface for contacts, chats, messages across channels
✅ **Message Tracing**: Full payload logging and analytics
✅ **Access Control**: Phone number allow/block rules (global + per-instance)
✅ **Desktop Management**: Electron app with process management
✅ **Type Safety**: Complete TypeScript types + Zod runtime validation

### Current Status

| Category | Completeness | Notes |
|----------|--------------|-------|
| **Core API** | 100% | All 32 endpoints implemented |
| **Desktop UI** | 95% | All pages functional, minor polish needed |
| **Process Management** | 100% | Backend + Evolution API lifecycle |
| **Type Safety** | 100% | Full TypeScript + Zod validation |
| **Documentation** | 100% | API guide, mock data, this reference |
| **Production Readiness** | 95% | Ready after merge to `dev` branch |

---

## Quick Start for Frontend Developers

### 1. Setup

```bash
# Clone the repository
git clone https://github.com/namastexlabs/automagik-omni.git
cd automagik-omni

# API Base URL
BASE_URL=http://localhost:8882

# Get your API key (desktop app generates this automatically)
# Windows: C:\Users\<user>\AppData\Roaming\Omni\evolution-api-key.txt
# macOS: ~/Library/Application Support/Omni/evolution-api-key.txt
# Linux: ~/.config/Omni/evolution-api-key.txt
```

### 2. Authentication

All API requests require the `x-api-key` header:

```typescript
const API_KEY = 'your-api-key-here'

fetch('http://localhost:8882/api/v1/instances', {
  headers: {
    'x-api-key': API_KEY,
    'Content-Type': 'application/json'
  }
})
```

### 3. Basic Example - List Instances

```typescript
interface Instance {
  id: number
  name: string
  channel_type: 'whatsapp' | 'discord'
  status: 'connected' | 'disconnected' | 'connecting' | 'error'
  is_active: boolean
  // ... see full type definitions below
}

async function listInstances(): Promise<Instance[]> {
  const response = await fetch('http://localhost:8882/api/v1/instances?include_status=true', {
    headers: { 'x-api-key': API_KEY }
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`)
  }

  return response.json()
}
```

### 4. Send a Message

```typescript
interface SendTextRequest {
  phone_number: string  // E.164 format: +5511999999999
  text: string
  quoted_message_id?: string
}

async function sendText(instanceName: string, message: SendTextRequest) {
  const response = await fetch(
    `http://localhost:8882/api/v1/instance/${instanceName}/send-text`,
    {
      method: 'POST',
      headers: {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(message)
    }
  )

  return response.json()
}

// Usage
await sendText('production-whatsapp', {
  phone_number: '+5511999999999',
  text: 'Hello from Omni!'
})
```

### 5. Mock Data Available

See `OMNI_MOCK_DATA.json` for complete PII-safe test data including:
- 4 sample instances (2 WhatsApp, 1 Discord, 1 inactive)
- 7 contacts (WhatsApp + Discord)
- 6 chats (direct + group)
- 5 messages (text, image, document)
- 5 traces with analytics
- 4 access rules

---

## Desktop Application Features

### Application Shell

**Custom Window Management:**
- Frameless Electron window (Windows 10/11 style)
- Custom titlebar with minimize/maximize/close
- Draggable window region
- 1400x900 default size, centered positioning
- Process naming for Windows Task Manager ("Omni")

**Backend Process Management:**
- Python FastAPI subprocess start/stop/restart
- Auto-restart on crash (max 3 attempts)
- Port conflict detection and cleanup (port 8882)
- Graceful shutdown (SIGTERM → SIGKILL fallback, 2s wait)
- Persistent SQLite database in user AppData

**Evolution API Management:**
- Bundled Node.js runtime for WhatsApp integration
- Start/stop/restart with socket health probes
- Auto-generated API key persistence
- SQLite database with Prisma migrations
- Port 8080 conflict detection
- Database corruption auto-recovery

### Dashboard (`/`)

**File:** `ui/app/pages/Dashboard.tsx`

**Features:**
- **Service Status Cards**: FastAPI backend, Discord bot, Evolution API
- **Health Monitoring**: Real-time status with 10-second auto-refresh
- **Process Manager Status**: Shows PM2 or Direct mode, running processes
- **Backend Controls**: Start/Stop/Restart buttons with 2-3s delays for PM2
- **Evolution API Controls**: Start/Stop/Restart with socket probes
- **API Key Management**: Show/hide/copy Evolution API key (masked by default)
- **Error Banners**: Color-coded (red=backend, blue=Evolution)
- **Uptime Display**: Real-time Evolution API uptime in minutes

**State Management:**
```typescript
interface DashboardState {
  status: BackendStatus  // api, discord, pm2
  health: HealthCheck    // services, timestamp
  evolutionStatus: EvolutionProcessInfo  // status, port, apiKey, uptime
  error: string | null
  evolutionError: string | null
}
```

### Instances Management (`/instances`)

**File:** `ui/app/pages/Instances.tsx`

**Features:**
- **Instance Table**: Name, channel type, connection status badges
- **Auto-Refresh**: Poll every 15 seconds for status updates
- **Status Badges**: Connected (green), Disconnected (gray), Error (red)
- **Create Instance Dialog**: Multi-step form with WhatsApp/Discord options
- **Edit Instance Dialog**: Modify all instance settings
- **Delete Confirmation**: Permanent deletion warning
- **QR Code Display**: Real-time WhatsApp pairing with 30s refresh
- **WhatsApp Auto-Detection**: Pre-fills Evolution API URL/key if local service detected
- **Row Actions**: Edit, Show QR, Delete contextual menu

**Create Instance Form:**

1. **Basic Settings:**
   - Instance name (unique identifier)
   - Channel selector: WhatsApp or Discord

2. **WhatsApp Fields:**
   - `evolution_url` (e.g., http://localhost:8080)
   - `evolution_key` (API key)
   - `phone_number` (E.164 format)
   - `auto_qr` (auto-generate QR code)

3. **Discord Fields:**
   - `discord_bot_token`
   - `discord_client_id`
   - `discord_guild_id`
   - Optional: default_channel_id, voice_enabled, slash_commands_enabled

4. **Agent Integration:**
   - `agent_api_url`
   - `agent_api_key`
   - `agent_name` (default agent to use)
   - `agent_timeout` (1-300 seconds)

5. **Settings:**
   - `enable_auto_split` - Split long messages automatically

**Component Breakdown:**
```
Instances.tsx
├── InstanceTable.tsx
│   └── InstanceStatusBadge.tsx
├── CreateInstanceDialog.tsx
├── EditInstanceDialog.tsx
├── DeleteInstanceDialog.tsx
└── QRCodeDialog.tsx
```

### Contacts Management (`/contacts`)

**File:** `ui/app/pages/Contacts.tsx`

**Features:**
- **Instance Selector**: Dropdown to choose active instance
- **Search**: Debounced search by name or phone number
- **Contacts Table**: Name, phone, status (online/offline/away/dnd), channel type
- **Clickable Rows**: Opens details panel on the side
- **Pagination**: 50 per page (adjustable: 10/25/50/100), offset-based
- **Details Panel**: Profile picture, contact metadata, status
- **Export to CSV**: Download as `contacts-<instance>-<timestamp>.csv`
- **Loading States**: Skeleton rows during fetch
- **Error Handling**: Instance not found detection with auto-clear

**Contact Schema:**
```typescript
interface Contact {
  id: string  // Phone JID or Discord ID
  name?: string
  channel_type: 'whatsapp' | 'discord'
  instance_name: string
  avatar_url?: string
  status: 'online' | 'offline' | 'away' | 'dnd' | 'unknown'
  is_verified?: boolean
  is_business?: boolean
  channel_data: { phone_number?: string }
  created_at?: string
  last_seen?: string
}
```

### Chats Management (`/chats`)

**File:** `ui/app/pages/Chats.tsx`

**Features:**
- **Instance Selector**: Dropdown to choose active instance
- **Chat Type Filter**: All, Group, Private, Channel, Thread
- **Chats Table**: Name, type, last message preview, unread count
- **Pagination**: 50 per page (adjustable), offset-based
- **Enhanced Details Panel**: Metadata, participant list, recent messages
- **Unread Indicators**: Visual unread count badges
- **Last Message Preview**: Truncated text with timestamp
- **Archive/Mute/Pin Status**: Visual indicators
- **Loading States**: Skeleton rows during fetch

**Chat Types:**
- `direct` - 1:1 conversation
- `group` - Group chat/channel
- `channel` - Broadcast channel (Discord)
- `thread` - Thread within a chat (Discord)

**Chat Schema:**
```typescript
interface Chat {
  id: string
  name?: string
  chat_type: 'direct' | 'group' | 'channel' | 'thread'
  avatar_url?: string
  unread_count?: number
  last_message_text?: string
  last_message_at?: string  // ISO timestamp
  is_archived: boolean
  is_muted: boolean
  is_pinned: boolean
  instance_name: string
  channel_type: 'whatsapp' | 'discord'
  participant_count?: number
  description?: string
  created_at?: string
  channel_data: Record<string, any>
}
```

### Messages Composer (`/messages`)

**File:** `ui/app/pages/Messages.tsx`

**Features:**
- **Instance Selector**: Dropdown showing channel type (whatsapp/discord)
- **Phone Number Input**: E.164 validation with real-time error
- **Message Type Tabs**: Text, Media, Audio, Reaction
- **Recent Messages List**: Last 10 sent (side panel, max-height: 600px)
- **Success Banners**: Auto-dismiss after 3 seconds (green)
- **Loading States**: Disabled buttons during send (prevent double-send)

**Message Types:**

1. **Text Message:**
   - Fields: `text` (required), `quotedMessageId` (optional)
   - Validation: Non-empty text

2. **Media Message:**
   - Fields: `mediaUrl`, `mediaType` (image/video/document), `caption` (optional)
   - Validation: Valid URL, type selection

3. **Audio Message:**
   - Fields: `audioUrl`
   - Validation: Valid URL

4. **Reaction:**
   - Fields: `messageId` (required), `emoji`
   - Validation: Message ID required, emoji picker

**Phone Validation:**
```typescript
// E.164 format: +[country][number]
const phoneRegex = /^\+?[1-9]\d{1,14}$/

function validatePhone(phone: string): boolean {
  return phoneRegex.test(phone)
}
```

### Access Rules Management (`/access-rules`)

**File:** `ui/app/pages/AccessRules.tsx`

**Features:**
- **Rule Filters**: Search by phone, filter by instance/type
- **Access Rules Table**: Phone, type badge (allow/block), scope pill, created date
- **Create Rule Dialog**: Phone number, rule type, scope (global/instance)
- **Delete Confirmation**: Permanent deletion warning
- **Phone Number Tester**: Test numbers against rules with visual results
- **Wildcard Support**: Trailing `*` in phone numbers (e.g., `+5511*`)

**Access Rule Schema:**
```typescript
interface AccessRule {
  id: number
  instance_name?: string | null  // null = global rule
  phone_number: string  // E.164 format, supports trailing *
  rule_type: 'allow' | 'block'
  created_at: string
  updated_at: string
}
```

**Rule Priority:**
1. Instance-specific rules checked first
2. Global rules checked second
3. If no rules match, default behavior depends on configuration

**Phone Tester:**
- Input: phone number, optional instance
- Output: Allowed (green), Blocked (red), No rules (gray)
- Shows matching rule details

### Traces Analytics (`/traces`)

**File:** `ui/app/pages/Traces.tsx`

**Features:**

**Filters (6 options):**
1. Instance selector (all or specific)
2. Date range (start + end date, default: last 7 days)
3. Status filter (all/success/failed)
4. Message type filter (all or specific type)
5. Phone number search
6. Pagination (offset-based, 50 per page)

**Analytics Section:**
- **4 Metric Cards**: Total messages, Success rate %, Avg duration (ms), Failed count
- **Success Rate Chart**: Pie/Donut chart (success vs failed)
- **Message Types Chart**: Bar chart (message type distribution)
- **Messages Over Time**: Line/Area chart (time series)
- **Top Contacts**: List of top 10 by message count

**Traces Table:**
- Columns: Timestamp, Instance, Phone, Message Type, Status
- Clickable rows open trace details dialog
- Status badges: Success (green), Failed (red), Access Denied (yellow)

**Trace Details Dialog:**
- Full metadata display
- Request/response payloads (JSON formatted)
- Error messages and stack traces
- Timing breakdown (agent time, total time)
- Agent session details

**Export to CSV:**
- Button with download
- Filename: `traces-<timestamp>.csv`
- Fields: Timestamp, Instance, Phone, Type, Status, Error

**Trace Schema:**
```typescript
interface Trace {
  trace_id: string
  instance_name: string
  whatsapp_message_id?: string
  sender_phone?: string
  sender_name?: string
  message_type?: string
  has_media: boolean
  has_quoted_message: boolean
  session_name?: string
  agent_session_id?: string
  status: 'received' | 'processing' | 'completed' | 'failed' | 'access_denied'
  error_message?: string
  error_stage?: string
  received_at?: string
  completed_at?: string
  agent_processing_time_ms?: number
  total_processing_time_ms?: number
  agent_response_success?: boolean
  evolution_success?: boolean
}
```

### Navigation & Layout

**Files:**
- `ui/app/layout.tsx` - Root layout
- `ui/app/components/Sidebar.tsx` - Navigation sidebar

**Navigation Menu:**
1. Dashboard (`/`)
2. Instances (`/instances`)
3. Access Rules (`/access-rules`)
4. Messages (`/messages`)
5. Contacts (`/contacts`)
6. Chats (`/chats`)
7. Traces (`/traces`)

**Responsive Behavior:**
- Desktop (≥1024px): Persistent sidebar
- Mobile (<1024px): Collapsible sidebar with hamburger menu

**Features:**
- HashRouter for Electron `file://` protocol compatibility
- Error boundaries per route (isolation)
- Active route highlighting
- Omni logo in sidebar

---

## API Endpoints Reference

### Base URL

```
http://localhost:8882
```

### Authentication

All endpoints require the `x-api-key` header:

```http
x-api-key: your-api-key-here
Content-Type: application/json
```

### 1. Instance Management

#### 1.1 List Instances

```http
GET /api/v1/instances?include_status=true&skip=0&limit=100
```

**Query Parameters:**
- `include_status` (bool, default: true) - Include Evolution API status
- `skip` (int, default: 0) - Offset for pagination
- `limit` (int, default: 100) - Max results

**Response:** `Instance[]`

```json
[
  {
    "id": 1,
    "name": "production-whatsapp",
    "channel_type": "whatsapp",
    "status": "connected",
    "evolution_status": {
      "state": "open",
      "owner_jid": "551199000001@s.whatsapp.net",
      "profile_name": "Acme Corp Support"
    },
    "is_active": true,
    "agent_api_url": "https://api.example.com/v1",
    "default_agent": "sales-agent",
    "enable_auto_split": true
  }
]
```

#### 1.2 Get Instance

```http
GET /api/v1/instances/{name}
```

**Response:** `Instance`

#### 1.3 Create Instance

```http
POST /api/v1/instances
Content-Type: application/json

{
  "name": "new-instance",
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "your-key",
  "agent_api_url": "https://api.example.com/v1",
  "agent_api_key": "sk-...",
  "default_agent": "support-agent",
  "agent_timeout": 60,
  "enable_auto_split": true
}
```

**Response:** `Instance` (201 Created)

#### 1.4 Update Instance

```http
PUT /api/v1/instances/{name}
Content-Type: application/json

{
  "agent_timeout": 90,
  "enable_auto_split": false
}
```

**Response:** `Instance`

#### 1.5 Delete Instance

```http
DELETE /api/v1/instances/{name}
```

**Response:** `{ success: true, message: "Instance deleted" }` (200 OK)

#### 1.6 Get QR Code

```http
GET /api/v1/instances/{name}/qr
```

**Response (WhatsApp):**
```json
{
  "instance_name": "my-instance",
  "channel_type": "whatsapp",
  "qr_code": "data:image/png;base64,...",
  "status": "connecting",
  "message": "Scan QR code to connect"
}
```

**Response (Discord):**
```json
{
  "instance_name": "my-discord",
  "channel_type": "discord",
  "qr_code": null,
  "invite_url": "https://discord.com/oauth2/authorize?client_id=...",
  "status": "disconnected",
  "message": "Use invite URL to add bot to server"
}
```

#### 1.7 Get Instance Status

```http
GET /api/v1/instances/{name}/status
```

**Response:**
```json
{
  "instance_name": "my-instance",
  "status": "connected",
  "evolution_status": {
    "state": "open",
    "owner_jid": "...",
    "profile_name": "..."
  }
}
```

#### 1.8 Connect Instance

```http
POST /api/v1/instances/{name}/connect
```

**Response:** `{ success: true, message: "Instance connected" }`

#### 1.9 Disconnect Instance

```http
POST /api/v1/instances/{name}/disconnect
```

**Response:** `{ success: true, message: "Instance disconnected" }`

#### 1.10 Restart Instance

```http
POST /api/v1/instances/{name}/restart
```

**Response:** `{ success: true, message: "Instance restarted" }`

### 2. Omni API (Unified Channel Access)

#### 2.1 List Contacts

```http
GET /api/v1/omni/{instance}/contacts?page=1&page_size=50&search_query=Alice
```

**Query Parameters:**
- `page` (int, default: 1, min: 1)
- `page_size` (int, default: 50, min: 1, max: 500)
- `search_query` (string, optional) - Search by name/phone
- `status_filter` (string, optional) - "online", "offline", "away", "dnd", "unknown"
- `channel_type` (string, optional) - "whatsapp", "discord"

**Response:**
```json
{
  "contacts": [
    {
      "id": "551199000101@s.whatsapp.net",
      "name": "Alice Johnson",
      "channel_type": "whatsapp",
      "instance_name": "production-whatsapp",
      "status": "online",
      "channel_data": {
        "phone_number": "+5511990000101"
      }
    }
  ],
  "total_count": 142,
  "page": 1,
  "page_size": 50,
  "has_more": true,
  "instance_name": "production-whatsapp",
  "channel_type": "whatsapp",
  "partial_errors": []
}
```

#### 2.2 List Chats

```http
GET /api/v1/omni/{instance}/chats?page=1&page_size=50&chat_type_filter=group
```

**Query Parameters:**
- `page` (int, default: 1, min: 1)
- `page_size` (int, default: 50, min: 1, max: 500)
- `chat_type_filter` (string, optional) - "direct", "group", "channel", "thread"
- `archived` (bool, optional)
- `channel_type` (string, optional) - "whatsapp", "discord"

**Response:**
```json
{
  "chats": [
    {
      "id": "120363123456789@g.us",
      "name": "Sales Team",
      "chat_type": "group",
      "channel_type": "whatsapp",
      "unread_count": 0,
      "last_message_text": "Meeting at 3 PM",
      "last_message_at": "2025-01-15T15:30:00Z",
      "participant_count": 15,
      "is_pinned": false
    }
  ],
  "total_count": 87,
  "page": 1,
  "page_size": 50,
  "has_more": true
}
```

#### 2.3 List Messages

```http
GET /api/v1/omni/{instance}/chats/{chat_id}/messages?page=1&page_size=50
```

**Query Parameters:**
- `page` (int, default: 1, min: 1)
- `page_size` (int, default: 50, min: 1, max: 200)
- `before_message_id` (string, optional) - Cursor pagination

**Response:**
```json
{
  "messages": [
    {
      "id": "3EB0ABC...",
      "chat_id": "...",
      "sender_id": "...",
      "sender_name": "Alice Johnson",
      "message_type": "text",
      "text": "Hello!",
      "is_from_me": false,
      "timestamp": "2025-01-15T16:45:00Z"
    }
  ],
  "total_count": 156,
  "page": 1,
  "page_size": 50,
  "has_more": true
}
```

### 3. Message Sending

**Note:** Message endpoints use `/instance/` (singular), not `/instances/`

#### 3.1 Send Text Message

```http
POST /api/v1/instance/{name}/send-text
Content-Type: application/json

{
  "phone_number": "+5511999999999",
  "text": "Hello from Omni!",
  "quoted_message_id": "3EB0ABC..."
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "3EB0XYZ...",
  "status": "sent"
}
```

#### 3.2 Send Media Message

```http
POST /api/v1/instance/{name}/send-media
Content-Type: application/json

{
  "phone_number": "+5511999999999",
  "media_url": "https://example.com/image.jpg",
  "media_type": "image",
  "caption": "Check this out!"
}
```

**Media Types:** `image`, `video`, `document`

#### 3.3 Send Audio Message

```http
POST /api/v1/instance/{name}/send-audio
Content-Type: application/json

{
  "phone_number": "+5511999999999",
  "audio_url": "https://example.com/audio.mp3"
}
```

#### 3.4 Send Reaction

```http
POST /api/v1/instance/{name}/send-reaction
Content-Type: application/json

{
  "phone_number": "+5511999999999",
  "message_id": "3EB0ABC...",
  "emoji": "👍"
}
```

### 4. Access Control

#### 4.1 List Access Rules

```http
GET /api/v1/access/rules?instance_name=production-whatsapp&rule_type=allow
```

**Query Parameters:**
- `instance_name` (string, optional) - Filter by instance scope
- `rule_type` (string, optional) - "allow" or "block"

**Response:**
```json
[
  {
    "id": 1,
    "instance_name": "production-whatsapp",
    "phone_number": "+5511990000101",
    "rule_type": "allow",
    "created_at": "2025-01-10T10:00:00Z"
  },
  {
    "id": 2,
    "instance_name": null,
    "phone_number": "+5511*",
    "rule_type": "allow",
    "created_at": "2025-01-08T08:00:00Z"
  }
]
```

#### 4.2 Create Access Rule

```http
POST /api/v1/access/rules
Content-Type: application/json

{
  "phone_number": "+5511999999999",
  "rule_type": "block",
  "instance_name": "production-whatsapp"
}
```

**Response:** `AccessRule` (201 Created)

**Note:** Omit `instance_name` or set to `null` for global rules

#### 4.3 Delete Access Rule

```http
DELETE /api/v1/access/rules/{rule_id}
```

**Response:** 204 No Content

#### 4.4 Check Phone Access

```http
POST /api/v1/access/check
Content-Type: application/json

{
  "phone_number": "+5511999999999",
  "instance_name": "production-whatsapp"
}
```

**Response:**
```json
{
  "allowed": false,
  "reason": "Phone number is blocked",
  "matched_rule": {
    "id": 2,
    "rule_type": "block",
    "phone_number": "+5511999999999"
  }
}
```

### 5. Traces & Analytics

#### 5.1 List Traces

```http
GET /api/v1/traces?instance_name=production-whatsapp&offset=0&limit=50&status=completed
```

**Query Parameters:**
- `phone` (string, optional) - Filter by sender phone
- `instance_name` (string, optional)
- `trace_status` (string, optional) - "received", "processing", "completed", "failed", "access_denied"
- `message_type` (string, optional)
- `session_name` (string, optional)
- `agent_session_id` (string, optional)
- `sender_phone` (string, optional) - Alias for phone
- `has_media` (bool, optional)
- `start_date` (datetime, optional) - ISO format
- `end_date` (datetime, optional) - ISO format
- `all_time` (bool, default: false) - Fetch all data without date filters
- `limit` (int, default: 50, min: 1, max: 1000)
- `offset` (int, default: 0, min: 0)

**Response:**
```json
[
  {
    "trace_id": "550e8400-...",
    "instance_name": "production-whatsapp",
    "sender_phone": "+5511990000101",
    "sender_name": "Alice Johnson",
    "message_type": "conversation",
    "status": "completed",
    "agent_processing_time_ms": 1823,
    "total_processing_time_ms": 2333,
    "received_at": "2025-01-15T16:45:00.123Z",
    "completed_at": "2025-01-15T16:45:02.456Z"
  }
]
```

#### 5.2 Get Trace Details

```http
GET /api/v1/traces/{trace_id}
```

**Response:** `Trace` (single object)

#### 5.3 Get Trace Payloads

```http
GET /api/v1/traces/{trace_id}/payloads?include_payload=false
```

**Query Parameters:**
- `include_payload` (bool, default: false) - Include actual payload data

**Response:**
```json
[
  {
    "id": 1,
    "trace_id": "550e8400-...",
    "stage": "webhook_received",
    "payload_type": "webhook",
    "timestamp": "2025-01-15T16:45:00.123Z",
    "payload_size_original": 3456,
    "payload_size_compressed": 1234,
    "compression_ratio": 0.36,
    "payload": null
  }
]
```

**Stages:** `webhook_received`, `agent_request`, `agent_response`, `evolution_send`

#### 5.4 Get Analytics

```http
GET /api/v1/traces/analytics?instance_name=production-whatsapp&start_date=2025-01-09&end_date=2025-01-15
```

**Query Parameters:**
- `start_date` (datetime, optional) - ISO format
- `end_date` (datetime, optional) - ISO format
- `all_time` (bool, default: false)
- `instance_name` (string, optional)

**Response:**
```json
{
  "total_messages": 1247,
  "successful_messages": 1189,
  "failed_messages": 58,
  "success_rate": 95.35,
  "avg_processing_time_ms": 2145.67,
  "avg_agent_time_ms": 1823.45,
  "message_types": {
    "conversation": 856,
    "imageMessage": 234,
    "audioMessage": 87
  },
  "error_stages": {
    "agent_request": 32,
    "evolution_send": 18
  },
  "instances": {
    "production-whatsapp": 983,
    "support-whatsapp": 264
  }
}
```

### 6. Health Check

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy"
}
```

### Error Response Format

**Standard Error (404, 400, etc.):**
```json
{
  "detail": "Instance 'my-bot' not found"
}
```

**Validation Error (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "phone_number"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Access Denied (403):**
```json
{
  "status": "blocked",
  "reason": "access_denied",
  "phone": "+5511999999999",
  "message": "Phone number is blocked by access rules"
}
```

---

## TypeScript Type Definitions

### Core Types

```typescript
type ChannelType = 'whatsapp' | 'discord'
type ContactStatus = 'online' | 'offline' | 'away' | 'dnd' | 'unknown'
type ChatType = 'direct' | 'group' | 'channel' | 'thread'
type MessageType = 'text' | 'image' | 'video' | 'audio' | 'document' | 'sticker' | 'contact' | 'location' | 'reaction' | 'system' | 'unknown'
type AccessRuleType = 'allow' | 'block'
type TraceStatus = 'received' | 'processing' | 'completed' | 'failed' | 'access_denied'
type InstanceStatus = 'connected' | 'disconnected' | 'connecting' | 'error'
```

### Instance

```typescript
interface Instance {
  id: number
  name: string
  channel_type: ChannelType
  status: InstanceStatus
  is_default?: boolean
  is_active?: boolean

  // WhatsApp
  evolution_url?: string
  evolution_key?: string
  whatsapp_instance?: string
  session_id_prefix?: string
  webhook_base64?: boolean

  // Discord
  has_discord_bot_token?: boolean
  discord_client_id?: string
  discord_guild_id?: string
  discord_default_channel_id?: string
  discord_voice_enabled?: boolean
  discord_slash_commands_enabled?: boolean

  // Agent Configuration
  agent_api_url?: string
  agent_api_key?: string
  default_agent?: string
  agent_timeout?: number
  agent_instance_type?: string
  agent_id?: string
  agent_type?: string
  agent_stream_mode?: boolean

  // Evolution Status (derived)
  evolution_status?: {
    state?: string
    owner_jid?: string
    profile_name?: string
    profile_picture_url?: string
    last_updated?: string
    error?: string
  }

  // Settings
  enable_auto_split?: boolean
  reject_call?: boolean
  msg_call?: string
  groups_ignore?: boolean
  always_online?: boolean
  read_messages?: boolean
  read_status?: boolean
  sync_full_history?: boolean

  // Metadata
  automagik_instance_id?: string
  automagik_instance_name?: string
  profile_name?: string
  profile_pic_url?: string
  owner_jid?: string
  created_at?: string
  updated_at?: string
}
```

### Contact

```typescript
interface Contact {
  id: string  // Phone JID or Discord ID
  name?: string
  channel_type: ChannelType
  instance_name: string
  avatar_url?: string
  status?: ContactStatus
  is_verified?: boolean
  is_business?: boolean
  channel_data?: {
    phone_number?: string
    pushName?: string
    isGroup?: boolean
    isBusiness?: boolean
    verifiedName?: string
    // Discord
    username?: string
    discriminator?: string
    bot?: boolean
  }
  created_at?: string
  last_seen?: string
}

interface ContactsResponse {
  contacts: Contact[]
  total_count: number
  page: number
  page_size: number
  has_more: boolean
  instance_name: string
  channel_type: ChannelType
  partial_errors: any[]
}
```

### Chat

```typescript
interface Chat {
  id: string
  name?: string
  chat_type?: ChatType
  avatar_url?: string
  unread_count?: number
  last_message_text?: string
  last_message_at?: string  // ISO timestamp
  is_archived?: boolean
  is_muted?: boolean
  is_pinned?: boolean
  instance_name: string
  channel_type: ChannelType
  participant_count?: number
  description?: string
  created_at?: string
  channel_data?: Record<string, any>
}

interface ChatsResponse {
  chats: Chat[]
  total_count: number
  page: number
  page_size: number
  has_more: boolean
  instance_name: string
  channel_type: ChannelType
  partial_errors: any[]
}
```

### Message

```typescript
interface Message {
  id: string
  chat_id: string
  sender_id: string
  sender_name?: string
  message_type: MessageType
  text?: string
  media_url?: string
  media_mime_type?: string
  media_size?: number
  caption?: string
  thumbnail_url?: string
  is_from_me?: boolean
  is_forwarded?: boolean
  is_reply?: boolean
  reply_to_message_id?: string
  timestamp: string
  edited_at?: string
  channel_type: ChannelType
  instance_name: string
  channel_data?: Record<string, any>
}

interface MessagesResponse {
  messages: Message[]
  total_count: number
  page: number
  page_size: number
  has_more: boolean
  instance_name: string
  chat_id: string
  channel_type: ChannelType
  partial_errors: any[]
}
```

### Message Sending

```typescript
interface SendTextRequest {
  phone_number?: string
  user_id?: string
  text: string
  quoted_message_id?: string
  auto_parse_mentions?: boolean
  mentioned?: string[]
  split_message?: boolean | null
}

interface SendMediaRequest {
  phone_number?: string
  user_id?: string
  media_url: string
  media_type: 'image' | 'video' | 'document'
  caption?: string
  file_name?: string
}

interface SendAudioRequest {
  phone_number?: string
  user_id?: string
  audio_url: string
}

interface SendReactionRequest {
  phone_number?: string
  user_id?: string
  message_id: string
  emoji: string
}

interface MessageResponse {
  success: boolean
  message_id?: string | null
  status: string
  error?: string | null
}
```

### Trace

```typescript
interface Trace {
  trace_id: string
  instance_name: string
  whatsapp_message_id?: string
  sender_phone?: string
  sender_name?: string
  message_type?: string
  message_type_display?: string
  has_media: boolean
  has_quoted_message: boolean
  session_name?: string
  agent_session_id?: string
  status: TraceStatus
  error_message?: string
  error_stage?: string
  received_at?: string
  completed_at?: string
  agent_processing_time_ms?: number
  total_processing_time_ms?: number
  agent_response_success?: boolean
  evolution_success?: boolean
  payload?: any
}

interface TracePayload {
  id: number
  trace_id: string
  stage: 'webhook_received' | 'agent_request' | 'agent_response' | 'evolution_send'
  payload_type: string
  timestamp: string
  status_code?: number
  error_details?: string
  payload_size_original: number
  payload_size_compressed: number
  compression_ratio: number
  contains_media: boolean
  contains_base64: boolean
  payload?: any
}
```

### Analytics

```typescript
interface Analytics {
  total_messages: number
  successful_messages: number
  failed_messages: number
  success_rate: number  // Percentage
  avg_processing_time_ms: number
  avg_agent_time_ms: number
  message_types: Record<string, number>
  error_stages: Record<string, number>
  instances: Record<string, number>
}
```

### Access Rule

```typescript
interface AccessRule {
  id: number
  instance_name?: string | null  // null = global rule
  phone_number: string  // E.164 format, supports trailing *
  rule_type: AccessRuleType
  created_at: string
  updated_at: string
}

interface CreateAccessRule {
  phone_number: string
  rule_type: AccessRuleType
  instance_name?: string | null
}

interface CheckAccessResponse {
  allowed: boolean
  reason: string
  matched_rule?: AccessRule
}
```

### Pagination

```typescript
interface PaginatedResponse<T> {
  data?: T[]
  contacts?: T[]  // Contacts endpoint
  chats?: T[]     // Chats endpoint
  messages?: T[]  // Messages endpoint
  total_count: number
  page: number
  page_size: number
  has_more: boolean
}
```

---

## Mock Data & Testing

### Mock Data File

**Location:** `OMNI_MOCK_DATA.json`

**Contents:**
- 4 sample instances (2 WhatsApp, 1 Discord, 1 inactive)
- 7 contacts (5 WhatsApp, 2 Discord)
- 6 chats (4 WhatsApp, 2 Discord)
- 5 messages (text, image, document)
- 5 traces with various statuses
- Complete analytics data
- 4 access rules
- QR code examples
- Error response examples

**All data is PII-safe:**
- Phone numbers: `+5511990000XXX` (fictional)
- Names: Generic (Alice Johnson, Bob Martinez, etc.)
- Avatar URLs: Placeholder images (`placehold.co`)
- Timestamps: Recent but fictional dates

### Using Mock Data

```typescript
import mockData from './OMNI_MOCK_DATA.json'

// Get sample instances
const instances = mockData.instances
console.log(instances[0])  // production-whatsapp

// Get sample contacts
const whatsappContacts = mockData.contacts.whatsapp
const discordContacts = mockData.contacts.discord

// Get sample messages
const messages = mockData.messages

// Get sample analytics
const analytics = mockData.analytics
console.log(analytics.success_rate)  // 95.35
```

### Testing Scenarios

**1. Connected WhatsApp Instance:**
```json
{
  "id": 1,
  "name": "production-whatsapp",
  "status": "connected",
  "evolution_status": {
    "state": "open"
  }
}
```

**2. Connecting WhatsApp Instance (QR needed):**
```json
{
  "id": 2,
  "name": "support-whatsapp",
  "status": "connecting",
  "evolution_status": {
    "state": "connecting"
  }
}
```

**3. Disconnected Instance:**
```json
{
  "id": 4,
  "name": "testing-whatsapp",
  "status": "disconnected",
  "is_active": false
}
```

**4. Successful Trace:**
```json
{
  "trace_id": "550e8400-...",
  "status": "completed",
  "agent_processing_time_ms": 1823,
  "total_processing_time_ms": 2333
}
```

**5. Failed Trace:**
```json
{
  "trace_id": "550e8400-...",
  "status": "failed",
  "error_message": "Agent API timeout",
  "error_stage": "agent_request"
}
```

**6. Access Denied Trace:**
```json
{
  "trace_id": "550e8400-...",
  "status": "access_denied",
  "error_message": "Phone number is blocked"
}
```

---

## Known Issues & Workarounds

### Process Management & Race Conditions (6 issues)

| # | Location | Issue | Mitigation | Impact |
|---|----------|-------|------------|--------|
| 1 | `backend-manager.ts:179` | Race: PID changes during cleanup | Kill-by-name strategy, then PID fallback | Rare edge case |
| 2 | `backend-manager.ts:206` | Race: PID exits before force kill | Gracefully handled with info logging | None (expected) |
| 3 | `backend-manager.ts:460` | Race: HTTP vs uvicorn init | Wait for uvicorn ready log | Brief "not ready" status |
| 4 | `backend-manager.ts:59,367` | Startup lock | Implemented and working | Prevents spam start |
| 5 | `main.ts:160` | Cleanup flag | Implemented | Prevents duplicate cleanup |
| 6 | `main.ts:187` | Infinite loop workaround | Uses `app.exit()` vs `quit()` | Required on Windows |

**Recent Fix (commit `0a03a38`):**
- Process termination wait increased: 1s → 2s
- Port release timeout increased: 5s → 10s
- **Reason:** Orphaned backends from installation not killed fast enough
- **Impact:** More reliable startup, slightly slower cleanup

### Evolution API Issues (3 issues)

| # | Location | Issue | Recovery | Impact |
|---|----------|-------|----------|--------|
| 7 | `evolution-manager.ts:329` | Database corruption detection | Auto-reinitialize | Automatic recovery |
| 8 | `evolution-manager.ts:345` | Template DB copy failure | Fallback to Prisma migration | Slower initialization |
| 9 | `evolution-manager.ts:378` | Database init failure | Logged with fallback | May prevent Evolution start |

### TypeScript & Tooling Workarounds (3 issues)

| # | Location | Issue | Reason | Impact |
|---|----------|-------|--------|--------|
| 10 | `omni-schema.ts:237` | `z.unknown()` for arrays | Zod v4 cache limitation | None (types intact) |
| 11 | `CustomTitlebar.tsx:5,10,15` | 3x `@ts-expect-error` | Preload API not typed | None (runtime OK) |
| 12 | 8+ files | `eslint-disable exhaustive-deps` | Intentional effect behavior | None (intended) |

**Files with ESLint Disables:**
- `Chats.tsx:47`
- `AccessRules.tsx:46,65`
- `Contacts.tsx:48`
- `Dashboard.tsx:186`
- `Instances.tsx:45`
- `Messages.tsx:31`
- `Traces.tsx:53,59`
- `QRCodeDialog.tsx:45`

**Reason:** Intentionally incomplete dependency arrays for specific effect behavior (run only on mount, not on every state change)

### Performance Optimizations (1 issue)

| # | Location | Type | Reason | Impact |
|---|----------|------|--------|--------|
| 13 | `backend-monitor.ts:184` | PM2 status cached | Prevent spamming checks | 10s update interval vs real-time |

### Design Decisions (Not Bugs)

| # | Location | Type | Reason | Impact |
|---|----------|------|--------|--------|
| 14 | `backend-manager.ts:145` | Excludes current process's child | Safety measure | Prevents self-termination |
| 15 | Browser mode | Conveyor API warning | Expected behavior | Electron-only features disabled |

### Summary

- **Total documented issues:** 15
- **Critical bugs:** 0 (all have mitigations/workarounds)
- **Race conditions:** 6 (all handled with retry/fallback logic)
- **Database issues:** 3 (all have auto-recovery)
- **TypeScript limitations:** 3 (cosmetic only)
- **Performance opts:** 1 (intentional caching)

**Most issues are edge cases with implemented workarounds or graceful degradation.**

---

## Architecture & Design Patterns

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Electron Desktop App (Windows)              │
├─────────────────────────────────────────────────────────┤
│  React Frontend (Renderer Process)                      │
│  ├── Pages (Dashboard, Instances, Contacts, etc.)       │
│  ├── Components (UI library - Shadcn)                   │
│  └── Conveyor API Client (IPC abstraction)              │
├─────────────────────────────────────────────────────────┤
│  Main Process (Node.js)                                 │
│  ├── Backend Manager (Python subprocess)                │
│  ├── Evolution Manager (Node.js subprocess)             │
│  ├── IPC Handlers (Conveyor handlers)                   │
│  └── Window Management (Electron)                       │
└─────────────────────────────────────────────────────────┘
          │                          │
          ▼                          ▼
┌──────────────────┐       ┌──────────────────┐
│  FastAPI Backend │       │  Evolution API   │
│  (Python)        │       │  (Node.js)       │
│  Port: 8882      │       │  Port: 8080      │
│  ├── Routes      │       │  ├── WhatsApp    │
│  ├── Services    │       │  │   Integration │
│  ├── Models      │       │  └── Baileys     │
│  └── SQLite DB   │       │      Library     │
└──────────────────┘       └──────────────────┘
          │
          ▼
┌──────────────────┐
│  Agent APIs      │
│  (External)      │
│  ├── Automagik   │
│  └── Custom      │
└──────────────────┘
```

### Data Flow

**1. Frontend → Backend:**
```
React Component
  ↓ (calls)
Conveyor API Method
  ↓ (IPC invoke)
Main Process Handler
  ↓ (HTTP request)
FastAPI Endpoint
  ↓ (processes)
Service Layer
  ↓ (queries)
SQLite Database
```

**2. WhatsApp Message Received:**
```
WhatsApp Web
  ↓ (Baileys)
Evolution API
  ↓ (webhook)
FastAPI /webhook
  ↓ (access check)
Access Control Service
  ↓ (if allowed)
Agent API
  ↓ (response)
Message Router
  ↓ (send)
Evolution API
  ↓
WhatsApp Web
```

### IPC Communication Pattern

**Conveyor API Abstraction:**

```typescript
// Frontend (Renderer)
import { useConveyor } from '@/lib/conveyor/hooks/use-conveyor'

function MyComponent() {
  const { omni } = useConveyor()

  const instances = await omni.listInstances()
  // ↑ This becomes IPC call: 'omni:instances:list'
}

// Main Process Handler
ipcMain.handle('omni:instances:list', async (event, params) => {
  // Validate with Zod
  const validated = ListInstancesParamsSchema.parse(params)

  // HTTP request to backend
  const response = await axios.get('http://localhost:8882/api/v1/instances', {
    headers: { 'x-api-key': API_KEY },
    params: validated
  })

  // Validate response with Zod
  return InstanceSchema.array().parse(response.data)
})
```

**Benefits:**
- Type-safe end-to-end
- Centralized error handling
- Runtime validation
- IPC abstraction (frontend doesn't know about IPC)

### State Management

**Instance State (Zustand):**
```typescript
interface InstanceStore {
  instances: Instance[]
  selectedInstance: Instance | null
  setInstances: (instances: Instance[]) => void
  selectInstance: (instance: Instance) => void
}

const useInstanceStore = create<InstanceStore>((set) => ({
  instances: [],
  selectedInstance: null,
  setInstances: (instances) => set({ instances }),
  selectInstance: (instance) => set({ selectedInstance: instance })
}))
```

**Component-Local State (React):**
- Loading states
- Form inputs
- Temporary UI state

**Server State (API):**
- Contacts, chats, messages
- Traces and analytics
- Backend status

### Error Handling Strategy

**1. HTTP Errors:**
```typescript
try {
  const response = await fetch(url, options)
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Request failed')
  }
  return response.json()
} catch (err) {
  if (isBackendError(err)) {
    setError('Backend not running. Please start from Dashboard.')
  } else if (isBackendStarting(err)) {
    setError('Backend is initializing. Auto-retrying...')
    setTimeout(retry, 2000)
  } else {
    setError(getErrorMessage(err))
  }
}
```

**2. Error Categories:**
- **Backend Connection**: `ECONNREFUSED`, `Network Error`
- **Backend Starting**: Circuit breaker errors
- **Validation**: 422 Unprocessable Entity
- **Not Found**: 404 Not Found
- **Access Denied**: 403 Forbidden
- **Internal**: 500 Internal Server Error

**3. Error Display:**
- **Banners**: Top of page, color-coded (red/blue/yellow)
- **Inline**: Below form fields
- **Toast**: Auto-dismiss notifications (planned)
- **Error Boundaries**: Per-route isolation

### Pagination Patterns

**Offset-Based (Traces, Contacts):**
```typescript
interface PaginationState {
  offset: number
  limit: number
  total: number
}

function nextPage() {
  setOffset(offset + limit)
}

function prevPage() {
  setOffset(Math.max(0, offset - limit))
}
```

**Page-Based (Chats, Messages):**
```typescript
interface PaginationState {
  page: number
  page_size: number
  total_count: number
  has_more: boolean
}

function nextPage() {
  if (has_more) setPage(page + 1)
}

function prevPage() {
  if (page > 1) setPage(page - 1)
}
```

### Loading State Patterns

**Skeleton Loaders:**
```typescript
{loading ? (
  <TableRow>
    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
  </TableRow>
) : (
  data.map(item => <TableRow key={item.id}>...</TableRow>)
)}
```

**Disabled States:**
```typescript
<Button
  onClick={handleSend}
  disabled={sending}
>
  {sending ? 'Sending...' : 'Send'}
</Button>
```

### Validation Patterns

**Zod Runtime Validation:**
```typescript
import { z } from 'zod'

const InstanceSchema = z.object({
  id: z.number(),
  name: z.string(),
  channel_type: z.enum(['whatsapp', 'discord']),
  status: z.enum(['connected', 'disconnected', 'connecting', 'error']),
  // ... more fields
}).transform((data) => ({
  ...data,
  // Derive status from evolution_status.state
  status: data.evolution_status?.state === 'open' ? 'connected' :
          data.evolution_status?.state === 'connecting' ? 'connecting' :
          data.evolution_status?.state === 'close' ? 'disconnected' : 'error'
}))

// Use in handler
const instance = InstanceSchema.parse(apiResponse)
```

**Form Validation:**
```typescript
const phoneRegex = /^\+?[1-9]\d{1,14}$/

function validatePhone(phone: string): boolean {
  return phoneRegex.test(phone)
}

// In component
const [phoneError, setPhoneError] = useState('')

function handlePhoneChange(value: string) {
  setPhone(value)
  if (!validatePhone(value)) {
    setPhoneError('Invalid phone number. Use E.164 format: +5511999999999')
  } else {
    setPhoneError('')
  }
}
```

---

## Production Deployment

### Desktop Application Build

**Build Commands:**
```bash
cd ui

# Development
npm run dev

# Production build
npm run build:win    # Windows
npm run build:mac    # macOS
npm run build:linux  # Linux
```

**Output:**
- Windows: `ui/dist/Omni-Setup-1.0.0.exe` (installer)
- macOS: `ui/dist/Omni-1.0.0.dmg`
- Linux: `ui/dist/Omni-1.0.0.AppImage`

**Bundled Components:**
- Python backend (PyInstaller, ~41 MB)
- Evolution API (pre-built, ~50 MB)
- Node.js runtime (~50 MB)
- Template databases

**Installation:**
- Windows: `C:\Users\<user>\AppData\Local\Programs\Automagik\Omni`
- macOS: `/Applications/Omni.app`
- Linux: User-defined location

**Data Directory:**
- Windows: `C:\Users\<user>\AppData\Roaming\Omni`
- macOS: `~/Library/Application Support/Omni`
- Linux: `~/.config/Omni`

**Contains:**
- `api-key.txt` - FastAPI API key
- `evolution-api-key.txt` - Evolution API key
- `data/automagik-omni.db` - Main SQLite database
- `evolution-data/evolution.db` - Evolution API database

### Backend API Deployment

**Standalone Deployment:**
```bash
# Install dependencies
uv sync

# Run migrations
alembic upgrade head

# Start server
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8882
```

**Environment Variables:**
```bash
AUTOMAGIK_OMNI_API_HOST=0.0.0.0
AUTOMAGIK_OMNI_API_PORT=8882
AUTOMAGIK_OMNI_API_KEY=your-api-key-here
AUTOMAGIK_OMNI_DATABASE_URL=sqlite:///./data/automagik-omni.db
AUTOMAGIK_OMNI_ENABLE_TRACING=true
LOG_LEVEL=INFO
```

**Docker Deployment (example):**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy files
COPY . .

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 8882

# Run
CMD ["uv", "run", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8882"]
```

### Production Checklist

**Before Release:**
- [ ] Merge `feature/electron-desktop-ui` → `dev`
- [ ] Merge `dev` → `main` (after approval)
- [ ] Run full test suite
- [ ] Test installer on clean Windows/macOS/Linux
- [ ] Verify backend auto-start on app launch
- [ ] Verify Evolution API auto-start with local detection
- [ ] Test all CRUD operations (instances, contacts, chats, messages, rules, traces)
- [ ] Test error scenarios (backend offline, Evolution offline, API timeout)
- [ ] Test process cleanup on app exit
- [ ] Verify data persistence after restart
- [ ] Check API key generation and persistence
- [ ] Test installer upgrade path (if applicable)

**Optional Enhancements:**
- [ ] Real-time WebSocket updates for status
- [ ] Toast notification system
- [ ] System tray integration
- [ ] Keyboard shortcuts
- [ ] Accessibility audit (WCAG 2.1)
- [ ] Integration test suite
- [ ] Performance profiling
- [ ] Security audit (API key handling)

### Branch Policy

**Current Status:**
- PR #8: `feature/electron-desktop-ui` → `main` (BLOCKED)
- **Reason:** Branch policy requires `dev` → `main` or `hotfix/*` → `main`

**Required Steps:**
1. Create PR: `feature/electron-desktop-ui` → `dev`
2. Review and merge to `dev`
3. Create PR: `dev` → `main`
4. Review and merge to `main`
5. Release desktop installers

### Release Process

**Version Numbering:**
- Format: `MAJOR.MINOR.PATCH` (e.g., 1.0.0)
- Increment MAJOR for breaking changes
- Increment MINOR for new features
- Increment PATCH for bug fixes

**Release Artifacts:**
- Windows installer (`.exe`)
- macOS disk image (`.dmg`)
- Linux AppImage (`.AppImage`)
- Source code (`.zip`, `.tar.gz`)

**Distribution:**
- GitHub Releases
- Optional: Auto-update server (Electron's `autoUpdater`)

---

## Summary

This document consolidates all information about the Automagik Omni desktop application and API:

✅ **Complete Feature Set**: 7 pages, 32 API methods, 60+ components
✅ **Type Safety**: Full TypeScript types + Zod validation
✅ **Mock Data**: PII-safe JSON for testing
✅ **Known Issues**: 15 documented with mitigations
✅ **Production Ready**: 95%+ complete, ready after `dev` merge

**Key Resources:**
- **This Document**: Complete reference
- **`FRONTEND_DEVELOPER_GUIDE.md`**: API integration guide
- **`DESKTOP_UI_STATUS.md`**: Implementation status report
- **`OMNI_MOCK_DATA.json`**: Test data

**Next Steps:**
1. Merge to `dev` branch (branch policy)
2. User acceptance testing
3. Production release

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-08
**Maintained By:** Automagik Omni Team
