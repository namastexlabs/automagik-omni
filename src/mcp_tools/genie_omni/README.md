# Genie Omni - Agent-First WhatsApp Communication

**Your personal hub to the digital world.**

## Philosophy

This tool is designed from Genie's perspective, not an API wrapper perspective.

**OLD (API-centric):**
- `manage_instances()` - Administrative thinking
- `manage_traces()` - Database thinking
- `send_message()` - Generic API thinking

**NEW (Agent-centric):**
- `my_whatsapp_info()` - Identity thinking ("Who am I?")
- `send_whatsapp()` - Action thinking ("What do I do?")
- `read_messages()` - Context thinking ("What happened?")

## Design Principles

1. **Agent-First**: Tools from AI agent's perspective, not developer's
2. **Natural Language**: Friendly, conversational tool descriptions
3. **Zero Configuration**: Smart defaults (instance_name="genie")
4. **Full Functionality**: No features lost from original omni tool
5. **No Backwards Compatibility**: Clean slate, better design

## Tool Categories

### 1. WHO AM I (Identity & Context)
- `my_whatsapp_info()` - Get MY WhatsApp number and status
- `my_contacts()` - People I can message
- `my_conversations()` - Active chats

### 2. SEND (Active Communication)
- `send_whatsapp()` - Send message (text/media/audio)
- `react_with()` - React with emoji

### 3. READ (Consume Context)
- `read_messages()` - Read messages from someone
- `check_new_messages()` - Check recent messages

### 4. SEARCH (Find Information)
- `find_message()` - Get message details by trace ID
- `find_person()` - Search contacts

### 5. ADMIN (Manage Connections)
- `my_connections()` - List WhatsApp instances
- `connection_status()` - Check connection status

## Schema Fixes Included

This version includes fixes for all schema validation bugs:

1. **TracePayloadResponse** - Fixed field types (id: int, stage: str, timestamp: str)
2. **ChatResponse** - Fixed unread_count to be Optional[int]
3. All schemas now match Omni backend exactly

## Environment Variables

```bash
OMNI_API_KEY=your_api_key
OMNI_BASE_URL=http://localhost:8882
OMNI_DEFAULT_INSTANCE=genie
```

## Usage Example

```python
# Agent perspective - natural and friendly
await send_whatsapp(
    to="5511999999999",
    message="Hello! Finished the bug analysis."
)

# Get my contacts
contacts = await my_contacts()

# Read recent messages
messages = await read_messages(
    from_number="5511999999999",
    limit=10
)
```

## Integration Notes

- Uses FastMCP for MCP server implementation
- Async client for Omni Hub API
- Pydantic models for validation
- Ready to publish in automagik-tools
