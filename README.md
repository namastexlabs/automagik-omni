> [!IMPORTANT]
> **This repository has been superseded.** Omni v2 — a complete TypeScript/Bun rewrite with event-driven architecture (NATS JetStream), a CLI-first design, and expanded channel support — is now the active project.
>
> **New home: [automagik-dev/omni](https://github.com/automagik-dev/omni)**
>
> This repo is archived and no longer maintained. Please star and use the new one!

<p align="center">
  <img src=".github/images/omni-logo.svg" alt="Automagik Omni Logo" width="400">
</p>
<h2 align="center">The Omnipresent Messaging Hub for AI Agents</h2>

<p align="center">
  <strong>🌐 One Integration, All Channels, Zero Headaches</strong><br>
  Connect your AI agents to WhatsApp, Discord, Slack, and more—all through one unified API<br>
  Multi-tenant, production-ready, and built for scale
</p>

<p align="center">
  <a href="https://github.com/namastexlabs/automagik-omni/actions"><img alt="Build Status" src="https://img.shields.io/github/actions/workflow/status/namastexlabs/automagik-omni/test.yml?branch=main&style=flat-square" /></a>
  <a href="https://github.com/namastexlabs/automagik-omni/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/namastexlabs/automagik-omni?style=flat-square&color=00D9FF" /></a>
  <a href="https://discord.gg/xcW8c7fF3R"><img alt="Discord" src="https://img.shields.io/discord/1095114867012292758?style=flat-square&color=00D9FF&label=discord" /></a>
  <a href="https://github.com/orgs/namastexlabs/projects/9/views/1?filterQuery=project%3Aomni"><img alt="Roadmap" src="https://img.shields.io/badge/📍_roadmap-view_initiatives-5319E7?style=flat-square" /></a>
</p>

<p align="center">
  <a href="#-what-is-automagik-omni">What is Omni?</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="https://github.com/orgs/namastexlabs/projects/9/views/1?filterQuery=project%3Aomni">🗺️ Roadmap</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## 🚀 What is Automagik Omni?

**Automagik Omni** is your AI agent's universal translator for the messaging world. Think of it as an **intelligent postman** who:
- 🗺️ Knows every address (WhatsApp, Discord, Slack, Instagram...)
- 🌍 Speaks every language (different protocols and APIs)
- 📬 Delivers messages reliably, every time
- 👥 Remembers every conversation for analytics and debugging

### 💔 The Problem: Integration Hell

**"Building messaging integrations is a developer's nightmare"**

Every time you want your AI agent to work on a new platform, you face:

- 📚 **Learn a new API**: Each platform has different docs, authentication, webhooks
- ♻️ **Duplicate code**: The same logic written 5 different ways for 5 platforms
- 🐛 **Maintenance nightmare**: Updates break across different integrations
- ⏰ **Procrastination paralysis**: *"I'll add Slack support... later"*
- 🔥 **Production fires**: When WhatsApp breaks, everything breaks

**The result?** Months of development, fragile code, and agents that only work on 1-2 platforms.

### ✨ The Omni Solution: Write Once, Connect Everywhere

```mermaid
graph LR
    A[Your AI Agent] -->|One API| B[OMNI HUB]
    B -->|Automatic| C[WhatsApp]
    B -->|Automatic| D[Discord]
    B -->|Automatic| E[Slack]
    B -->|Automatic| F[Instagram]
    B -->|Automatic| G[Teams]
    B -->|Automatic| H[...and more]

    style B fill:#00D9FF,stroke:#0099CC,stroke-width:3px,color:#000
```

**What you get:**
- ✍️ **Write integration code once** → works everywhere
- 🔌 **Plug & Play**: Connect new channels in minutes, not weeks
- 🏗️ **Production-grade**: Multi-tenant, secure, scalable from day one
- 📊 **Full visibility**: Every message traced from input to output
- 🤖 **MCP-native**: Control via Claude, Cursor, or any MCP tool

### 🌟 The Vision: True Omnipresence

Imagine talking to the same AI agent across all your apps, with perfect context:

> *"Hey assistant, I saw a cool product on Instagram—can you help me order it here on WhatsApp?"*

The agent remembers who you are, what you were talking about, and responds naturally—**regardless of platform**.

**Today:** Omni makes your agents **present** on multiple channels
**Tomorrow:** True **omnipresence** with shared context across all platforms

---

## 🌟 Key Features

### ✅ Production-Ready Today

- **🔌 Plug & Play Setup**: From zero to sending messages in under 5 minutes
- **🏢 Multi-Tenant Architecture**: Complete isolation between instances, teams, and clients
- **📊 Comprehensive Tracing**: Every message logged with performance metrics and payloads
- **🔐 Enterprise Security**: API key authentication, request validation, CORS controls
- **🤖 MCP Server Built-in**: Control from Claude Code, Cursor, or any MCP-compatible tool
- **🚀 Battle-Tested Scale**: Handle 100+ instances and hundreds of concurrent conversations
- **🔄 Real-Time Streaming**: SSE support for [Automagik Hive](https://github.com/namastexlabs/automagik-hive) agents
- **🐳 Deployment Flexible**: Docker, PM2, systemd—deploy however you prefer

### 📱 Supported Channels

| Channel | Status | Features |
|---------|--------|----------|
| **WhatsApp** | ✅ Production | Text, media, audio, stickers, reactions, presence, QR login via Evolution API |
| **Discord** | ✅ Production | Multi-server, text, attachments, voice infrastructure, bot + IPC architecture |
| **Slack** | 🔄 Q4 2025 | Full workspace integration with threads and reactions |
| **WhatsApp Business** | 🔄 Q4 2025 | Business API with Flows for structured interactions |
| **Instagram Direct** | 📅 Q1 2026 | DMs, stories, and engagement |
| **Telegram** | 📅 Q1 2026 | Bots, channels, and groups |
| **Microsoft Teams** | 📅 Q1 2026 | Enterprise collaboration |
| **LinkedIn Messages** | 📅 2026-2027 | Professional networking |
| **WeChat** | 📅 2026-2027 | China market access |
| **TikTok DMs** | 📅 2026-2027 | Short-form social engagement |
| **SMS Gateway** | 📅 2026-2027 | Universal text messaging |

### 🧩 Integrations

Works seamlessly with the Automagik ecosystem:

- **[Automagik Hive](https://github.com/namastexlabs/automagik-hive)**: Multi-agent orchestration with streaming SSE
- **[Automagik Spark](https://github.com/namastexlabs/automagik-spark)**: Scheduled messaging and workflows
- **[Automagik Tools](https://github.com/namastexlabs/automagik-tools)**: MCP tools for enhanced agent capabilities
- **Any OpenAPI-Compatible Agent**: Bring your own agent with standard HTTP APIs

---

## 📦 Quick Start

### Prerequisites

- **Python 3.12+** (3.11+ supported)
- **PostgreSQL** (recommended) or **SQLite** (for development)
- **Node.js 20+** (for Evolution API - WhatsApp integration)
- **Discord Bot Token** (optional, for Discord) - [Create here](https://discord.com/developers/applications)

> **Note**: Evolution API (WhatsApp) is included as a git submodule with SQLite support - no Docker required!

### Installation

```bash
# 1. Clone with submodules (includes Evolution API for WhatsApp)
git clone --recurse-submodules https://github.com/namastexlabs/automagik-omni.git
cd automagik-omni

# 2. Run the setup script (installs everything)
./update-automagik-omni.sh
# This installs Python deps, Evolution API deps, and runs migrations

# 3. Configure your API keys
cp .env.example .env
nano .env  # Set EVOLUTION_API_KEY and AUTOMAGIK_OMNI_API_KEY

# 4. Start all services with PM2
pm2 start ecosystem.config.js

# ✅ Done! Services running:
# - Omni API: http://localhost:8882
# - Evolution API (WhatsApp): http://localhost:18082
```

**What gets installed:**
- ✅ **Omni Backend** - Multi-tenant messaging hub (Python/FastAPI)
- ✅ **Evolution API** - WhatsApp integration with SQLite (no Docker!)
- ✅ **Health Checks** - Ensures services start in correct order
- ✅ **Discord Manager** - Multi-bot Discord integration (optional)

### Your First Message in 60 Seconds

#### Quick Start with Defaults

Use this curl command to create your first instance with local Evolution API:

```bash
# Create instance with local Evolution API (started via PM2)
curl -X POST http://localhost:8882/api/v1/instances \
  -H "x-api-key: YOUR_OMNI_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-bot",
    "channel_type": "whatsapp",
    "evolution_url": "http://localhost:18082",
    "evolution_key": "YOUR_EVOLUTION_API_KEY_HERE",
    "agent_api_url": "http://localhost:8886",
    "agent_api_key": "YOUR_AGENT_API_KEY_HERE",
    "default_agent": "template-agent"
  }'
```

**Replace the placeholders:**
- `YOUR_OMNI_API_KEY_HERE` → Value from `AUTOMAGIK_OMNI_API_KEY` in your `.env`
- `YOUR_EVOLUTION_API_KEY_HERE` → Value from `EVOLUTION_API_KEY` in your `.env`
- `YOUR_AGENT_API_KEY_HERE` → Your AI agent's API key (e.g., Automagik Hive)

**Default ports:**
- **Evolution API** (WhatsApp): `localhost:18082`
- **Omni API**: `localhost:8882`
- **Automagik Hive** (optional): `localhost:8886`

#### Complete Example

```bash
# Check health
curl http://localhost:8882/health
# {"status": "healthy"}

# Get QR code to connect WhatsApp
curl http://localhost:8882/api/v1/instances/my-first-bot/qr \
  -H "x-api-key: YOUR_OMNI_API_KEY_HERE"
# Scan with WhatsApp → Connected!

# Send a test message
curl -X POST http://localhost:8882/api/v1/instances/my-first-bot/send-text \
  -H "x-api-key: YOUR_OMNI_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890",
    "message": "🎉 Hello from Automagik Omni!"
  }'
```

**That's it!** Your agent is now live and responding on WhatsApp.

> **Security Note**: Always use strong, unique API keys in production. Never commit real keys to git.

---

## 🏗️ Architecture

### How Omni Works

```
┌─────────────────────────────────────────────────────────────┐
│                         OMNI HUB                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌───────────────┐      ┌──────────┐ │
│  │   WhatsApp   │─────▶│   Instance    │─────▶│   AI     │ │
│  │   Webhook    │      │   Manager     │      │  Agent   │ │
│  └──────────────┘      └───────────────┘      └──────────┘ │
│                               │                              │
│  ┌──────────────┐             │                              │
│  │   Discord    │─────────────┤                              │
│  │   Bot + IPC  │             │                              │
│  └──────────────┘             │                              │
│                         ┌─────▼──────┐                       │
│  ┌──────────────┐      │   Message   │      ┌──────────┐   │
│  │   Slack      │─────▶│   Router    │─────▶│  Trace   │   │
│  │   (Soon)     │      │  & Handler  │      │  Store   │   │
│  └──────────────┘      └─────────────┘      └──────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Instance Manager**: Multi-tenant instance management with complete isolation
2. **Channel Handler Factory**: Pluggable architecture for platform-specific logic
3. **Message Router**: Validates, enriches, and routes messages to appropriate agents
4. **Trace System**: Complete message lifecycle tracking with performance metrics
5. **MCP Server**: Remote control interface for AI coding agents

### Message Flow

```
User sends message → Platform webhook → Omni validates
                                      ↓
                              Access control check
                                      ↓
                              Route to AI agent
                                      ↓
                              Agent processes (with streaming support)
                                      ↓
                              Format for platform
                                      ↓
                              Send via channel
                                      ↓
                              Store trace for analytics
```

---

## 🤖 MCP: Control from Anywhere

Automagik Omni includes a **Model Context Protocol (MCP) server**, enabling AI agents to programmatically manage messaging instances and send messages.

### Available MCP Tools

| Tool | Description | Operations |
|------|-------------|------------|
| `manage_instances` | Instance CRUD operations | list, get, create, update, delete, status, qr, restart, logout |
| `send_message` | Send messages to any channel | text, media, audio, sticker, contact, reaction |
| `manage_traces` | Message history and analytics | list, get, analytics, cleanup |
| `manage_profiles` | User profile management | fetch, update_picture |

### Quick MCP Setup

<details>
<summary><b>🤖 Claude Code Configuration</b></summary>

Add to your Claude Code MCP servers configuration:

```json
{
  "mcpServers": {
    "omni": {
      "command": "uvx",
      "args": ["--from", "automagik-omni", "mcp-server-omni"],
      "env": {
        "OMNI_URL": "http://localhost:8000",
        "OMNI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Usage:**
```
"List all my messaging instances"
"Send a WhatsApp message to +1234567890: Hello!"
"Show me message analytics for the last 24 hours"
```

</details>

<details>
<summary><b>🎯 Cursor Configuration</b></summary>

Add to Cursor's MCP settings:

```json
{
  "mcp.servers": {
    "omni": {
      "command": "uvx",
      "args": ["--from", "automagik-omni", "mcp-server-omni"],
      "env": {
        "OMNI_URL": "http://localhost:8000",
        "OMNI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

</details>

<details>
<summary><b>📝 VSCode + Cline Configuration</b></summary>

For the Cline extension:

```json
{
  "cline.mcpServers": [
    {
      "name": "omni",
      "command": "uvx",
      "args": ["--from", "automagik-omni", "mcp-server-omni"],
      "env": {
        "OMNI_URL": "http://localhost:8000",
        "OMNI_API_KEY": "your-api-key-here"
      }
    }
  ]
}
```

</details>

<details>
<summary><b>🔧 Generic MCP Configuration</b></summary>

For any MCP-compatible tool:

```json
{
  "command": "uvx",
  "args": ["--from", "automagik-omni", "mcp-server-omni"],
  "env": {
    "OMNI_URL": "http://localhost:8000",
    "OMNI_API_KEY": "your-api-key-here"
  }
}
```

</details>

### MCP Usage Examples

```bash
# From Claude Code or any MCP client

"Create a new WhatsApp instance named 'support-bot'"
→ Uses manage_instances to create and configure

"Send a message to customer +5511999999999: Your order has shipped!"
→ Uses send_message with proper formatting

"Show me all failed messages from yesterday"
→ Uses manage_traces with filters

"Get QR code for my WhatsApp instance 'sales-team'"
→ Uses manage_instances(operation="qr")
```

---

## 🛠️ API Reference

### Core Endpoints

#### Instance Management

```http
# List all instances
GET /api/v1/instances
Headers: x-api-key: your-key

# Create new instance
POST /api/v1/instances
{
  "name": "my-bot",
  "channel_type": "whatsapp|discord",
  "evolution_url": "https://...",  # WhatsApp only
  "evolution_api_key": "...",      # WhatsApp only
  "discord_token": "...",          # Discord only
  "agent_url": "https://your-agent.com/chat",
  "agent_api_key": "optional"
}

# Get instance details
GET /api/v1/instances/{name}

# Update instance
PATCH /api/v1/instances/{name}
{
  "agent_url": "https://new-endpoint.com"
}

# Delete instance
DELETE /api/v1/instances/{name}
```

#### Channel Operations

```http
# Get WhatsApp QR Code
GET /api/v1/instances/{name}/qr

# Check connection status
GET /api/v1/instances/{name}/status

# Restart connection
POST /api/v1/instances/{name}/restart

# Logout/disconnect
POST /api/v1/instances/{name}/logout
```

#### Messaging

```http
# Send text message
POST /api/v1/instances/{name}/send-text
{
  "phone": "+1234567890",
  "message": "Hello!",
  "quoted_message_id": "optional"
}

# Send media (image, video, document)
POST /api/v1/instances/{name}/send-media
{
  "phone": "+1234567890",
  "media_url": "https://example.com/image.jpg",
  "media_type": "image|video|document",
  "caption": "Optional caption"
}

# Send audio/voice note
POST /api/v1/instances/{name}/send-audio
{
  "phone": "+1234567890",
  "audio_url": "https://example.com/audio.mp3"
}

# Send reaction
POST /api/v1/instances/{name}/send-reaction
{
  "phone": "+1234567890",
  "message_id": "message-to-react-to",
  "emoji": "👍"
}
```

#### Traces & Analytics

```http
# List message traces
GET /api/v1/traces?instance_name=my-bot&limit=50

# Get specific trace
GET /api/v1/traces/{trace_id}

# Analytics summary
GET /api/v1/traces/analytics/summary?start_date=2025-01-01

# Cleanup old traces
POST /api/v1/traces/cleanup
{
  "days_old": 30,
  "dry_run": false
}
```

### Authentication

All API requests require the `x-api-key` header:

```bash
curl -H "x-api-key: your-secret-key" \
  http://localhost:8000/api/v1/instances
```

Set your API key in `.env`:
```env
OMNI_API_KEY=your-super-secret-key-here
```

---

## 🎯 Agent Integration

### Automagik Hive (Recommended)

Omni has first-class support for [Automagik Hive](https://github.com/namastexlabs/automagik-hive) with **streaming Server-Sent Events**:

```python
# Hive agent responds with SSE streaming
# Omni automatically:
# 1. Buffers the stream
# 2. Formats for the target channel
# 3. Sends when complete
# 4. Handles errors gracefully

# Just point agent_url to your Hive endpoint!
```

### Custom HTTP Agent

Any agent that accepts HTTP POST with JSON:

```json
POST https://your-agent.com/chat
Content-Type: application/json

{
  "message": "User's message",
  "user_id": "platform:user_id",
  "platform": "whatsapp|discord",
  "context": {
    "phone": "+1234567890",
    "instance_name": "my-bot"
  }
}

Response:
{
  "response": "Agent's reply message"
}
```

### OpenAPI-Compatible Agent

If your agent has an OpenAPI spec, it just works:

```bash
# Create instance pointing to any OpenAPI endpoint
curl -X POST http://localhost:8000/api/v1/instances \
  -H "x-api-key: your-key" \
  -d '{
    "agent_url": "https://api.yourservice.com/v1/chat",
    "agent_api_key": "service-api-key"
  }'
```

---

## 🗺️ Roadmap

### Q4 2025 - Foundation Strengthening

- 🎯 **Robustness & Scale**: Performance beyond Evolution API limitations
- 📋 **Access Control**: Whitelist/blacklist for user management
- 💼 **WhatsApp Business API**: Flows for structured interactions
- 💬 **Slack Integration**: Full workspace support with threads
- 🔄 **Fallback System**: Multiple WhatsApp engines for redundancy

### Q1-Q2 2026 - Channel Expansion

- 📱 **Instagram Direct**: DMs, stories, engagement
- ✈️ **Telegram**: Bots, channels, groups
- 👔 **Microsoft Teams**: Enterprise collaboration
- 🌐 **Meta Messenger**: Facebook messaging
- 🌟 **Unified User Management**: Link users across platforms
- 🧠 **True Omnipresence**: Shared context across all channels

### 2026-2027 - Global Scale

- 💼 **LinkedIn Messages**: Professional networking
- 🇨🇳 **WeChat**: China market access
- 🎵 **TikTok DMs**: Short-form social engagement
- 📱 **SMS Gateway**: Universal text messaging
- 🔌 **Open Architecture**: Plugin system for any messaging platform
- 🌍 **Enterprise Features**: SSO, audit logs, compliance tools

---

## 🚀 Development

### Local Development

```bash
# Start with hot reload
make dev

# Run tests
make test

# View logs
make logs

# Check code quality
make lint
make format

# Database operations
make migrate        # Run migrations
make db-reset      # Reset database (caution!)
make db-shell      # Open database shell
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f omni-api

# Restart services
docker-compose restart

# Stop everything
docker-compose down
```

### Production Deployment with PM2

```bash
# Install PM2
npm install -g pm2

# Start all services
pm2 start ecosystem.config.js

# Monitor
pm2 monit

# View logs
pm2 logs omni-api

# Restart
pm2 restart all

# Stop
pm2 stop all
```

### Environment Variables

Key configuration options (see `.env.example` for complete list):

```env
# Omni API Configuration
AUTOMAGIK_OMNI_API_HOST=0.0.0.0
AUTOMAGIK_OMNI_API_PORT=8882
AUTOMAGIK_OMNI_API_KEY=CHANGE-THIS-TO-SECURE-KEY

# Database (SQLite for development)
AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH=./data/automagik-omni.db
# Or PostgreSQL for production:
# AUTOMAGIK_OMNI_DATABASE_URL=postgresql://user:pass@localhost:5432/automagik_omni

# Evolution API (WhatsApp - runs locally via PM2)
EVOLUTION_API_PATH=resources/evolution-api
EVOLUTION_API_URL=http://localhost:18082
EVOLUTION_API_PORT=18082
EVOLUTION_API_KEY=CHANGE-THIS-TO-SECURE-KEY
EVOLUTION_LOG_LEVEL=ERROR,WARN

# Discord (optional)
DISCORD_TOKEN=YOUR-DISCORD-BOT-TOKEN-HERE

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

> **Important**: Generate strong, unique API keys for production. Never use default values!

---

## 🤝 Contributing

We love contributions! Here's how to get started:

### Quick Contribution Guide

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create** a feature branch: `git checkout -b feature/amazing-feature`
4. **Make** your changes
5. **Test** thoroughly: `make test`
6. **Commit** with conventional commits: `feat: add slack integration`
7. **Push** to your fork: `git push origin feature/amazing-feature`
8. **Open** a Pull Request with clear description

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/automagik-omni.git
cd automagik-omni

# Install dependencies with UV (recommended)
make install

# Create .env file
cp .env.example .env

# Run migrations
make migrate

# Start development server
make dev

# Run tests before committing
make test
make lint
```

### Contribution Guidelines

- Follow existing code style (use `make format`)
- Write tests for new features
- Update documentation
- Use conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)
- Keep PRs focused on a single feature/fix

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 🙏 Acknowledgments

Special thanks to:

- **Evolution API Team**: For excellent WhatsApp infrastructure
- **Discord.py Community**: For the powerful bot framework
- **Automagik Community**: Early adopters and contributors
- **FastAPI Team**: For the amazing Python web framework

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **GitHub**: [github.com/namastexlabs/automagik-omni](https://github.com/namastexlabs/automagik-omni)
- **Discord**: [discord.gg/xcW8c7fF3R](https://discord.gg/xcW8c7fF3R)
- **Twitter**: [@namastexlabs](https://twitter.com/namastexlabs)
- **DeepWiki Docs**: [deepwiki.com/namastexlabs/automagik-omni](https://deepwiki.com/namastexlabs/automagik-omni)

---

<p align="center">
  <strong>🌐 Connect your AI to every messaging platform with one integration</strong><br>
  <strong>The omnipresent hub that just works™</strong><br><br>
  <a href="https://github.com/namastexlabs/automagik-omni">Star us on GitHub</a> •
  <a href="https://discord.gg/xcW8c7fF3R">Join our Discord</a>
</p>

<p align="center">
  Made with ❤️ by <a href="https://namastex.ai">Namastex Labs</a><br>
  <em>AI that elevates human potential, not replaces it</em>
</p>
<a href="https://deepwiki.com/namastexlabs/automagik-omni"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>