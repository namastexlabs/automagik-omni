# Automagik Omni - Complete Feature Documentation

## 🎯 Executive Overview

**Automagik Omni** is an enterprise-grade, multi-tenant omnichannel messaging platform that serves as the bridge between AI agents and real-world messaging platforms. It enables organizations to deploy intelligent conversational AI across WhatsApp, Discord, and other messaging channels with complete isolation between instances.

### Core Value Proposition
- **Unified AI-to-Human Communication**: Single platform for all messaging channels
- **Multi-Tenant Architecture**: Complete isolation between clients/teams/use cases
- **Enterprise Scalability**: Support for 100+ concurrent instances
- **Real-Time Processing**: Sub-second message routing and response
- **Complete Traceability**: Full message lifecycle tracking and analytics

## 🏗️ System Architecture

### Multi-Tenant Design
The system implements **instance-based multi-tenancy** where each instance represents:
- A separate client organization
- An isolated team within an organization
- A specific use case or project
- A development/staging/production environment

Each instance maintains:
- **Complete Configuration Isolation**: Separate API keys, endpoints, and settings
- **Independent Agent Routing**: Different AI agents per instance
- **Isolated Message History**: No cross-instance data leakage
- **Separate Connection Management**: Independent channel connections

### Technology Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: SQLAlchemy ORM with PostgreSQL/SQLite
- **Process Management**: PM2 for production deployment
- **Authentication**: Bearer token with API key validation
- **Real-Time**: WebSocket support for streaming
- **Testing**: pytest with comprehensive coverage

## 📱 Messaging Channel Integrations

### 1. WhatsApp Integration (via Evolution API)

#### Connection Methods
- **QR Code Authentication**: Generate and scan QR codes for device linking
- **API Key Management**: Secure Evolution API integration
- **Instance Lifecycle**: Connect, disconnect, restart capabilities

#### Message Types Supported
- **Text Messages**: Plain text with emoji support
- **Media Messages**: 
  - Images (JPEG, PNG, GIF)
  - Videos (MP4, AVI, MOV)
  - Audio (MP3, OGG, WAV)
  - Documents (PDF, DOC, XLSX)
- **Voice Messages**: Audio recording and transcription
- **Contact Cards**: Share contact information
- **Reactions**: Emoji reactions to messages
- **Mentions**: @mentions with proper parsing
- **Quoted Messages**: Reply to specific messages

#### Advanced Features
- **Audio Transcription**: Automatic voice-to-text conversion
- **Media Encryption/Decryption**: Secure media handling
- **Streaming Support**: Real-time message delivery
- **Session Management**: Persistent conversation contexts
- **User Identity Tracking**: Stable user IDs across sessions

#### Configuration
```json
{
  "evolution_url": "https://your-evolution-api.com",
  "evolution_api_key": "your-api-key",
  "instance_name": "production-whatsapp"
}
```

### 2. Discord Integration

#### Bot Capabilities
- **Multi-Server Support**: Single bot across multiple Discord servers
- **Channel Management**: Text and voice channel operations
- **Slash Commands**: Interactive command system
- **Rich Embeds**: Advanced message formatting

#### Voice Features
- **Voice Channel Support**: Join/leave voice channels
- **Speech-to-Text**: Voice message transcription
- **Text-to-Speech**: Audio response generation
- **Voice Activity Detection**: Automatic speech detection

#### Resilience Features
- **Circuit Breaker Pattern**: Automatic recovery from failures
- **Rate Limiting**: Prevent API throttling
- **Connection Management**: Auto-reconnect on disconnect
- **Health Monitoring**: Real-time bot status tracking

#### Configuration
```json
{
  "discord_bot_token": "your-bot-token",
  "discord_application_id": "your-app-id",
  "voice_enabled": true
}
```

### 3. Extensible Channel Support

The platform is designed for easy extension with:
- **Channel Factory Pattern**: Register new channel handlers
- **Abstract Base Classes**: Implement standard interface
- **Unified Configuration**: Channel-agnostic setup

Ready for integration:
- Slack (workspace and DM support)
- Microsoft Teams (channels and chats)
- Telegram (bots and channels)
- Custom webhook endpoints

## 🤖 AI Agent Integration

### Dual Agent System Support

#### 1. Automagik Agent Integration
- **Session Persistence**: Maintain conversation context
- **User Mapping**: Phone-to-agent user ID mapping
- **Tool Support**: Handle agent tool calls
- **Custom Timeouts**: Configurable request timeouts

Configuration:
```json
{
  "agent_instance_type": "automagik",
  "agent_api_url": "https://agent-api.com",
  "agent_api_key": "secure-key",
  "agent_id": "agent-123",
  "timeout": 60
}
```

#### 2. AutomagikHive Integration
- **Team Coordination**: Multi-agent team support
- **Streaming Mode**: Real-time response streaming
- **Advanced Configuration**: Granular timeout/retry settings
- **Backward Compatibility**: Legacy field migration

Configuration:
```json
{
  "agent_instance_type": "hive",
  "agent_api_url": "https://hive-api.com",
  "agent_api_key": "secure-key",
  "agent_id": "team-456",
  "agent_stream_mode": true
}
```

### Agent Communication Flow
1. **Message Reception**: Incoming message from channel
2. **User Context Loading**: Retrieve user session and history
3. **Agent Processing**: Send to configured AI agent
4. **Response Handling**: Process agent response
5. **Channel Delivery**: Send response back to user
6. **Trace Recording**: Log complete interaction

## 🛠️ API Endpoints & Operations

### Instance Management (`/api/v1/instances/`)

#### Create Instance
`POST /api/v1/instances/`
```json
{
  "name": "production-support",
  "channel_type": "whatsapp",
  "evolution_url": "https://evolution-api.com",
  "evolution_api_key": "key-123",
  "agent_api_url": "https://agent.com",
  "agent_api_key": "agent-key"
}
```

#### List Instances
`GET /api/v1/instances/`
- Returns all configured instances
- Shows connection status
- Displays message counts

#### Update Instance
`PUT /api/v1/instances/{name}`
- Modify configuration
- Change agent endpoints
- Update API keys

#### Delete Instance
`DELETE /api/v1/instances/{name}`
- Remove instance completely
- Clean up associated data

#### Instance Operations
- `POST /api/v1/instances/{name}/connect` - Connect to channel
- `POST /api/v1/instances/{name}/disconnect` - Disconnect from channel
- `POST /api/v1/instances/{name}/restart` - Restart connection
- `GET /api/v1/instances/{name}/qr` - Get WhatsApp QR code
- `GET /api/v1/instances/{name}/status` - Check connection status

### Messaging Operations (`/api/v1/instance/{name}/`)

#### Send Text Message
`POST /api/v1/instance/{name}/send/text`
```json
{
  "phone": "+1234567890",
  "message": "Hello from Automagik!"
}
```

#### Send Media Message
`POST /api/v1/instance/{name}/send/media`
```json
{
  "phone": "+1234567890",
  "media_url": "https://example.com/image.jpg",
  "media_type": "image",
  "caption": "Check this out!"
}
```

#### Send Audio Message
`POST /api/v1/instance/{name}/send/audio`
```json
{
  "phone": "+1234567890",
  "audio_url": "https://example.com/voice.mp3"
}
```

#### Send Contact
`POST /api/v1/instance/{name}/send/contact`
```json
{
  "phone": "+1234567890",
  "contacts": [{
    "full_name": "John Doe",
    "phone_number": "+9876543210"
  }]
}
```

### Trace & Analytics (`/api/v1/traces/`)

#### List Traces
`GET /api/v1/traces/`
Query parameters:
- `instance_name`: Filter by instance
- `phone`: Filter by phone number
- `status`: Filter by status (received, processing, completed, failed)
- `start_date`/`end_date`: Date range filtering
- `limit`/`offset`: Pagination

#### Get Trace Details
`GET /api/v1/traces/{trace_id}`
Returns:
- Complete message lifecycle
- Processing times
- Error details if any
- Payload data (compressed)

#### Analytics Dashboard
`GET /api/v1/traces/analytics`
Returns:
- Message volume metrics
- Response time statistics
- Success/failure rates
- Per-instance breakdown

#### Cleanup Old Traces
`DELETE /api/v1/traces/cleanup`
Parameters:
- `days_old`: Delete traces older than X days
- `dry_run`: Preview without deletion

### Profile Management (`/api/v1/profiles/`)

#### Fetch User Profile
`GET /api/v1/profiles/fetch`
```json
{
  "instance_name": "production",
  "phone_number": "+1234567890"
}
```

#### Update Profile Picture
`POST /api/v1/profiles/update_picture`
```json
{
  "instance_name": "production",
  "picture_url": "https://example.com/avatar.jpg"
}
```

### System Operations

#### Health Check
`GET /health`
Returns:
- API status
- Database connectivity
- Evolution API status
- Active instance count

#### Metrics
`GET /metrics`
Returns:
- Request counts
- Response times
- Error rates
- System resources

## 📊 Message Tracing System

### Trace Lifecycle Stages

1. **WEBHOOK_RECEIVED**: Initial message reception
   - Timestamp recording
   - User identification
   - Message type detection

2. **AGENT_REQUEST**: Sending to AI agent
   - Session loading
   - Context preparation
   - Request timestamp

3. **AGENT_RESPONSE**: Agent reply received
   - Response processing
   - Media handling
   - Processing time calculation

4. **EVOLUTION_SENT**: Message sent to user
   - Delivery confirmation
   - Total time calculation
   - Success/failure recording

### Trace Data Structure
```python
{
  "trace_id": "uuid-v4",
  "whatsapp_message_id": "message-id",
  "sender_phone": "+1234567890",
  "sender_name": "John Doe",
  "message_type": "text|image|audio|video|document",
  "message_content": "Hello!",
  "instance_name": "production",
  "session_name": "session-123",
  "status": "completed",
  "agent_processing_time_ms": 1250,
  "total_processing_time_ms": 1500,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Analytics Capabilities
- **Performance Monitoring**: Track response times
- **Volume Analysis**: Message counts per instance/user
- **Error Tracking**: Identify failure patterns
- **User Behavior**: Conversation patterns and frequency
- **Agent Performance**: Processing time analysis

## 🔐 Security & Authentication

### API Authentication
- **Bearer Token Scheme**: Standard OAuth-style authentication
- **API Key Validation**: Configurable master API key
- **Development Mode**: Auto-bypass for local development
- **Request Logging**: All API calls logged for audit

### Data Protection
- **Payload Compression**: zlib compression for sensitive data
- **API Key Masking**: Partial key exposure in logs
- **Input Validation**: Pydantic schema validation
- **SQL Injection Prevention**: ORM-based queries

### Instance Isolation
- **Database Isolation**: Separate configurations per instance
- **API Key Scoping**: Instance-specific API keys
- **Channel Isolation**: No cross-instance message routing
- **User Data Separation**: Complete user data isolation

## 🚀 Deployment & Operations

### Process Management (PM2)
```javascript
// ecosystem.config.js
{
  name: 'automagik-omni-api',
  script: 'python',
  args: '-m uvicorn src.main:app',
  instances: 4,
  exec_mode: 'cluster',
  env: {
    PORT: 3210,
    DATABASE_URL: 'postgresql://...'
  }
}
```

### Deployment Commands
```bash
# Start API
pm2 start ecosystem.config.js

# View logs
pm2 logs automagik-omni-api --nostream

# Restart
pm2 restart automagik-omni-api

# Monitor
pm2 monit
```

### Database Management
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback
alembic downgrade -1
```

### Health Monitoring
- **Endpoint**: `GET /health`
- **Checks**: Database, Evolution API, Discord bots
- **Response Time**: <100ms expected
- **Auto-restart**: PM2 handles process failures

## 🧪 Testing & Quality

### Test Coverage Areas
- **Integration Tests**: End-to-end API testing
- **Database Tests**: Model validation and migrations
- **Channel Tests**: WhatsApp and Discord handlers
- **Agent Tests**: AI agent communication
- **Trace Tests**: Message lifecycle tracking

### Quality Tools
```bash
# Run tests
pytest tests/ -v --cov

# Code formatting
ruff format src/

# Linting
ruff check src/

# Type checking
mypy src/
```

## 📈 Performance Characteristics

### System Capacity
| Metric | Development | Production |
|--------|------------|------------|
| Concurrent Instances | 10+ | 100+ |
| Messages/Second | 50 | 500+ |
| Response Time | <100ms | <300ms |
| Database Connections | 10 | 50 |
| Memory Usage | 200MB | 2GB |

### Optimization Features
- **Connection Pooling**: Efficient database connections
- **Async Processing**: Non-blocking I/O operations
- **Payload Compression**: Reduced storage requirements
- **Caching**: Session and user data caching
- **Batch Operations**: Bulk message processing

## 🔄 MCP (Model Context Protocol) Integration

### Available MCP Tools

#### manage_instances
Manage messaging instances programmatically:
- List all instances with status
- Create/update/delete instances
- Connect/disconnect instances
- Get QR codes for WhatsApp

#### send_message
Send messages through any instance:
- Text, media, audio messages
- Contact cards and reactions
- Cross-platform support

#### manage_traces
Access message analytics:
- Query message history
- Performance metrics
- Cleanup operations

#### manage_profiles
User profile operations:
- Fetch user information
- Update profile pictures

### MCP Configuration
```json
{
  "mcpServers": {
    "omni": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "env": {
        "DATABASE_URL": "sqlite:///data/omni.db"
      }
    }
  }
}
```

## 🎯 Use Cases & Implementation Examples

### 1. Customer Support Bot
```python
# Configure instance for support
{
  "name": "customer-support",
  "channel_type": "whatsapp",
  "agent_api_url": "https://support-ai.com",
  "agent_id": "support-bot-v2"
}
```

### 2. Multi-Channel Marketing
```python
# WhatsApp instance
{
  "name": "marketing-whatsapp",
  "channel_type": "whatsapp"
}

# Discord instance
{
  "name": "marketing-discord",
  "channel_type": "discord"
}
```

### 3. Internal Team Assistant
```python
# Slack integration (when available)
{
  "name": "team-assistant",
  "channel_type": "slack",
  "agent_type": "team"
}
```

### 4. Development/Staging/Production
```python
# Separate instances per environment
{
  "name": "dev-bot",
  "name": "staging-bot",
  "name": "prod-bot"
}
```

## 🚨 Important Operational Notes

### WhatsApp Considerations
- **QR Code Expiry**: QR codes expire after 60 seconds
- **Rate Limiting**: Evolution API has rate limits
- **Media Size Limits**: Maximum 16MB for media files
- **Session Persistence**: Sessions maintained for 24 hours

### Discord Considerations
- **Bot Token Security**: Never expose bot tokens
- **Guild Permissions**: Bot needs appropriate permissions
- **Rate Limiting**: Discord API has strict rate limits
- **Voice Latency**: Voice channels add 50-200ms latency

### Database Maintenance
- **Trace Cleanup**: Run cleanup weekly for old traces
- **Index Optimization**: Monitor query performance
- **Backup Strategy**: Regular backups recommended
- **Migration Testing**: Test migrations in staging first

## 📚 Getting Started Guide

### 1. Initial Setup
```bash
# Clone repository
git clone https://github.com/namastexlabs/automagik-omni.git

# Install dependencies
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 2. Create First Instance
```bash
# Using CLI
python -m src.cli.omni_cli instance create \
  --name "my-first-bot" \
  --channel-type whatsapp \
  --evolution-url "https://evolution-api.com" \
  --evolution-api-key "your-key"
```

### 3. Connect WhatsApp
```bash
# Get QR code
python -m src.cli.omni_cli instance qr my-first-bot

# Or use API
curl -X GET "http://localhost:3210/api/v1/instances/my-first-bot/qr"
```

### 4. Start Processing Messages
```bash
# Start API server
pm2 start ecosystem.config.js

# Monitor logs
pm2 logs automagik-omni-api --nostream
```

### 5. Send Test Message
```bash
# Using MCP
mcp omni send_message \
  --message_type text \
  --phone "+1234567890" \
  --message "Hello from Automagik Omni!"
```

## 🎉 Summary

Automagik Omni provides a complete, production-ready platform for omnichannel AI-powered messaging with:

✅ **Multi-tenant architecture** for complete instance isolation
✅ **WhatsApp and Discord** support with more channels coming
✅ **Dual AI agent** integration (Automagik and Hive)
✅ **Complete message tracing** and analytics
✅ **Enterprise-grade security** and authentication
✅ **Scalable architecture** supporting 100+ instances
✅ **Comprehensive API** for all operations
✅ **MCP integration** for Claude Code
✅ **Production deployment** with PM2
✅ **Extensive testing** and quality assurance

The platform is designed for reliability, scalability, and extensibility, making it suitable for everything from small projects to enterprise deployments.