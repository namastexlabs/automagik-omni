"""Reading tools - What messages have I received?"""

import logging
from typing import Callable, Dict, List, Any, Optional
from fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, get_client: Callable):
    """Register message reading tools with the MCP server."""

    @mcp.tool()
    async def read_messages(
        from_phone: str,
        instance_name: str = "genie",
        limit: int = 50,
        before_message_id: str = None
    ,
        ctx: Optional[Context] = None,) -> str:
        """Read messages from person or conversation. Args: from_phone (number or group ID), instance_name, limit, before_message_id (for pagination). Returns: messages newest first, with pagination info."""
        client = get_client(ctx)

        try:
            # Use Evolution API directly for message history (Omni traces don't support groups)
            response = await client.evolution_find_messages(instance_name, from_phone, limit=limit)

            messages_data = response.get("messages", {})
            records = messages_data.get("records", [])
            # Apply limit client-side since Evolution API ignores it
            records = records[:limit]
            total = messages_data.get("total", 0)

            if not records:
                return f"📱 No messages found from {from_phone}"

            result = [f"📱 MESSAGES: {from_phone} ({total} total, showing {len(records)})"]
            result.append("")

            for msg in records:
                # Extract message details
                key = msg.get("key", {})
                sender_name = msg.get("pushName", "Unknown")
                from_me = key.get("fromMe", False)

                # Get timestamp
                timestamp = msg.get("messageTimestamp", 0)
                if timestamp:
                    from datetime import datetime
                    dt = datetime.fromtimestamp(timestamp)
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    time_str = "?"

                # Get message content
                msg_type = msg.get("messageType", "unknown")
                message_content = msg.get("message", {})

                # Extract text content and mentions
                text = ""
                mentions = []
                if "conversation" in message_content:
                    text = message_content["conversation"]
                elif "extendedTextMessage" in message_content:
                    ext_msg = message_content["extendedTextMessage"]
                    text = ext_msg.get("text", "")
                    # Check for mentions in contextInfo
                    context_info = ext_msg.get("contextInfo", {})
                    mentions = context_info.get("mentionedJid", [])

                # Extract phone number: for groups, use participant; for DMs, use remoteJid
                # Priority: participant (group member) > remoteJid (DM or group ID)
                phone_number = key.get("participant")
                if not phone_number:
                    remote_jid = key.get("remoteJid", "")
                    # Don't use group ID as phone number (groups end with @g.us)
                    if not remote_jid.endswith("@g.us"):
                        phone_number = remote_jid
                    else:
                        phone_number = "Unknown"

                # Clean phone number (remove @s.whatsapp.net or @lid suffix)
                if phone_number and "@" in phone_number:
                    phone_number = phone_number.split("@")[0]

                # Format sender: pushName (phone/LID)
                if from_me:
                    sender_label = "You"
                else:
                    sender_label = f"{sender_name} ({phone_number})"
                message_id = key.get("id", "?")

                # Build compact message line
                type_tag = f"[{msg_type}]" if msg_type != "conversation" else ""
                mention_tag = f" @{len(mentions)}" if mentions else ""
                result.append(f"[{time_str}] {sender_label}{mention_tag} {type_tag}")

                if text:
                    # Truncate long messages
                    display_text = text[:100] + "..." if len(text) > 100 else text
                    result.append(f"  {display_text}")

                result.append(f"  ID: {message_id}")
                result.append("")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error reading messages: {e}")
            return f"❌ Failed to read messages: {str(e)}"

    @mcp.tool()
    async def check_new_messages(
        instance_name: str = "genie", hours: int = 24, limit: int = 50
    ,
        ctx: Optional[Context] = None,) -> str:
        """Check recent incoming messages. Args: instance_name, hours (lookback), limit. Returns: messages grouped by sender."""
        client = get_client(ctx)

        try:
            from datetime import datetime, timedelta
            # Import models from parent package
            from ..models import TraceFilter

            start_time = datetime.utcnow() - timedelta(hours=hours)

            filters = TraceFilter(
                instance_name=instance_name, start_date=start_time, limit=limit
            )

            traces = await client.list_traces(filters)

            if not traces:
                return f"📱 No new messages in the last {hours} hours"

            result = [f"📱 NEW MESSAGES ({len(traces)} in last {hours}h)"]
            result.append("")

            # Group by sender
            by_sender: Dict[str, List[Any]] = {}
            for trace in traces:
                sender = trace.sender_name or trace.sender_phone
                if sender not in by_sender:
                    by_sender[sender] = []
                by_sender[sender].append(trace)

            for sender, msgs in by_sender.items():
                result.append(f"👤 {sender} ({len(msgs)})")
                for msg in msgs[:3]:  # Show max 3 per sender
                    timestamp = msg.received_at.strftime("%H:%M") if msg.received_at else "?"
                    msg_type = msg.message_type or "?"
                    result.append(f"  [{timestamp}] {msg_type}")
                if len(msgs) > 3:
                    result.append(f"  +{len(msgs) - 3} more")
                result.append("")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error checking new messages: {e}")
            return f"❌ Failed to check new messages: {str(e)}"
