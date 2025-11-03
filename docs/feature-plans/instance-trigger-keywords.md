# Instance-Level Trigger Keywords & Mentions

**Feature Branch:** `feature/instance-trigger-keywords`
**Status:** Planning
**Created:** 2025-11-03
**Last Updated:** 2025-11-03

---

## Overview

Add instance-level configuration for trigger keywords and mentions. Agents will only respond when:
- A configured keyword is present in the message, OR
- The instance is explicitly @mentioned

This allows per-instance control over when agents should engage, similar to Discord's native @bot pattern.

---

## Key Architectural Decisions

### Channel Metadata Parameter

**Decision:** Add a new `channel_metadata` parameter to message routing methods instead of repurposing `whatsapp_raw_payload`.

**Rationale:**
- `whatsapp_raw_payload` is clearly named for WhatsApp-specific data
- Existing code (ACL checks) assumes WhatsApp webhook structure
- Repurposing would create confusion and brittleness
- Adding a dedicated parameter is clearer and more maintainable
- Backward compatibility maintained with `channel_metadata=None` default

**Impact:**
- `MessageRouter.route_message()` signature updated
- `MessageRouter.route_message_smart()` signature updated
- All Discord call sites must pass `channel_metadata` with mention data
- WhatsApp continues using `whatsapp_raw_payload` (no changes to WhatsApp paths)
- Existing call sites without `channel_metadata` continue working (fail-open behavior)

---

## Requirements

### Core Behavior

1. **Default Response Rule**:
   - In group contexts, agents respond when the incoming message contains any configured keyword **or** explicitly mentions the instance.
   - In direct messages (DMs), agents keep the current behavior: they always respond, ignoring keywords/mentions.
   - If no keywords are configured, group behavior relies only on explicit mentions.

2. **Keyword Matching**:
   - Support multiple keywords per instance (stored as JSON array string)
   - Matching is case-insensitive by default
   - Only applied in group contexts; DMs ignore keywords

3. **Mention Detection**:
   - **WhatsApp**: Extract mentions from the message payload
   - **Discord**: Extract mentions from the message object
   - Platform-specific mention resolution rules (see Mention Semantics below)

4. **Channel Parity**:
   - Consistent behavior across WhatsApp and Discord
   - Respect platform-specific mention conventions

---

## Usage Examples (expected behavior)

1. **WhatsApp - Group (keyword)**: message "jack, help me?" -> responds (keyword matched)
2. **WhatsApp - Group (mention)**: message "@<owner_jid> check this" -> responds (mention)
3. **WhatsApp - Group (no trigger)**: message "hey" without keyword/mention -> ignored
4. **WhatsApp - DM**: message "hey" -> responds (DM bypasses triggers)
5. **Discord - Guild (keyword)**: message "flash can you look?" -> responds (keyword matched)
6. **Discord - Guild (mention)**: message "@bot hi" -> responds (mention)
7. **Discord - Guild (no trigger)**: message "hi" without keyword/mention -> ignored
8. **Discord - DM**: message "are you there?" -> responds (DM bypasses triggers)

---

## Database Schema

### New InstanceConfig Fields

Add to `src/db/models.py:InstanceConfig`:

```python
# Trigger configuration (add after line 90)
trigger_keywords = Column(String, nullable=True)
# JSON array stored as string: '["jack", "bot", "help"]'
# NULL or empty when no keyword trigger is configured
```

### Alembic Migration

**File:** `alembic/versions/{timestamp}_add_trigger_fields_to_instance_config.py`

```python
def upgrade() -> None:
    """Add trigger configuration columns."""
    op.add_column(
        "instance_configs",
        sa.Column("trigger_keywords", sa.String(), nullable=True)
    )

def downgrade() -> None:
    """Remove trigger configuration columns."""
    op.drop_column("instance_configs", "trigger_keywords")
```

**Backward Compatibility:**
- Existing instances continue responding to mentions by default (keywords unset)
- No migration data transformations needed

---

## Mention Semantics

### What Counts as "Mentioning the Instance"?

The requirement states: "when someone uses @ with the instance number."
Each channel has different mention mechanisms:

#### WhatsApp Mention Resolution

**Group Messages:**
- Extract `mentionedJid` array from: `data.message.extendedTextMessage.contextInfo.mentionedJid[]`
- Compare each JID against **`instance.owner_jid`** (stored in InstanceConfig)
- If `owner_jid` is in `mentionedJid` -> instance is mentioned

**Direct Messages (DMs):**
- No explicit mentions possible in WhatsApp DMs
- **Behavior:** unchanged - DMs bypass triggers and always respond
- Detection: message from/to `owner_jid` without group context

**Fallback:**
- If `owner_jid` is not set -> log warning, default to keyword-only matching
- If `mentionedJid` extraction fails -> log error, fail open (respond)

#### Discord Mention Resolution

**Guild Messages:**
- Extract mentions from Discord message object: `message.mentions[]`
- Each mention has `.id` property (Discord user/bot ID)
- Compare against **bot's client user ID**: `client.user.id`
- If bot's ID is in `message.mentions` -> instance is mentioned

**Direct Messages (DMs):**
- No explicit mentions possible in Discord DMs
- **Behavior:** matches current system - DMs skip triggers and always respond
- Detection: `message.guild is None` (indicates DM)

**Fallback:**
- If bot client not initialized -> log warning, default to keyword-only
- If mention extraction fails -> log error, fail open (respond)

#### Instance Number Mapping

The requirement mentions "@ with the instance number" but:
- **WhatsApp**: No concept of "instance number" in mentions - we use `owner_jid` (phone number)
- **Discord**: No concept of "instance number" - we use bot's user ID

**Interpretation:**
- "Instance number" -> **the unique identifier that represents this instance on the channel**
- WhatsApp: `owner_jid` field (e.g., `"1234567890@s.whatsapp.net"`)
- Discord: Bot's client user ID (e.g., `"1234567890123456789"`)

---

## Trigger Matching Service

### File: `src/services/trigger_matcher.py`

```python
"""Service for determining if agent should respond based on trigger configuration."""

import json
import logging
from typing import Any, Dict, List, Optional

from src.db.models import InstanceConfig

logger = logging.getLogger(__name__)


class TriggerMatcher:
    """
    Determines if an agent should respond to a message based on instance trigger configuration.

    Supports keyword matching plus mention detection across WhatsApp and Discord.
    """

    def should_respond(
        self,
        message_text: str,
        instance_config: Optional[InstanceConfig] = None,
        channel_payload: Optional[Dict[str, Any]] = None,
        channel_type: str = "whatsapp",
        channel_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Determine if agent should respond based on trigger configuration.

        Args:
            message_text: The message text to check
            instance_config: Instance configuration (optional, fails open if missing)
            channel_payload: Raw channel payload (WhatsApp only)
            channel_type: Channel type ("whatsapp" or "discord")
            channel_metadata: Additional channel metadata (Discord mentions, DM status, bot ID)
                Expected Discord metadata format:
                {
                    "mentions": [{"id": "123", "username": "bot"}],  # List of mentioned users
                    "is_dm": False,  # Whether this is a direct message
                    "bot_id": "123456",  # Bot's user ID for comparison
                    "guild_id": "789"  # Guild ID (None for DMs)
                }

        Returns:
            True if agent should respond, False to suppress response
        """
        # Fail open if no instance config available (backward compatibility)
        if not instance_config:
            logger.warning(
                "TriggerMatcher.should_respond called without instance_config - "
                "failing open (responding). This may indicate an older test or "
                "direct router invocation that needs updating."
            )
            return True

        keyword_match = self._check_keywords(message_text, instance_config)
        mention_match = self._check_mention(
            instance_config, channel_payload, channel_type, channel_metadata
        )

        if keyword_match:
            logger.info("Trigger matched via keyword")
            return True
        if mention_match:
            logger.info("Trigger matched via mention")
            return True

        logger.info("Trigger conditions not met (no keyword or mention)")
        return False

    def _check_keywords(self, message_text: str, instance_config: InstanceConfig) -> bool:
        """Check if message contains any configured keywords."""
        if not instance_config.trigger_keywords:
            logger.info("No trigger keywords configured - fallback to mention-only behavior")
            return False

        try:
            keywords = json.loads(instance_config.trigger_keywords)
            if not isinstance(keywords, list):
                logger.error("trigger_keywords is not a list - ignoring keyword matches")
                return False
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse trigger_keywords JSON: {e} - ignoring keyword matches")
            return False

        search_text = message_text.lower()

        # Check each keyword
        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            search_keyword = keyword.lower().strip()
            if not search_keyword:
                continue
            if search_keyword in search_text:
                logger.info(f"Trigger keyword matched: '{keyword}'")
                return True

        logger.info("No trigger keywords matched")
        return False

    def _check_mention(
        self,
        instance_config: InstanceConfig,
        channel_payload: Optional[Dict[str, Any]],
        channel_type: str,
        channel_metadata: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if instance was mentioned in the message."""
        if channel_type == "whatsapp":
            return self._check_whatsapp_mention(instance_config, channel_payload)
        elif channel_type == "discord":
            return self._check_discord_mention(instance_config, channel_metadata)
        else:
            logger.warning(f"Unknown channel_type '{channel_type}' for mention check - failing open")
            return True

    def _check_whatsapp_mention(
        self, instance_config: InstanceConfig, channel_payload: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if instance was mentioned in WhatsApp message."""
        if not channel_payload:
            logger.warning("No channel_payload provided for WhatsApp mention check - failing open")
            return True

        try:
            # Extract message data
            data = channel_payload.get("data", {})
            if not isinstance(data, dict):
                logger.warning("WhatsApp payload 'data' is not a dict - failing open")
                return True

            # Check if this is a DM (triggers are ignored in DMs; keep existing behavior)
            # DM detection: message from/to owner without group context
            is_group = data.get("key", {}).get("remoteJid", "").endswith("@g.us")
            if not is_group:
            logger.info("WhatsApp DM detected - triggers bypassed (responding)")
                return True

            # Extract mentioned JIDs from group message
            message_obj = data.get("message", {})
            extended_text = message_obj.get("extendedTextMessage", {})
            context_info = extended_text.get("contextInfo", {})
            mentioned_jids = context_info.get("mentionedJid", [])

            if not isinstance(mentioned_jids, list):
                logger.warning("mentionedJid is not a list - failing open")
                return True

            # Check if owner_jid is mentioned
            owner_jid = instance_config.owner_jid
            if not owner_jid:
                logger.warning(
                    "No owner_jid configured for instance - cannot check mentions, "
                    "defaulting to keyword-only behavior"
                )
                return False

            is_mentioned = owner_jid in mentioned_jids
            if is_mentioned:
                logger.info(f"WhatsApp instance mentioned: {owner_jid}")
            else:
                logger.info(f"WhatsApp instance NOT mentioned (owner_jid: {owner_jid})")

            return is_mentioned

        except Exception as e:
            logger.error(f"Error checking WhatsApp mention: {e} - failing open", exc_info=True)
            return True

    def _check_discord_mention(
        self, instance_config: InstanceConfig, channel_metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if instance was mentioned in Discord message."""
        if not channel_metadata:
            logger.warning("No channel_metadata provided for Discord mention check - failing open")
            return True

        try:
            # DMs keep existing behavior (triggers ignored)
            is_dm = channel_metadata.get("is_dm", False)
            if is_dm:
                logger.info("Discord DM detected - triggers bypassed (responding)")
                return True

            # Extract mentions and bot ID
            mentions = channel_metadata.get("mentions", [])
            bot_id = channel_metadata.get("bot_id")

            if not bot_id:
                logger.warning(
                    "No bot_id in Discord metadata - cannot check mentions, "
                    "defaulting to keyword-only behavior"
                )
                return False

            if not isinstance(mentions, list):
                logger.warning("Discord mentions is not a list - failing open")
                return True

            # Check if bot is mentioned
            bot_id_str = str(bot_id)
            is_mentioned = any(str(m.get("id")) == bot_id_str for m in mentions if isinstance(m, dict))

            if is_mentioned:
                logger.info(f"Discord bot mentioned: {bot_id}")
            else:
                logger.info(f"Discord bot NOT mentioned (bot_id: {bot_id})")

            return is_mentioned

        except Exception as e:
            logger.error(f"Error checking Discord mention: {e} - failing open", exc_info=True)
            return True


# Singleton instance
trigger_matcher = TriggerMatcher()
```

### Key Design Decisions

1. **Fail-Open Philosophy:**
   - Missing `instance_config` -> respond (logs warning)
   - Malformed configuration -> respond (logs error)
   - Exception during matching -> respond (logs error with traceback)
   - Rationale: Better to over-respond than silently drop messages

2. **Keyword Storage Format:**
   - JSON array string: `'["keyword1", "keyword2"]'`
   - Validates on API input to prevent malformed data
   - Graceful handling of parse errors (fail-open)

3. **DM Behavior Unchanged:**
   - DMs bypass all triggers and always respond (matches current behavior)
   - Implementation: TriggerMatcher detects DMs and returns `True` before checking keywords/mentions
   - Rationale: users in 1:1 expect immediate responses; avoids regressions

4. **Channel Metadata Contract:**
   - WhatsApp: Uses existing `channel_payload` (no changes needed)
   - Discord: Requires new `channel_metadata` dict with structured mention data

---

## Message Router Integration

### Update `MessageRouter.route_message()` Signature

**File:** `src/services/message_router.py:42`

Add new `channel_metadata` parameter to method signature:

```python
def route_message(
    self,
    message_text: str,
    user_id: Optional[Union[str, int]] = None,
    user: Optional[Dict[str, Any]] = None,
    session_name: Optional[str] = None,
    message_type: str = "text",
    whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
    session_origin: str = "whatsapp",
    agent_config: Optional[Dict[str, Any]] = None,
    media_contents: Optional[List[Dict[str, Any]]] = None,
    trace_context=None,
    channel_metadata: Optional[Dict[str, Any]] = None,  # ADD: New parameter
) -> Union[str, Dict[str, Any]]:
```

**Rationale:**
- Dedicated parameter for channel-specific metadata (mentions, DM status, etc.)
- Default `None` ensures backward compatibility with existing call sites
- Clear naming avoids confusion with `whatsapp_raw_payload`
- WhatsApp continues using `whatsapp_raw_payload` for ACL and other checks
- Discord uses `channel_metadata` for mention information

### Add Trigger Check Logic

**File:** `src/services/message_router.py:133` (after access control)

```python
# Import at top of file
from src.services.trigger_matcher import trigger_matcher

# Add after access control check (line 133)
# ------------------------------------------------------------------
# Trigger check (determines if agent should respond)
# Runs after access control, before agent routing
# ------------------------------------------------------------------
try:
    # Extract instance_config from agent_config if available
    instance_config_obj = None
    if isinstance(agent_config, dict):
        instance_config_obj = agent_config.get("instance_config")

    # Check trigger configuration
    should_respond = trigger_matcher.should_respond(
        message_text=message_text,
        instance_config=instance_config_obj,
        channel_payload=whatsapp_raw_payload,  # WhatsApp payload (unchanged)
        channel_type=session_origin,
        channel_metadata=channel_metadata,  # NEW: Dedicated metadata parameter
    )

    if not should_respond:
        instance_name_log = getattr(instance_config_obj, "name", "unknown") if instance_config_obj else "unknown"
        logger.info(
            f"Message ignored - trigger condition not met for instance {instance_name_log}"
        )
        return "AUTOMAGIK:TRIGGER_NOT_MET"

except Exception as trigger_err:
    # Never fail routing due to trigger check errors; default to respond and log
    logger.error(f"Trigger check failed, allowing by default: {trigger_err}", exc_info=True)
```

### Update `MessageRouter.route_message_smart()` Signature

**File:** `src/services/message_router.py:500`

Add new `channel_metadata` parameter to method signature:

```python
async def route_message_smart(
    self,
    message_text: str,
    recipient: str,
    instance_config: InstanceConfig,
    user_id: Optional[Union[str, int]] = None,
    user: Optional[Dict[str, Any]] = None,
    session_name: Optional[str] = None,
    message_type: str = "text",
    whatsapp_raw_payload: Optional[Dict[str, Any]] = None,
    session_origin: str = "whatsapp",
    media_contents: Optional[List[Dict[str, Any]]] = None,
    trace_context=None,
    channel_metadata: Optional[Dict[str, Any]] = None,  # ADD: New parameter
) -> Union[str, Dict[str, Any], bool]:
    """Smart routing with trigger check."""

    # ADD: Trigger check at the top
    try:
        should_respond = trigger_matcher.should_respond(
            message_text=message_text,
            instance_config=instance_config,
            channel_payload=whatsapp_raw_payload,  # WhatsApp payload (unchanged)
            channel_type=session_origin,
            channel_metadata=channel_metadata,  # NEW: Dedicated metadata parameter
        )

        if not should_respond:
            logger.info(f"Smart routing: trigger not met for instance {instance_config.name}")
            return False  # Return False for streaming, consistent with failure

    except Exception as trigger_err:
        logger.error(f"Trigger check in smart routing failed, allowing: {trigger_err}", exc_info=True)

    # Continue with existing streaming vs traditional decision...
    if self.should_use_streaming(instance_config):
        # ... existing code
```

---

## Discord Metadata Plumbing

### Problem Statement

Only WhatsApp currently passes raw payload to `route_message()`. Discord paths do not pass mention information, so `TriggerMatcher` will never see Discord mentions unless we explicitly package and pass them.

### Solution: Build `channel_metadata` in Each Discord Path

The new `channel_metadata` parameter (see [Key Architectural Decisions](#key-architectural-decisions)) provides a clean way to pass Discord-specific information without conflicting with WhatsApp's `whatsapp_raw_payload`. This keeps the code clear and maintainable.

**Why not reuse `whatsapp_raw_payload`?**
- Parameter name clearly indicates WhatsApp-only usage
- Existing ACL checks at `src/services/message_router.py:99-115` assume WhatsApp structure
- Future refactors could break when unexpected data is passed
- Intent becomes unclear to readers and maintainers

**Channel Metadata Format for Discord:**
```python
{
    "mentions": [{"id": "123", "username": "bot"}],  # List of mentioned users
    "is_dm": False,  # Whether this is a direct message
    "bot_id": "123456",  # Bot's user ID for comparison
    "guild_id": "789"  # Guild ID (None for DMs)
}
```

#### Path 1: Discord Channel Handler

**File:** `src/channels/discord/channel_handler.py:365`

```python
# BEFORE calling route_message (around line 360)

# Build channel metadata for trigger matching
channel_metadata = {
    "mentions": [
        {"id": str(mention.id), "username": mention.name}
        for mention in message.mentions
    ],
    "is_dm": message.guild is None,
    "bot_id": str(self._bot_instances[instance.name].client.user.id) if instance.name in self._bot_instances else None,
    "guild_id": str(message.guild.id) if message.guild else None,
}

# Build agent_config with instance (MISSING currently)
agent_config = {
    "name": instance.agent_id or instance.default_agent or "default",
    "agent_id": instance.agent_id or instance.default_agent or "default",
    "api_url": instance.agent_api_url,
    "api_key": instance.agent_api_key,
    "timeout": instance.agent_timeout or 60,
    "instance_type": instance.agent_instance_type or "automagik",
    "agent_type": instance.agent_type or "agent",
    "stream_mode": instance.agent_stream_mode or False,
    "instance_config": instance,  # CRITICAL: Include instance_config
}

# THEN call route_message
agent_response = message_router.route_message(
    user_id=cached_agent_user_id,
    user=user_dict if not cached_agent_user_id else None,
    session_name=session_name,
    message_text=content,
    message_type="text",
    session_origin="discord",
    whatsapp_raw_payload=None,  # Discord doesn't have WhatsApp payload
    agent_config=agent_config,  # ADD: agent_config
    media_contents=None,
    trace_context=trace_context,
    channel_metadata=channel_metadata,  # ADD: Discord metadata
)
```

#### Path 2: Discord Bot Manager

**File:** `src/channels/discord/bot_manager.py:762`

```python
# BEFORE calling route_message (around line 760)

# Build channel metadata for trigger matching
channel_metadata = {
    "mentions": [
        {"id": str(mention.id), "username": mention.name}
        for mention in message.mentions
    ],
    "is_dm": message.guild is None,
    "bot_id": str(self.client.user.id),
    "guild_id": str(message.guild.id) if message.guild else None,
}

# Build agent_config (MISSING currently)
# Need to get instance config - stored in self or passed to bot_manager
agent_config = {
    "name": self.instance_config.agent_id or self.instance_config.default_agent or "default",
    "agent_id": self.instance_config.agent_id or self.instance_config.default_agent or "default",
    "api_url": self.instance_config.agent_api_url,
    "api_key": self.instance_config.agent_api_key,
    "timeout": self.instance_config.agent_timeout or 60,
    "instance_type": self.instance_config.agent_instance_type or "automagik",
    "agent_type": self.instance_config.agent_type or "agent",
    "stream_mode": self.instance_config.agent_stream_mode or False,
    "instance_config": self.instance_config,  # CRITICAL: Include instance_config
}

# Update route_func to include new parameters
route_func = partial(
    self.message_router.route_message,
    message_text=content,
    user_id=resolved_user_id,
    user=None if resolved_user_id else user_dict,
    session_name=session_name,
    message_type="text",
    session_origin="discord",
    whatsapp_raw_payload=None,  # Discord doesn't have WhatsApp payload
    agent_config=agent_config,  # ADD: agent_config
    media_contents=None,
    trace_context=trace_context,
    channel_metadata=channel_metadata,  # ADD: Discord metadata
)
```

**Note:** Bot manager needs access to `instance_config`. Verify if it's stored in `self` or needs to be passed during initialization.

#### Path 3: Discord Interaction Handler

**File:** `src/channels/discord/interaction_handler.py:599`

```python
# BEFORE calling route_message (around line 598)

# Build channel metadata for trigger matching
channel_metadata = {
    "mentions": [],  # Slash commands don't have text mentions
    "is_dm": interaction.guild is None,
    "bot_id": str(self.bot.user.id),
    "guild_id": str(interaction.guild.id) if interaction.guild else None,
}

# Build agent_config (MISSING currently)
# Need instance_config - may need to fetch from interaction context
# Assuming interaction handler has access to instance
agent_config = {
    "name": instance.agent_id or instance.default_agent or "default",
    "agent_id": instance.agent_id or instance.default_agent or "default",
    "api_url": instance.agent_api_url,
    "api_key": instance.agent_api_key,
    "timeout": instance.agent_timeout or 60,
    "instance_type": instance.agent_instance_type or "automagik",
    "agent_type": instance.agent_type or "agent",
    "stream_mode": instance.agent_stream_mode or False,
    "instance_config": instance,
}

response = await self.message_router.route_message(
    content=question,
    user_id=str(interaction.user.id),
    channel_id=str(interaction.channel.id) if interaction.channel else None,
    session_origin="discord",
    whatsapp_raw_payload=None,  # Discord doesn't have WhatsApp payload
    agent_config=agent_config,  # ADD: agent_config
    channel_metadata=channel_metadata,  # ADD: Discord metadata
)
```

**Note:** Interaction handler signature may differ. Verify parameter names and adjust accordingly.

### Implementation Notes

1. **Bot ID Availability:**
   - Channel handler: Get from `self._bot_instances[instance.name].client.user.id`
   - Bot manager: Get from `self.client.user.id`
   - Interaction handler: Get from `self.bot.user.id`

2. **Instance Config Availability (required actions):**
   - Channel handler: already receives `instance`; use it directly (no extra work)
   - Bot manager: ensure `self.instance_configs[instance_name]` is populated; if missing, log an error and abort
   - Interaction handler: add an explicit lookup via the instance service (`instance_manager`/`SessionLocal`) to retrieve `InstanceConfig`

3. **Backward Compatibility:**
   - Older tests/invocations may not pass `agent_config`
   - `TriggerMatcher` fails open when `instance_config` is missing
   - Log warnings help identify call sites that need updating

---

## Response Suppression

### Sentinel Pattern

When trigger conditions are not met, router returns: `"AUTOMAGIK:TRIGGER_NOT_MET"`

All channel handlers must check for this sentinel and suppress response.

### WhatsApp Handler

**File:** `src/channels/whatsapp/handlers.py:652`

Already implemented - no changes needed:

```python
# Check if the response should be ignored
if isinstance(response_to_send, str) and response_to_send.startswith("AUTOMAGIK:"):
    logger.warning(
        f"Ignoring AUTOMAGIK message for user {user_dict['phone_number']}, "
        f"session {session_name}: {response_to_send}"
    )
else:
    # Send response...
```

### Discord Channel Handler

**File:** `src/channels/discord/channel_handler.py:395`

Missing - add check before sending:

```python
# ADD: Check for sentinel before extract_response_text
if isinstance(agent_response, str) and agent_response.startswith("AUTOMAGIK:"):
    logger.info(
        f"Suppressing sentinel response for Discord user {message.author.name}: "
        f"{agent_response}"
    )
    return  # Don't send anything

# Existing code continues...
if agent_response:
    response_text = extract_response_text(agent_response)
    # ...
```

Apply same check at **line 432** (duplicate response handling block).

### Discord Bot Manager

**File:** `src/channels/discord/bot_manager.py` (after `route_message` call)

Missing - add check after getting response:

```python
# After executing route_func and getting agent_response (around line 780)

# ADD: Check for sentinel
if isinstance(agent_response, str) and agent_response.startswith("AUTOMAGIK:"):
    logger.info(
        f"Suppressing sentinel response for Discord user {message.author.name}: "
        f"{agent_response}"
    )
    return  # Don't send anything

# Existing response handling continues...
```

### Discord Interaction Handler

**File:** `src/channels/discord/interaction_handler.py:599` (after `route_message` call)

Missing - add check after getting response:

```python
# After route_message call (around line 599)
response = await self.message_router.route_message(...)

# ADD: Check for sentinel
if isinstance(response, str) and response.startswith("AUTOMAGIK:"):
    logger.info(f"Suppressing sentinel response for interaction: {response}")
    # Optionally send ephemeral message: "This bot only responds to specific triggers"
    return

# Existing response handling continues...
```

### Utility Function

**File:** `src/channels/message_utils.py:10`

Update `extract_response_text()` to handle sentinels:

```python
def extract_response_text(response: Union[str, Dict[str, Any]]) -> str:
    """Extract text content from various response formats."""

    # ADD: Handle sentinel responses
    if isinstance(response, str) and response.startswith("AUTOMAGIK:"):
        return ""  # Return empty string for suppression

    # Existing code continues...
    if isinstance(response, str):
        return response
    # ...
```

---

## API Schema Updates

### File: `src/api/routes/instances.py`

#### InstanceConfigCreate (line 50)

```python
class InstanceConfigCreate(BaseModel):
    # ... existing fields ...

    # ADD: Trigger configuration
    trigger_keywords: Optional[str] = Field(
        default=None,
        description="JSON array of keywords, e.g. '[\"jack\", \"bot\", \"help\"]'"
    )
```

#### InstanceConfigUpdate (line 102)

```python
class InstanceConfigUpdate(BaseModel):
    # ... existing fields ...

    # ADD: Trigger configuration
    trigger_keywords: Optional[str] = Field(
        default=None,
        description="JSON array of keywords, e.g. '[\"jack\", \"bot\", \"help\"]'"
    )
```

#### InstanceConfigResponse (line 149)

```python
class InstanceConfigResponse(BaseModel):
    # ... existing fields ...

    # ADD: Trigger configuration
    trigger_keywords: Optional[str] = None
```

#### Validation in Create/Update Endpoints

Add validation in `create_instance()` and `update_instance()` endpoints:

```python
# In create_instance() after line 230
# Validate trigger_keywords JSON format
if instance_data.trigger_keywords:
    try:
        keywords = json.loads(instance_data.trigger_keywords)
        if not isinstance(keywords, list):
            raise ValueError("Must be an array")
        if not all(isinstance(k, str) for k in keywords):
            raise ValueError("All keywords must be strings")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger_keywords: must be a JSON array of strings. Error: {str(e)}"
        )
```

---

## Testing Strategy

### Unit Tests

#### File: `tests/test_trigger_matcher.py`

```python
class TestTriggerMatcher:
    """Unit tests for TriggerMatcher service."""

    def test_always_mode_responds(self):
        """Always mode should always return True."""

    def test_keyword_match(self):
        """Returns True when message contains configured keyword."""

    def test_keyword_no_match(self):
        """Returns False when no keywords match and no mention."""

    def test_keyword_malformed_json(self):
        """Ignores keywords when JSON is invalid (mention-only fallback)."""

    def test_whatsapp_group_mention(self):
        """Detects mention via WhatsApp group payload."""

    def test_whatsapp_dm_bypasses_triggers(self):
        """WhatsApp DM bypasses triggers and returns True."""

    def test_discord_guild_mention(self):
        """Detects mention via Discord metadata (guild)."""

    def test_discord_guild_no_mention(self):
        """Returns False when Discord guild message lacks mention and keyword."""

    def test_discord_dm_bypasses_triggers(self):
        """Discord DM bypasses triggers and returns True."""

    def test_missing_instance_config_fails_open(self):
        """Returns True when instance_config is missing (backward compatibility)."""
```

### Integration Tests

#### File: `tests/test_trigger_integration.py`

```python
class TestTriggerIntegration:
    """Integration tests for trigger feature across routing paths."""

    def test_whatsapp_handler_suppresses_trigger_not_met(self):
        """WhatsApp handler should suppress TRIGGER_NOT_MET sentinel."""

    def test_discord_handler_suppresses_trigger_not_met(self):
        """Discord handler should suppress TRIGGER_NOT_MET sentinel."""

    def test_route_message_checks_triggers(self):
        """MessageRouter.route_message should check triggers."""

    def test_route_message_smart_checks_triggers(self):
        """MessageRouter.route_message_smart should check triggers."""

    def test_api_create_instance_validates_keywords(self):
        """API should validate trigger_keywords JSON payloads."""

    def test_api_update_instance_validates_keywords(self):
        """API update should reject malformed trigger_keywords."""

    def test_api_response_includes_trigger_keywords(self):
        """API response should include trigger_keywords value."""

    def test_backward_compatibility_no_agent_config(self):
        """Routing should work when agent_config is not provided (older tests)."""
```

### End-to-End Tests

#### File: `tests/test_trigger_e2e.py`

```python
class TestTriggerE2E:
    """End-to-end tests simulating real message flows."""

    async def test_whatsapp_keyword_no_match_no_response(self):
        """WhatsApp message without keyword should not respond."""

    async def test_whatsapp_keyword_match_responds(self):
        """WhatsApp message with keyword should respond."""

    async def test_whatsapp_mention_in_group_responds(self):
        """WhatsApp group message with @mention should respond."""

    async def test_whatsapp_dm_bypasses_triggers(self):
        """WhatsApp DM still responds even without keyword/mention (triggers ignored)."""

    async def test_discord_keyword_no_match_no_response(self):
        """Discord message without keyword or mention should not respond."""

    async def test_discord_guild_mention_responds(self):
        """Discord guild message with @bot should respond."""

    async def test_discord_dm_bypasses_triggers(self):
        """Discord DM still responds even without keyword/mention (triggers ignored)."""
```

---

## Implementation Checklist

### Phase 1: Database & Model
- [ ] Create Alembic migration for trigger fields
- [ ] Add trigger field to `InstanceConfig` model
- [ ] Add trigger field to API schemas (Create, Update, Response)
- [ ] Add validation for `trigger_keywords` in API endpoints
- [ ] Test migration up/down on clean and existing databases

### Phase 2: Trigger Matcher Service
- [ ] Create `src/services/trigger_matcher.py` with all methods
- [ ] Implement keyword matching (case-insensitive default)
- [ ] Implement WhatsApp mention extraction and matching
- [ ] Implement Discord mention extraction and matching
- [ ] Implement fail-open error handling throughout
- [ ] Write unit tests covering keyword, mention, and DM behavior

### Phase 3: Discord Metadata Plumbing
- [ ] Update Discord channel handler to build `channel_metadata` and `agent_config`
- [ ] Update Discord bot manager to build `channel_metadata` and `agent_config`
- [ ] Update Discord interaction handler to build `channel_metadata` and `agent_config`
- [ ] Verify bot manager has access to `instance_config` (or add it)
- [ ] Verify interaction handler can lookup instance from context (or add it)

### Phase 4: Router Integration
- [ ] Add `channel_metadata` parameter to `MessageRouter.route_message()` signature
- [ ] Add `channel_metadata` parameter to `MessageRouter.route_message_smart()` signature
- [ ] Add trigger check to `MessageRouter.route_message()` after access control
- [ ] Add trigger check to `MessageRouter.route_message_smart()`
- [ ] Update all WhatsApp call sites to pass `channel_metadata=None` (explicit, for clarity)
- [ ] Update all Discord call sites to pass `channel_metadata` with mention data
- [ ] Return `AUTOMAGIK:TRIGGER_NOT_MET` sentinel when triggers not met
- [ ] Add error handling and fail-open logic

### Phase 5: Response Suppression
- [ ] Verify WhatsApp handler sentinel suppression (already exists)
- [ ] Add sentinel check to Discord channel handler (2 locations)
- [ ] Add sentinel check to Discord bot manager
- [ ] Add sentinel check to Discord interaction handler
- [ ] Slash commands: enforce bypass (standard response if TriggerMatcher blocks)
- [ ] Update `extract_response_text()` to handle sentinels
- [ ] Write integration tests for suppression in all paths

### Phase 6: Testing & Validation
- [ ] Write unit tests for `TriggerMatcher` (15+ test cases)
- [ ] Write integration tests for routing with triggers
- [ ] Write E2E tests for WhatsApp and Discord flows
- [ ] Test backward compatibility (no `agent_config` provided)
- [ ] Test fail-open behavior with malformed configs
- [ ] Test DM behavior on both platforms
- [ ] Test slash commands bypassing triggers
- [ ] Test keyword matches, mentions, DMs, and malformed configurations

### Phase 7: Documentation & Cleanup
- [ ] Update API documentation with trigger field
- [ ] Add inline code comments for complex logic
- [ ] Document explicit note that DMs bypass triggers (for stakeholder alignment)
- [ ] Create example configurations for common use cases
- [ ] Update CHANGELOG.md with feature description

---

### Instance Number Mapping Clarity

**Question:** What exactly is the "instance number" mentioned in requirements?

**Current Interpretation:**
- WhatsApp: `owner_jid` field (e.g., `"1234567890@s.whatsapp.net"`)
- Discord: Bot's user ID (e.g., `"1234567890123456789"`)

**Recommendation:** Confirm this mapping is correct and document in user-facing materials.

---

### Slash Command Triggers

**Decision:** Slash commands bypass triggers (treated as explicit intent).

**Implications:**
- The interaction handler still calls the router with `channel_metadata` marking `is_dm` appropriately, but if `AUTOMAGIK:TRIGGER_NOT_MET` comes back it replies with a standard message explaining slash commands always run.
- Document this behavior in any UI/public documentation.
- If product later wants keywords to apply to slash commands, remove this exception.

---

## Migration Path

### Existing Instances

All existing instances will have `trigger_keywords` unset after the migration.

Result: they continue responding to explicit mentions (WhatsApp/Discord) and ignore non-mentioned messages until keywords are configured.

### Feature Adoption

Users can opt-in to keyword triggers by:
1. Configuring `trigger_keywords` via API update endpoint
2. Ensuring WhatsApp instances have `owner_jid` populated for mention detection
3. Ensuring Discord bots are properly initialized for mention detection

---

## Performance Considerations

### Trigger Check Overhead

- Keyword matching: O(n) where n = number of keywords (typically < 10)
- Mention extraction: O(m) where m = number of mentions (typically < 5)
- JSON parsing: Cached after first parse (future optimization)

**Impact:** Negligible - adds < 1ms to message processing.

### Database Impact

- One new column on `instance_configs` table
- No new indexes needed
- No impact on existing queries

---

## Security Considerations

### Keyword Validation

- Validate JSON format on API input to prevent injection
- Limit keyword array size (max 50 keywords recommended)
- Sanitize keywords for logging (avoid PII)

### Mention Spoofing

- WhatsApp: Evolution API handles mention validation
- Discord: Discord.py handles mention validation
- No additional validation needed in our layer

### DDoS via Keyword Matching

- Keyword matching is fast (string contains check)
- No regex evaluation (would be slow)
- Rate limiting at API/webhook level handles message floods

---

## Future Enhancements

### Phase 2 Features (Not in Scope)

- [ ] Regex pattern matching for keywords
- [ ] Keyword groups (OR/AND logic)
- [ ] Time-based trigger windows (only respond during business hours)
- [ ] User-specific trigger overrides
- [ ] Trigger analytics (which keywords are most common)
- [ ] UI for trigger configuration (beyond API)

---

## Changelog

**2025-11-03 (v2):**
- **BREAKING CHANGE:** Added `channel_metadata` parameter to `route_message()` and `route_message_smart()`
- Removed approach of repurposing `whatsapp_raw_payload` for Discord data
- Clarified that WhatsApp continues using `whatsapp_raw_payload` (unchanged)
- Discord now uses dedicated `channel_metadata` parameter for mention data
- Updated all code examples to use new parameter
- Simplified trigger configuration: removed `trigger_mode`/`trigger_case_sensitive`; default behavior is mention-or-keyword
- Updated implementation checklist to include signature changes

**2025-11-03 (v1):**
- Initial plan created
- Addressed feedback on Discord metadata plumbing
- Clarified mention semantics for WhatsApp and Discord
- Documented DM behavior assumption
- Added InstanceConfig availability fail-open strategy
- Expanded testing strategy
- Added open questions section

---

## Approval Checklist

Before implementation begins:

- [ ] Product confirms DM behavior assumption
- [ ] Product confirms instance number mapping
- [ ] Architecture reviews trigger matcher design
- [ ] Security reviews keyword validation approach
- [ ] QA reviews testing strategy
- [ ] Discord path metadata plumbing confirmed feasible

---

**Next Steps:**
1. Review this plan with stakeholders
2. Get confirmation on open questions (slash command messaging, DM documentation wording)
3. Approve plan
4. Begin Phase 1 implementation (database & model)
