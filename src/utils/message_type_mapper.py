"""
Message type mapping for WhatsApp/Evolution API message types.
Maps Evolution API raw message types to user-friendly display names.
"""

MESSAGE_TYPE_MAP = {
    # Text messages
    "conversation": "text",
    "extendedTextMessage": "text",
    # Media messages
    "imageMessage": "image",
    "videoMessage": "video",
    "audioMessage": "audio",
    "documentMessage": "document",
    "stickerMessage": "sticker",
    # Interactive messages
    "reactionMessage": "reaction",
    "pollMessage": "poll",
    "pollUpdateMessage": "poll_update",
    # Special messages
    "ephemeralMessage": "ephemeral",
    "viewOnceMessage": "view_once",
    "viewOnceMessageV2": "view_once",
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


def normalize_message_type(raw_type: str) -> str:
    """
    Normalize Evolution API message type to standard type.

    Args:
        raw_type: Raw message type from Evolution API

    Returns:
        Normalized message type (text, image, reaction, etc.) or "unknown"
    """
    if not raw_type:
        return "unknown"

    # Try direct lookup
    normalized = MESSAGE_TYPE_MAP.get(raw_type)
    if normalized:
        return normalized

    # Try case-insensitive lookup
    for key, value in MESSAGE_TYPE_MAP.items():
        if key.lower() == raw_type.lower():
            return value

    # Return unknown if not found (not the raw type)
    return "unknown"


def get_display_name(message_type: str) -> str:
    """
    Get human-readable display name for message type.

    Args:
        message_type: Normalized message type

    Returns:
        Display name for UI
    """
    DISPLAY_NAMES = {
        "text": "Text",
        "image": "Image",
        "video": "Video",
        "audio": "Audio",
        "document": "Document",
        "sticker": "Sticker",
        "reaction": "Reaction",
        "poll": "Poll",
        "poll_update": "Poll Update",
        "ephemeral": "Disappearing Message",
        "view_once": "View Once",
        "protocol": "Protocol Message",
        "system": "System Message",
        "edited": "Edited Message",
        "call": "Call",
        "location": "Location",
        "live_location": "Live Location",
        "contact": "Contact",
        "contacts": "Contacts",
        "unknown": "Unknown",
    }
    return DISPLAY_NAMES.get(message_type, message_type.title())
