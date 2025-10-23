# Message Type Normalization - Implementation Summary

## Problem
Many traces showed `message_type: "unknown"` because the message type detection only handled basic types (text, image, video, audio, document). WhatsApp has many additional message types that weren't being recognized:
- `reactionMessage` (emoji reactions) - **Most common unknown type (782 traces)**
- `ephemeralMessage` (disappearing messages) - 427 traces
- `stickerMessage` - 73 traces
- `protocolMessage`, `pollMessage`, `locationMessage`, `contactMessage`, etc.

## Solution

### 1. Created Message Type Mapper (`src/utils/message_type_mapper.py`)

A comprehensive mapping system that:
- Maps 20+ WhatsApp/Evolution API message types to normalized display names
- Provides `normalize_message_type()` for converting raw types to standard types
- Provides `get_display_name()` for UI-friendly display names

**MESSAGE_TYPE_MAP:**
```python
{
    # Text
    "conversation": "text",
    "extendedTextMessage": "text",

    # Media
    "imageMessage": "image",
    "videoMessage": "video",
    "audioMessage": "audio",
    "documentMessage": "document",
    "stickerMessage": "sticker",

    # Interactive
    "reactionMessage": "reaction",
    "pollMessage": "poll",
    "pollUpdateMessage": "poll_update",

    # Special
    "ephemeralMessage": "ephemeral",
    "viewOnceMessage": "view_once",

    # System/Protocol
    "protocolMessage": "protocol",
    "systemMessage": "system",
    "editedMessage": "edited",

    # Calls
    "call": "call",

    # Location
    "locationMessage": "location",
    "liveLocationMessage": "live_location",

    # Contact
    "contactMessage": "contact",
    "contactsArrayMessage": "contacts",
}
```

### 2. Updated Trace Service (`src/services/trace_service.py`)

Modified `_determine_message_type()` to:
- Import and use `normalize_message_type()`
- Iterate through all keys in the message object
- Skip metadata keys like "contextInfo"
- Use the normalizer to map any recognized message type

**Before:**
```python
def _determine_message_type(message_obj: Dict[str, Any]) -> str:
    if "conversation" in message_obj:
        return "text"
    elif "extendedTextMessage" in message_obj:
        return "text"
    # ... only 5 types supported
    else:
        return "unknown"
```

**After:**
```python
def _determine_message_type(message_obj: Dict[str, Any]) -> str:
    for key in message_obj.keys():
        if key in ["contextInfo", "messageContextInfo"]:
            continue
        normalized = normalize_message_type(key)
        if normalized != "unknown":
            return normalized
    return "unknown"
```

### 3. Updated API Routes (`src/api/routes/traces.py`)

Enhanced the TraceResponse model:
- Added `message_type_display` field for UI-friendly names
- Updated all trace endpoints to populate this field using `get_display_name()`
- Applied to: `list_traces()`, `get_trace()`, `get_traces_by_phone()`

### 4. Created Migration Script (`scripts/fix_unknown_message_types.py`)

A one-time migration script that:
- Finds all traces with `message_type='unknown'`
- Re-analyzes their webhook payloads
- Updates the message type based on the new detection logic
- Supports dry-run mode for safety

**Results:**
- Processed: 1,798 traces with "unknown" type
- Successfully updated: 1,287 traces (71.6%)
- Failed: 0 traces
- Remaining unknown: 511 traces (genuine unknowns or missing payloads)

## Message Type Distribution (After Migration)

```
text:      4,998  (64.8%)  - Text messages
reaction:    782  (10.1%)  - Emoji reactions ⭐ Previously unknown!
image:       766   (9.9%)  - Image messages
ephemeral:   427   (5.5%)  - Disappearing messages ⭐ Previously unknown!
unknown:     511   (6.6%)  - Genuine unknowns
audio:       127   (1.6%)  - Voice messages
sticker:      73   (0.9%)  - Stickers ⭐ Previously unknown!
video:        38   (0.5%)  - Video messages
document:     26   (0.3%)  - Documents
location:      2   (0.0%)  - Location shares
contact:       4   (0.1%)  - Contact cards
```

## Verification Tests

### 1. Specific Trace Check
```bash
curl -s "http://0.0.0.0:8882/api/v1/traces/8a2388fa-f546-488c-b4ee-3e2ab36aafdd" \
  -H "x-api-key: namastex888" | jq '.message_type'
```
**Result:** `"ephemeral"` (was `"unknown"`)

### 2. Analytics Check
```bash
curl -s "http://0.0.0.0:8882/api/v1/traces/analytics/summary?all_time=true" \
  -H "x-api-key: namastex888" | jq '.message_types'
```
**Result:** Shows proper distribution with reactions, ephemeral, stickers now visible

### 3. Display Names Check
```bash
curl -s "http://0.0.0.0:8882/api/v1/traces?message_type=ephemeral&limit=1" \
  -H "x-api-key: namastex888" | jq '.[0].message_type_display'
```
**Result:** `"Disappearing Message"`

## Future New Messages

All new messages will automatically:
1. Be detected with the correct type using the mapper
2. Have a display name available via `get_display_name()`
3. No migration needed - works immediately

To add new message types, simply update `MESSAGE_TYPE_MAP` in `src/utils/message_type_mapper.py`.

## Files Changed

1. **Created:**
   - `src/utils/message_type_mapper.py` - Message type mapping utility
   - `scripts/fix_unknown_message_types.py` - One-time migration script

2. **Modified:**
   - `src/services/trace_service.py` - Updated message type detection
   - `src/api/routes/traces.py` - Added display names to API responses

## Running the Migration

**Dry run (check what would change):**
```bash
uv run python scripts/fix_unknown_message_types.py
```

**Execute (apply changes):**
```bash
uv run python scripts/fix_unknown_message_types.py --execute
```

## Impact

- ✅ 782 reactions now properly identified (was the #1 unknown type)
- ✅ 427 ephemeral messages now properly identified
- ✅ 73 stickers now properly identified
- ✅ Better analytics and reporting
- ✅ UI can now show friendly names like "Reaction" instead of "unknown"
- ✅ Future message types can be easily added to the mapper
- ✅ Zero breaking changes - backwards compatible
