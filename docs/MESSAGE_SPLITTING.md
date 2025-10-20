# Message Splitting Configuration

## Overview

Automagik Omni provides configurable message splitting controls at both the instance level and per-message level. This feature allows you to control how long messages are automatically split before being sent to different channels.

## Configuration Levels

### 1. Instance-Level Configuration

Control the default splitting behavior for an entire instance using the `enable_auto_split` field.

**Database Field**: `InstanceConfig.enable_auto_split`
- **Type**: Boolean
- **Default**: `True` (maintains backward compatibility)
- **Scope**: Applies to all messages sent through the instance unless overridden

**API Endpoints**:

#### Create Instance with Splitting Control
```http
POST /api/v1/instances
Content-Type: application/json
x-api-key: your-api-key

{
  "name": "my-bot",
  "channel_type": "whatsapp",
  "enable_auto_split": false,
  "evolution_url": "https://...",
  "evolution_key": "...",
  "agent_api_url": "https://...",
  "agent_api_key": "..."
}
```

#### Update Instance Splitting Behavior
```http
PATCH /api/v1/instances/my-bot
Content-Type: application/json
x-api-key: your-api-key

{
  "enable_auto_split": false
}
```

#### Query Instance Configuration
```http
GET /api/v1/instances/my-bot
x-api-key: your-api-key
```

Response includes:
```json
{
  "id": 1,
  "name": "my-bot",
  "enable_auto_split": false,
  ...
}
```

### 2. Per-Message Configuration

Override the instance-level setting for individual messages using the `split_message` parameter.

**API Field**: `split_message`
- **Type**: Optional[bool]
- **Default**: `None` (uses instance config)
- **Scope**: Applies only to the specific message being sent

**Example**:
```http
POST /api/v1/instances/my-bot/send-text
Content-Type: application/json
x-api-key: your-api-key

{
  "phone": "+5511999999999",
  "text": "Long message with\n\nmultiple paragraphs",
  "split_message": false
}
```

## Priority Logic

The system uses the following priority order to determine splitting behavior:

1. **Per-message override** (`split_message` parameter)
2. **Instance configuration** (`enable_auto_split` field)
3. **Default behavior** (`True`)

### Example Scenarios

| Instance `enable_auto_split` | Message `split_message` | Result |
|------------------------------|-------------------------|--------|
| `True` | `None` | Split enabled |
| `False` | `None` | Split disabled |
| `True` | `False` | Split disabled (override) |
| `False` | `True` | Split enabled (override) |
| `None`/not set | `None` | Split enabled (default) |

## Platform-Specific Behavior

### WhatsApp

**Complete control over message splitting**

- **When enabled** (`True`):
  - Messages are split at `\n\n` (double newline) boundaries
  - Each segment sent as a separate message
  - Maintains conversation flow

- **When disabled** (`False`):
  - Entire message sent as a single block
  - No automatic splitting regardless of length
  - WhatsApp handles long messages natively

**Example**:
```python
# Message with paragraphs
text = """First paragraph here.

Second paragraph here.

Third paragraph here."""

# With split_message=True: sends 3 separate messages
# With split_message=False: sends 1 message with all content
```

### Discord

**Partial control with platform limits**

- **2000-character hard limit**: Always enforced (Discord platform requirement)
- **When enabled** (`True`):
  - Prefers splitting at `\n\n` boundaries
  - Falls back to sentence boundaries if needed
  - Falls back to word boundaries if needed

- **When disabled** (`False`):
  - Skips `\n\n` as preferred split point
  - Uses sentence/word boundaries directly
  - 2000-char limit still applies

**Important**: Discord's 2000-character limit is ALWAYS enforced regardless of the `split_message` setting. The setting only controls the preferred split points.

**Example**:
```python
# 5000-character message
long_text = "..." * 5000

# With split_message=True:
#   - Tries to split at \n\n first
#   - Creates ~3 messages under 2000 chars each

# With split_message=False:
#   - Skips \n\n preference
#   - Splits at sentences/words
#   - Still creates ~3 messages (2000-char limit)
```

## Use Cases

### 1. Narrative Content (Split Enabled)

**Best for**: Stories, articles, tutorials, multi-step instructions

```http
POST /api/v1/instances/content-bot/send-text
{
  "phone": "+5511999999999",
  "text": "Introduction paragraph.\n\nMain content.\n\nConclusion.",
  "split_message": true
}
```
Result: 3 separate messages for better readability

### 2. Code/Logs/Data (Split Disabled)

**Best for**: Code snippets, logs, structured data, preserving formatting

```http
POST /api/v1/instances/dev-bot/send-text
{
  "phone": "+5511999999999",
  "text": "```python\ndef example():\n\n    return True\n```",
  "split_message": false
}
```
Result: Single message preserving code formatting

### 3. Status Updates (Instance Default)

**Best for**: Simple notifications, alerts, confirmations

```http
POST /api/v1/instances/alert-bot/send-text
{
  "phone": "+5511999999999",
  "text": "Deployment complete ✅"
}
```
Result: Uses instance `enable_auto_split` setting

## MCP Integration

The Omni MCP server supports message splitting configuration:

### Set Instance Default
```python
# Via MCP tool
manage_instances(
    operation="update",
    instance_name="my-bot",
    config={"enable_auto_split": False}
)
```

### Send Message with Override
```python
# Via MCP tool
send_message(
    message_type="text",
    instance_name="my-bot",
    phone="+5511999999999",
    message="Long text with\n\nmultiple sections",
    # Note: MCP tool may need extension for split_message parameter
)
```

## Migration Guide

### From v0.1.x to v0.2.x

The `enable_auto_split` field was added in v0.2.0 with a default value of `True`.

**Existing instances**: Automatically default to `True` (backward compatible)
**New instances**: Can explicitly set during creation

**Database Migration**: `49e3788203da_add_enable_auto_split_to_instance_config.py`

No action required for existing deployments - behavior remains unchanged.

### Updating Instance Behavior

To change splitting behavior for existing instances:

```bash
# Via API
curl -X PATCH http://localhost:8000/api/v1/instances/my-bot \
  -H "x-api-key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"enable_auto_split": false}'

# Via Python
from src.db.database import SessionLocal
from src.db.models import InstanceConfig

db = SessionLocal()
instance = db.query(InstanceConfig).filter(
    InstanceConfig.name == "my-bot"
).first()
instance.enable_auto_split = False
db.commit()
db.close()
```

## Testing

### Unit Tests

Test coverage includes:
- Database column validation (`tests/db/test_migrations.py`)
- Pydantic schema validation (`src/api/routes/messages.py`)
- WhatsApp splitting behavior (`tests/channels/whatsapp/test_evolution_api_sender_split.py`)
- Discord hard limit enforcement (`tests/channels/discord/test_channel_handler.py`)

### Integration Testing

```python
import pytest
from src.channels.message_sender import OmniChannelMessageSender

def test_message_splitting_override(test_instance):
    """Test per-message split override."""
    sender = OmniChannelMessageSender(test_instance)

    # Instance has enable_auto_split=True
    # Override with split_message=False
    result = sender.send_text_message(
        phone="+5511999999999",
        text="Paragraph 1\n\nParagraph 2",
        split_message=False
    )

    # Should send as single message
    assert result.message_count == 1
```

## Troubleshooting

### Messages Still Splitting Despite `split_message=False`

**Possible causes**:
1. **Discord platform**: 2000-char limit always enforced
2. **Parameter not passed**: Check API request includes `split_message` field
3. **Instance config**: Verify instance `enable_auto_split` setting

**Solution**:
```bash
# Check instance configuration
curl http://localhost:8000/api/v1/instances/my-bot \
  -H "x-api-key: your-key" | jq '.enable_auto_split'

# Verify request payload
curl -X POST http://localhost:8000/api/v1/instances/my-bot/send-text \
  -H "x-api-key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+5511999999999",
    "text": "test",
    "split_message": false
  }' -v
```

### Messages Not Splitting When Expected

**Possible causes**:
1. No `\n\n` in message (nothing to split on)
2. Instance has `enable_auto_split=False`
3. Per-message override set to `False`

**Solution**:
```bash
# Enable splitting at instance level
curl -X PATCH http://localhost:8000/api/v1/instances/my-bot \
  -H "x-api-key: your-key" \
  -d '{"enable_auto_split": true}'

# Or override per message
curl -X POST http://localhost:8000/api/v1/instances/my-bot/send-text \
  -H "x-api-key: your-key" \
  -d '{
    "phone": "+5511999999999",
    "text": "Part 1\n\nPart 2",
    "split_message": true
  }'
```

## API Reference Summary

### Instance Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_auto_split` | `bool` | `True` | Enable automatic message splitting on `\n\n` |

### Message Sending Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `split_message` | `Optional[bool]` | `None` | Override instance splitting behavior for this message |

### Endpoints Supporting Message Splitting

- `POST /api/v1/instances` - Create with `enable_auto_split`
- `PATCH /api/v1/instances/{name}` - Update `enable_auto_split`
- `GET /api/v1/instances/{name}` - Query `enable_auto_split`
- `POST /api/v1/instances/{name}/send-text` - Send with `split_message` override

## See Also

- [API Documentation](../README.md#api-reference)
- [Instance Management](../README.md#instance-management)
- [Discord Architecture](./IPC_ARCHITECTURE.md)
- [Migration: 49e3788203da](../alembic/versions/49e3788203da_add_enable_auto_split_to_instance_config.py)
