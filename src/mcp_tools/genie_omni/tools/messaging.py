"""Messaging tools - Send and manage WhatsApp messages."""

import logging
from typing import Callable, Optional, Literal, Dict, List, Any
from pathlib import Path
from fastmcp import FastMCP, Context
from ..models import SendMediaRequest, SendAudioRequest

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, get_client: Callable, get_config: Callable):
    """Register messaging tools with the MCP server."""
    # =============================================================================
    # CATEGORY 2: SEND (Active Communication)
    # =============================================================================


    @mcp.tool()
    async def send_whatsapp(
        to: str,
        message: str,
        instance_name: str = "genie",
        message_type: Literal["text", "media", "audio"] = "text",
        media_url: Optional[str] = None,
        media_type: Optional[Literal["image", "video", "document"]] = None,
        mime_type: Optional[str] = None,
        audio_url: Optional[str] = None,
        quoted_message_id: Optional[str] = None,
        delay: Optional[int] = None,
        split_message: Optional[bool] = None,

        ctx: Optional[Context] = None,) -> str:
        """Send WhatsApp message (text/media/audio). Args: to (phone or contact ID), message (text or caption), instance_name, message_type, media_url, media_type, mime_type, audio_url, quoted_message_id, delay, split_message. Returns: confirmation with message ID."""
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(to)

        if not is_allowed:
            logger.warning(f"Blocked send attempt to {to}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        # Log send attempt
        if ctx:
            await ctx.info(f"Sending {message_type} message to {to} via {instance_name}")

        try:
            if message_type == "text":
                # Send "composing" presence (typing indicator) before sending text
                try:
                    if ctx:
                        await ctx.debug("Sending typing indicator")
                    await client.evolution_send_presence(
                        instance_name=instance_name,
                        remote_jid=to,
                        presence="composing",
                        delay=3000  # 3 seconds
                    )
                except Exception as e:
                    logger.warning(f"Failed to send presence: {e}")
                    if ctx:
                        await ctx.warning("Could not send typing indicator")

                # Use Evolution API directly for all text messages to get proper message IDs
                if ctx:
                    await ctx.debug(f"Sending text message ({len(message)} chars)")

                response_data = await client.evolution_send_text(
                    instance_name=instance_name,
                    remote_jid=to,
                    text=message,
                    quoted_msg_id=quoted_message_id,
                    from_me=False if quoted_message_id else True,
                    delay=delay
                )
                message_id = response_data.get('key', {}).get('id', 'Unknown')

                if ctx:
                    await ctx.info(
                        f"Message delivered successfully",
                        extra={"message_id": message_id, "recipient": to}
                    )

                return f"✅ Message sent to {to}\nMessage ID: {message_id}"
            elif message_type == "media":
                if not media_url:
                    return "❌ Error: media_url required for media messages"

                # Detect if media_url is a local file or URL
                import os
                import base64
                from pathlib import Path
                import mimetypes
                from urllib.parse import urlparse

                detected_mime = mime_type
                detected_media_type = media_type or "image"
                media_base64_data = None
                actual_media_url = None

                # Check if it's a local file path
                if os.path.exists(media_url):
                    # It's a local file - read and encode to base64
                    file_path = Path(media_url).absolute()

                    if ctx:
                        await ctx.debug(f"Detected local file: {file_path.name}")

                    # Auto-detect mime type if not provided
                    if not detected_mime:
                        detected_mime, _ = mimetypes.guess_type(str(file_path))
                        if ctx and detected_mime:
                            await ctx.debug(f"Auto-detected MIME type: {detected_mime}")

                    # Auto-detect media_type from mime_type
                    if not media_type and detected_mime:
                        if detected_mime.startswith("image/"):
                            detected_media_type = "image"
                        elif detected_mime.startswith("video/"):
                            detected_media_type = "video"
                        else:
                            detected_media_type = "document"

                        if ctx:
                            await ctx.debug(f"Auto-detected media type: {detected_media_type}")

                    # Read file and encode to base64
                    try:
                        if ctx:
                            await ctx.debug(f"Reading and encoding file ({file_path.stat().st_size} bytes)")

                        with open(file_path, "rb") as f:
                            file_data = f.read()
                            media_base64_data = base64.b64encode(file_data).decode("utf-8")

                        if ctx:
                            await ctx.debug(f"File encoded successfully (base64 length: {len(media_base64_data)})")
                    except Exception as e:
                        if ctx:
                            await ctx.error(f"Failed to read file: {str(e)}", extra={"file_path": str(file_path)})
                        return f"❌ Error reading file {media_url}: {str(e)}"
                else:
                    # It's a URL - try to detect mime_type from URL path
                    actual_media_url = media_url

                    if ctx:
                        await ctx.debug(f"Detected remote URL: {media_url}")

                    # Auto-detect mime type from URL if not provided
                    if not detected_mime:
                        parsed_url = urlparse(media_url)
                        url_path = parsed_url.path
                        detected_mime, _ = mimetypes.guess_type(url_path)

                        if ctx and detected_mime:
                            await ctx.debug(f"Auto-detected MIME type from URL: {detected_mime}")

                    # Auto-detect media_type from mime_type for URLs too
                    if not media_type and detected_mime:
                        if detected_mime.startswith("image/"):
                            detected_media_type = "image"
                        elif detected_mime.startswith("video/"):
                            detected_media_type = "video"
                        else:
                            detected_media_type = "document"

                        if ctx:
                            await ctx.debug(f"Auto-detected media type from MIME: {detected_media_type}")

                if ctx:
                    await ctx.debug(f"Sending {detected_media_type} media to Evolution API")

                # Use Evolution API directly for media (supports all features)
                response_data = await client.evolution_send_media(
                    instance_name=instance_name,
                    remote_jid=to,
                    media_url=actual_media_url,
                    media_base64=media_base64_data,
                    media_type=detected_media_type,
                    caption=message,
                    filename=Path(media_url).name if media_base64_data else None,
                    mime_type=detected_mime,
                    quoted_message_id=quoted_message_id,
                    delay=delay
                )
                message_id = response_data.get('key', {}).get('id', 'Unknown')

                if ctx:
                    await ctx.info(
                        f"Media delivered successfully",
                        extra={"message_id": message_id, "recipient": to, "media_type": detected_media_type}
                    )

                return f"✅ Media sent to {to}\nMessage ID: {message_id}"
            elif message_type == "audio":
                if not audio_url:
                    return "❌ Error: audio_url required for audio messages"

                # Send "recording" presence (recording indicator) before sending audio
                try:
                    if ctx:
                        await ctx.debug("Sending recording indicator")

                    await client.evolution_send_presence(
                        instance_name=instance_name,
                        remote_jid=to,
                        presence="recording",
                        delay=3000  # 3 seconds
                    )
                except Exception as e:
                    if ctx:
                        await ctx.warning("Could not send recording indicator")
                    logger.warning(f"Failed to send presence: {e}")

                # Detect if audio_url is a local file or URL
                import os
                import base64
                from pathlib import Path

                audio_base64_data = None
                actual_audio_url = None

                # Check if it's a local file path
                if os.path.exists(audio_url):
                    # It's a local file - read and encode to base64
                    file_path = Path(audio_url).absolute()

                    if ctx:
                        await ctx.debug(f"Detected local audio file: {file_path.name}")

                    try:
                        if ctx:
                            await ctx.debug(f"Reading and encoding audio ({file_path.stat().st_size} bytes)")

                        with open(file_path, "rb") as f:
                            file_data = f.read()
                            audio_base64_data = base64.b64encode(file_data).decode("utf-8")

                        if ctx:
                            await ctx.debug(f"Audio encoded successfully (base64 length: {len(audio_base64_data)})")
                    except Exception as e:
                        if ctx:
                            await ctx.error(f"Failed to read audio file: {str(e)}", extra={"file_path": str(file_path)})
                        return f"❌ Error reading audio file {audio_url}: {str(e)}"
                else:
                    # It's a URL
                    actual_audio_url = audio_url

                    if ctx:
                        await ctx.debug(f"Detected remote audio URL: {audio_url}")

                # Build request
                request_data = {
                    "phone": to,
                    "quoted_message_id": quoted_message_id,
                    "delay": delay,
                }

                # Add audio_url OR audio_base64
                if audio_base64_data:
                    request_data["audio_base64"] = audio_base64_data
                else:
                    request_data["audio_url"] = actual_audio_url

                if ctx:
                    await ctx.debug("Sending audio message to Omni API")

                request = SendAudioRequest(**request_data)
                response = await client.send_audio(instance_name, request)

                if response.success and ctx:
                    await ctx.info(
                        f"Audio delivered successfully",
                        extra={"message_id": response.message_id, "recipient": to}
                    )
            else:
                return f"❌ Error: Unknown message type '{message_type}'"

            if response.success:
                return f"✅ Message sent to {to}\nMessage ID: {response.message_id}"
            else:
                if ctx:
                    await ctx.error(
                        f"Message delivery failed: {response.error or 'Unknown error'}",
                        extra={"recipient": to, "message_type": message_type}
                    )
                return f"❌ Failed to send message: {response.error or 'Unknown error'}"

        except Exception as e:
            if ctx:
                await ctx.error(
                    f"WhatsApp message error: {str(e)}",
                    extra={"recipient": to, "message_type": message_type}
                )
            logger.error(f"Error sending WhatsApp message: {e}")
            return f"❌ Failed to send message: {str(e)}"


    @mcp.tool()
    async def react_with(
        emoji: str, to_message_id: str, phone: str, instance_name: str = "genie"
,
        ctx: Optional[Context] = None,) -> str:
        """React to message with emoji (auto-detects sender). Args: emoji, to_message_id, phone, instance_name. Returns: confirmation."""
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(phone)

        if not is_allowed:
            logger.warning(f"Blocked reaction attempt to {phone}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        try:
            if ctx:
                await ctx.info(f"Reacting with {emoji} to message {to_message_id}")

            # Auto-detect from_me by checking message in Evolution API
            from ..client import normalize_jid
            remote_jid = normalize_jid(phone)

            if ctx:
                await ctx.debug(f"Fetching messages to detect sender (limit 100)")

            # Fetch messages to find the target message
            messages_response = await client.evolution_find_messages(
                instance_name=instance_name,
                remote_jid=remote_jid,
                limit=100  # Check last 100 messages
            )

            # Find the message and check if it's from me
            from_me = True  # Default to True if not found
            if isinstance(messages_response, list):
                for msg in messages_response:
                    msg_key = msg.get("key", {})
                    if msg_key.get("id") == to_message_id:
                        from_me = msg_key.get("fromMe", True)
                        if ctx:
                            await ctx.debug(f"Found message, from_me={from_me}")
                        break

            if ctx:
                await ctx.debug(f"Sending reaction to Evolution API")

            # Use Evolution API directly for reactions (Omni doesn't support it properly)
            response = await client.evolution_send_reaction(
                instance_name=instance_name,
                remote_jid=phone,
                message_id=to_message_id,
                emoji=emoji,
                from_me=from_me
            )

            if ctx:
                await ctx.info(
                    f"Reaction delivered successfully",
                    extra={"emoji": emoji, "message_id": to_message_id}
                )

            return f"✅ Reacted with {emoji} to message {to_message_id}"

        except Exception as e:
            if ctx:
                await ctx.error(
                    f"Reaction error: {str(e)}",
                    extra={"emoji": emoji, "message_id": to_message_id}
                )
            logger.error(f"Error sending reaction: {e}")
            return f"❌ Failed to send reaction: {str(e)}"


    @mcp.tool()
    async def send_sticker(
        to: str,
        sticker_url: str,
        instance_name: str = "genie",
        quoted_message_id: Optional[str] = None,
        delay: Optional[int] = None,

        ctx: Optional[Context] = None,) -> str:
        """Send WhatsApp sticker. Args: to, sticker_url, instance_name, quoted_message_id, delay. Returns: confirmation with message ID."""
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(to)

        if not is_allowed:
            logger.warning(f"Blocked sticker send attempt to {to}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        try:
            if ctx:
                await ctx.info(f"Sending sticker to {to}")
                await ctx.debug(f"Sticker URL: {sticker_url}")

            response = await client.evolution_send_sticker(
                instance_name=instance_name,
                remote_jid=to,
                sticker_url=sticker_url,
                quoted_message_id=quoted_message_id,
                delay=delay,
            )

            # Extract message ID from Evolution API response
            message_id = response.get("key", {}).get("id", "Unknown")

            if ctx:
                await ctx.info(
                    f"Sticker delivered successfully",
                    extra={"message_id": message_id, "recipient": to}
                )

            return f"✅ Sticker sent to {to}\nMessage ID: {message_id}"

        except Exception as e:
            if ctx:
                await ctx.error(
                    f"Sticker send error: {str(e)}",
                    extra={"recipient": to, "sticker_url": sticker_url}
                )
            logger.error(f"Error sending sticker: {e}")
            return f"❌ Failed to send sticker: {str(e)}"


    @mcp.tool()
    async def send_contact(
        to: str,
        contacts: Optional[List[Dict[str, Any]]] = None,
        contact_name: Optional[str] = None,
        instance_name: str = "genie",
        quoted_message_id: Optional[str] = None,
        delay: Optional[int] = None,

        ctx: Optional[Context] = None,) -> str:
        """Send vCard contact. Use contacts= for custom data OR contact_name= to send saved contact by name. Args: to, contacts (list of dicts: full_name, phone_number, email, organization, url), contact_name (search saved contacts), instance_name, quoted_message_id, delay. Returns: confirmation with message ID."""
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(to)

        if not is_allowed:
            logger.warning(f"Blocked contact send attempt to {to}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        try:
            # If contact_name is provided, search for the contact first
            if contact_name:
                import sqlite3
                import os
                from thefuzz import fuzz
                import unicodedata

                def _normalize(text: str) -> str:
                    if not text:
                        return ""
                    text = unicodedata.normalize('NFD', text)
                    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
                    return text.lower().strip()

                # Search local contacts database
                db_path = os.getenv("AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH", "/home/namastex/data/automagik-omni.db")
                db = sqlite3.connect(db_path)
                cursor = db.cursor()
                cursor.execute("SELECT phone_number, name, nickname FROM contacts")

                best_match = None
                best_score = 0
                normalized_search = _normalize(contact_name)

                for phone, name, nickname in cursor.fetchall():
                    norm_name = _normalize(name)
                    norm_nickname = _normalize(nickname) if nickname else ""

                    name_score = fuzz.partial_ratio(normalized_search, norm_name)
                    nickname_score = fuzz.partial_ratio(normalized_search, norm_nickname) if norm_nickname else 0
                    score = max(name_score, nickname_score)

                    if score > best_score:
                        best_score = score
                        best_match = {"phone_number": phone, "name": name}

                db.close()

                if not best_match or best_score < 60:
                    return f"❌ No contact found matching '{contact_name}'"

                # Build contacts list from found contact
                contacts = [{
                    "full_name": best_match["name"],
                    "phone_number": best_match["phone_number"]
                }]

            elif not contacts:
                return "❌ Must provide either 'contacts' or 'contact_name' parameter"

            # Continue with normal send logic
            # Use Evolution API directly to get proper message IDs
            response_data = await client.evolution_send_contact(
                instance_name=instance_name,
                remote_jid=to,
                contacts=contacts,
                quoted_message_id=quoted_message_id,
                delay=delay
            )

            # Extract message ID from Evolution API response
            message_id = response_data.get("key", {}).get("id", "Unknown")

            contact_count = len(contacts)
            plural = "s" if contact_count > 1 else ""
            return f"✅ {contact_count} contact{plural} sent to {to}\nMessage ID: {message_id}"

        except Exception as e:
            logger.error(f"Error sending contact: {e}")
            return f"❌ Failed to send contact(s): {str(e)}"


    @mcp.tool()
    async def send_location(
        to: str,
        latitude: float,
        longitude: float,
        instance_name: str = "genie",
        name: Optional[str] = None,
        address: Optional[str] = None,

        ctx: Optional[Context] = None,) -> str:
        """Send location. Args: to, latitude, longitude, instance_name, name, address. Returns: confirmation with message ID."""
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(to)

        if not is_allowed:
            logger.warning(f"Blocked location send attempt to {to}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        # Evolution API requires address field - provide default if not given
        if not address:
            address = name if name else f"{latitude}, {longitude}"

        try:
            response = await client.evolution_send_location(
                instance_name=instance_name,
                remote_jid=to,
                latitude=latitude,
                longitude=longitude,
                name=name,
                address=address,
            )

            location_desc = f" ({name})" if name else ""
            return f"✅ Location{location_desc} sent to {to}\nCoordinates: {latitude}, {longitude}\nMessage ID: {response.get('key', {}).get('id', 'None')}"

        except Exception as e:
            logger.error(f"Error sending location: {e}")
            return f"❌ Failed to send location: {str(e)}"


    @mcp.tool()
    async def delete_message(
        message_id: str,
        phone: str,
        instance_name: str = "genie",
        from_me: bool = True,

        ctx: Optional[Context] = None,) -> str:
        """Delete message for everyone. Only works for messages from you (from_me=True), within ~48 hour window. Args: message_id, phone, instance_name, from_me. Returns: confirmation."""
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(phone)

        if not is_allowed:
            logger.warning(f"Blocked delete attempt for {phone}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        try:
            response = await client.evolution_delete_message(
                instance_name=instance_name,
                remote_jid=phone,
                message_id=message_id,
                from_me=from_me,
            )

            return f"✅ Message {message_id} deleted for everyone in chat with {phone}"

        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return f"❌ Failed to delete message: {str(e)}"


    # Internal helper - presence is automatically sent with send_whatsapp
    async def send_presence(
        to: str,
        presence: str = "composing",
        instance_name: str = "genie",
        delay: int = 0,
) -> str:
        """
        Send presence status (typing, recording, etc) to a WhatsApp contact.

        Use this when you need to:
        - Show "typing..." indicator before sending message
        - Show "recording..." indicator before sending audio
        - Provide better UX by simulating human behavior
        - Clear presence indicators (paused/unavailable)

        Args:
            to: Phone number with country code (e.g., "5511999999999") or contact ID
            presence: Status to show:
                     - "composing": Typing... indicator
                     - "recording": Recording audio... indicator
                     - "paused": Stop typing indicator
                     - "available": Show online
                     - "unavailable": Hide status
            instance_name: Your WhatsApp instance (default: "genie")
            delay: How long to show presence in milliseconds (0 = until next message)

        Returns:
            Confirmation that presence was sent

        Example:
            # Show typing indicator before sending message
            send_presence(to="5511999999999", presence="composing")
            # Then send your message
            send_whatsapp(to="5511999999999", message="Hello!")
        """
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(to)

        if not is_allowed:
            logger.warning(f"Blocked presence send attempt to {to}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        try:
            response = await client.evolution_send_presence(
                instance_name=instance_name,
                remote_jid=to,
                presence=presence,
                delay=delay,
            )

            presence_emoji = {
                "composing": "⌨️",
                "recording": "🎤",
                "paused": "⏸️",
                "available": "🟢",
                "unavailable": "⚫"
            }.get(presence, "📡")

            return f"{presence_emoji} Presence '{presence}' sent to {to}"

        except Exception as e:
            logger.error(f"Error sending presence: {e}")
            return f"❌ Failed to send presence: {str(e)}"


    @mcp.tool()
    async def update_message(
        message_id: str,
        new_text: str,
        phone: str,
        instance_name: str = "genie",
        from_me: bool = True,

        ctx: Optional[Context] = None,) -> str:
        """
        Edit/update a WhatsApp message that was already sent.

        Use this when you need to:
        - Fix a typo in a message you sent
        - Update information in a previous message
        - Correct a mistake

        IMPORTANT: Only works for messages sent FROM you (from_me=True).
        Messages from others cannot be edited.
        WhatsApp has time limits for editing (~15 minutes).

        Args:
            message_id: ID of the message to edit
            new_text: New text content for the message
            phone: Phone number of the conversation (e.g., "5511999999999")
            instance_name: Your WhatsApp instance (default: "genie")
            from_me: Whether the message is from you (default: True)

        Returns:
            Confirmation that message was updated

        Example:
            update_message(
                message_id="3EB0C1234567890ABCDEF",
                new_text="Corrected message text",
                phone="5511999999999"
            )
        """
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(phone)

        if not is_allowed:
            logger.warning(f"Blocked update attempt for {phone}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        try:
            response = await client.evolution_update_message(
                instance_name=instance_name,
                remote_jid=phone,
                message_id=message_id,
                new_text=new_text,
                from_me=from_me,
            )

            return f"✅ Message {message_id} updated in chat with {phone}\nNew text: {new_text[:50]}..."

        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return f"❌ Failed to update message: {str(e)}"


    @mcp.tool()
    async def check_is_whatsapp(
        phone_numbers: List[str],
        instance_name: str = "genie",

        ctx: Optional[Context] = None,) -> str:
        """
        Check if phone numbers are registered on WhatsApp.

        Use this when you need to:
        - Verify if a number exists on WhatsApp before sending message
        - Check multiple numbers at once
        - Validate phone numbers before bulk messaging

        Args:
            phone_numbers: List of phone numbers to check (e.g., ["5511999999999", "5511888888888"])
            instance_name: Your WhatsApp instance (default: "genie")

        Returns:
            List of numbers with their WhatsApp status

        Example:
            check_is_whatsapp(phone_numbers=["5511999999999", "5511888888888"])
        """
        client = get_client(ctx)

        try:
            response = await client.evolution_check_is_whatsapp(
                instance_name=instance_name,
                phone_numbers=phone_numbers,
            )

            # Format response for readability
            result_lines = ["📱 WhatsApp Number Check:\n"]

            # Response format varies, handle both formats
            if isinstance(response, list):
                for item in response:
                    number = item.get("jid", item.get("number", "Unknown"))
                    exists = item.get("exists", False)
                    status = "✅ On WhatsApp" if exists else "❌ Not on WhatsApp"
                    result_lines.append(f"  {number}: {status}")
            elif isinstance(response, dict) and "results" in response:
                for item in response["results"]:
                    number = item.get("jid", item.get("number", "Unknown"))
                    exists = item.get("exists", False)
                    status = "✅ On WhatsApp" if exists else "❌ Not on WhatsApp"
                    result_lines.append(f"  {number}: {status}")
            else:
                result_lines.append(f"  Raw response: {response}")

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"Error checking WhatsApp numbers: {e}")
            return f"❌ Failed to check WhatsApp numbers: {str(e)}"


    @mcp.tool()
    async def send_poll(
        to: str,
        question: str,
        options: List[str],
        instance_name: str = "genie",
        selectable_count: int = 1,

        ctx: Optional[Context] = None,) -> str:
        """
        Send an interactive poll to a WhatsApp contact.

        Use this when you need to:
        - Gather opinions from contacts
        - Make group decisions
        - Create surveys or feedback forms
        - Get quick responses with predefined options

        Args:
            to: Phone number with country code (e.g., "5511999999999") or contact ID
            question: The poll question (e.g., "What time works best for the meeting?")
            options: List of answer options (e.g., ["9 AM", "2 PM", "5 PM"])
            instance_name: Your WhatsApp instance (default: "genie")
            selectable_count: How many options can be selected (1 = single choice, >1 = multiple choice)

        Returns:
            Confirmation that poll was sent with message ID

        Example:
            send_poll(
                to="5511999999999",
                question="What's your favorite programming language?",
                options=["Python", "JavaScript", "Go", "Rust"],
                selectable_count=1
            )
        """
        # Safety check: validate recipient against master context
        config = get_config(ctx)
        is_allowed, validation_message = config.validate_recipient(to)

        if not is_allowed:
            logger.warning(f"Blocked poll send attempt to {to}: {validation_message}")
            return validation_message

        # Show safety warning if in full access mode
        if not config.has_master_context():
            logger.warning(config.get_safety_warning())

        client = get_client(ctx)

        try:
            response = await client.evolution_send_poll(
                instance_name=instance_name,
                remote_jid=to,
                name=question,
                options=options,
                selectable_count=selectable_count,
            )

            poll_type = "single choice" if selectable_count == 1 else f"multiple choice (max {selectable_count})"
            return f"📊 Poll sent to {to}\nQuestion: {question}\nOptions: {len(options)} ({poll_type})\nMessage ID: {response.get('key', {}).get('id', 'None')}"

        except Exception as e:
            logger.error(f"Error sending poll: {e}")
            return f"❌ Failed to send poll: {str(e)}"


    # =============================================================================
    # CATEGORY 3: READ (Consume Context)
    # =============================================================================


