# Allowed Users Feature Implementation Plan

## Overview
Add user allowlist functionality to restrict omni-hub responses to only pre-configured users across all channels (WhatsApp/Evolution API, Discord, etc.).

## KISS Approach
- Single table for all allowed users
- Environment variable for quick enable/disable
- Simple CLI commands for management
- Early filtering in webhook handlers

## Database Changes

### New Table: `allowed_users`
```sql
CREATE TABLE allowed_users (
    id INTEGER PRIMARY KEY,
    user_identifier VARCHAR(255) NOT NULL,  -- phone/discord_id
    channel_type VARCHAR(50) NOT NULL,      -- 'whatsapp', 'discord'
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_identifier, channel_type)
);
```

### Add to `instance_configs`
```sql
ALTER TABLE instance_configs ADD COLUMN allowlist_enabled BOOLEAN DEFAULT FALSE;
```

## Core Service

### `AllowlistService` (`src/services/allowlist_service.py`)
```python
class AllowlistService:
    def is_user_allowed(self, user_id: str, channel_type: str) -> bool
    def add_user(self, user_id: str, channel_type: str, name: str = None) -> bool
    def remove_user(self, user_id: str, channel_type: str) -> bool
    def list_users(self, channel_type: str = None) -> List[dict]
```

## Integration Points (Maintainable Architecture)

### Abstract User Filter Interface
```python
# src/channels/filters/base.py
class ChannelUserFilter(ABC):
    @abstractmethod
    def extract_user_id(self, message_data: dict) -> str:
        """Extract user identifier from channel-specific message data."""
        pass
    
    @abstractmethod
    def should_process_message(self, user_id: str, instance_config: InstanceConfig) -> bool:
        """Check if user should be allowed to interact."""
        pass
```

### Channel-Specific Filters
```python
# src/channels/filters/whatsapp_filter.py
class WhatsAppUserFilter(ChannelUserFilter):
    def extract_user_id(self, webhook_data: dict) -> str:
        return webhook_data.get("key", {}).get("remoteJid", "").split("@")[0]

# src/channels/filters/discord_filter.py  
class DiscordUserFilter(ChannelUserFilter):
    def extract_user_id(self, message_data: dict) -> str:
        return str(message_data.get("author", {}).get("id", ""))
```

### Universal Message Filter Middleware
```python
# src/middleware/allowlist_middleware.py
class AllowlistMiddleware:
    def __init__(self):
        self.filters = {
            "whatsapp": WhatsAppUserFilter(),
            "discord": DiscordUserFilter(),
            # Auto-registers new channels
        }
    
    def should_process_message(self, channel_type: str, message_data: dict, instance_config: InstanceConfig) -> bool:
        if not instance_config.allowlist_enabled:
            return True
            
        filter_instance = self.filters.get(channel_type)
        if not filter_instance:
            logger.warning(f"No allowlist filter for channel: {channel_type}")
            return True  # Fail open
            
        user_id = filter_instance.extract_user_id(message_data)
        return filter_instance.should_process_message(user_id, instance_config)
```

### Webhook Integration (Clean)
```python
# Any webhook handler - just add this line
if not allowlist_middleware.should_process_message(channel_type, webhook_data, instance_config):
    return {"status": "user_not_allowed"}
```

## CLI Management

### Add to `src/cli/` or extend existing CLI
```bash
# Add user
automagik-omni users add +5511999999999 whatsapp --name "John Doe"

# Remove user  
automagik-omni users remove +5511999999999 whatsapp

# List users
automagik-omni users list --channel whatsapp
```

## Configuration

### Environment Variables
```bash
# Global toggle (overrides per-instance settings)
ALLOWLIST_ENABLED=false

# Pre-populate users on startup
ALLOWED_WHATSAPP_USERS=+5511999999999,+5511888888888
ALLOWED_DISCORD_USERS=123456789012345678
```

## Implementation Steps

### Phase 1: Core (1-2 days)
1. Create database migration
2. Implement `AllowlistService`
3. Add CLI commands
4. Basic tests

### Phase 2: WhatsApp Integration (1 day)
1. Add filtering to WhatsApp webhook handler
2. Test with real messages
3. Handle phone number normalization

### Phase 3: Discord Integration (1 day)
1. Add filtering to Discord handlers
2. Test with Discord messages
3. Handle Discord user ID extraction

### Phase 4: Instance Configuration (1 day)
1. Add `allowlist_enabled` to instance config
2. Update CLI/API to manage per-instance settings
3. Environment variable population

## Adding New Channels (Easy Maintainability)

### For Slack, Instagram, etc.:
```python
# 1. Create filter (only file needed)
# src/channels/filters/slack_filter.py
class SlackUserFilter(ChannelUserFilter):
    def extract_user_id(self, message_data: dict) -> str:
        return message_data.get("user", "")
    
    def should_process_message(self, user_id: str, instance_config: InstanceConfig) -> bool:
        return allowlist_service.is_user_allowed(user_id, "slack")

# 2. Auto-register in middleware (optional - can be done automatically)
allowlist_middleware.filters["slack"] = SlackUserFilter()

# 3. Database already supports it (channel_type field)
# 4. CLI already supports it (generic channel_type parameter)
```

### Zero Code Changes Needed:
- ✅ **Database**: Already supports any `channel_type`
- ✅ **CLI**: Generic commands work for any channel
- ✅ **Core Service**: Channel-agnostic
- ✅ **Integration**: One-line addition to webhook handlers

## Key Design Decisions (Maintainable KISS)

### KISS Principles Applied:
- **Plugin Architecture**: New channels = one filter class
- **Single responsibility**: One table, one service, clear purpose  
- **Zero coupling**: Filters are independent, fail-safe
- **Environment-driven**: Quick enable/disable via env vars
- **Early filtering**: Stop processing before expensive operations

### What We're NOT Building:
- Complex role-based access control
- Time-based restrictions  
- Rate limiting per user
- User groups or hierarchies
- Web UI (CLI only initially)

### Maintainability Benefits:
- **New channels**: Just add one filter class
- **Zero core changes**: Middleware handles everything
- **Fail-safe**: Unknown channels default to "allow"
- **Testing**: Each filter can be unit tested independently

## File Structure (Maintainable)
```
src/
├── services/
│   └── allowlist_service.py     # Core logic (channel-agnostic)
├── middleware/
│   └── allowlist_middleware.py  # Universal message filtering
├── channels/filters/
│   ├── base.py                  # Abstract filter interface
│   ├── whatsapp_filter.py       # WhatsApp user extraction
│   ├── discord_filter.py        # Discord user extraction
│   └── slack_filter.py          # Future: just add this file
├── cli/
│   └── users_cli.py             # Generic commands (all channels)
└── api/routes/
    └── *any_webhook*.py         # One-line integration

migrations/
└── add_allowlist_tables.py      # Database changes

tests/
├── test_allowlist_service.py    # Unit tests
├── test_filters/                # Per-channel filter tests
│   ├── test_whatsapp_filter.py
│   └── test_discord_filter.py
└── test_allowlist_integration.py # E2E tests
```

## Testing Strategy
1. **Unit tests**: `AllowlistService` methods
2. **Integration tests**: Webhook filtering end-to-end
3. **Manual testing**: Real WhatsApp/Discord messages
4. **Performance**: Large allowlists (1000+ users)

## Deployment
1. Deploy with `ALLOWLIST_ENABLED=false` (no impact)
2. Run migration to create tables
3. Test on staging instances
4. Enable per instance as needed
5. Populate users via CLI or env vars

This approach prioritizes simplicity and functionality over complexity, ensuring quick implementation and easy maintenance.