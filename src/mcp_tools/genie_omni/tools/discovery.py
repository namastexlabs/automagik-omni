"""Discovery tools - Find and download information."""

import logging
import sqlite3
import os
import unicodedata
from typing import Callable, Optional
from pathlib import Path
import base64
from fastmcp import FastMCP, Context
from thefuzz import fuzz

logger = logging.getLogger(__name__)

def _get_db_path() -> str:
    """Get the SQLite database path from environment."""
    db_path = os.getenv("AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH", "/home/namastex/data/automagik-omni.db")
    return db_path

def _normalize_search(text: str) -> str:
    """Normalize search text: lowercase, remove accents, strip spaces."""
    if not text:
        return ""
    # Remove accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Lowercase and strip
    return text.lower().strip()


def register_tools(mcp: FastMCP, get_client: Callable, get_config: Callable):
    """Register discovery tools with the MCP server."""
    @mcp.tool()
    async def download_media(
        message_id: str, instance_name: str = "genie", filename: Optional[str] = None
,
        ctx: Optional[Context] = None,) -> str:
        """Download media from WhatsApp message (image/video/audio/document). Args: message_id, instance_name, filename (optional, auto-detected). Returns: local file path where saved."""
        import base64
        import os
        from pathlib import Path

        config = get_config(ctx)
        client = get_client(ctx)

        try:
            # Get media as base64
            response = await client.evolution_get_base64_media(
                instance_name=instance_name, message_id=message_id
            )

            if not response or "base64" not in response:
                logger.warning(f"No base64 data in response for message {message_id}")
                return None

            # Decode base64
            media_data = base64.b64decode(response["base64"])

            # Determine media type and subdirectory from mimetype
            mimetype = response.get("mimetype", "")
            if mimetype.startswith("image/"):
                media_subdir = "media/images"
                ext = mimetype.split("/")[-1] if "/" in mimetype else "jpg"
            elif mimetype.startswith("video/"):
                media_subdir = "media/videos"
                ext = mimetype.split("/")[-1] if "/" in mimetype else "mp4"
            elif mimetype.startswith("audio/"):
                media_subdir = "media/audio"
                ext = mimetype.split("/")[-1] if "/" in mimetype else "mp3"
            elif "sticker" in mimetype.lower():
                media_subdir = "media/stickers"
                ext = "webp"
            elif mimetype.startswith("application/") or mimetype.startswith("text/"):
                media_subdir = "media/documents"
                ext = mimetype.split("/")[-1] if "/" in mimetype else "bin"
            else:
                media_subdir = "downloads"
                ext = "bin"

            # Ensure download folder exists with subdirectory
            download_folder = Path(config.media_download_folder) / media_subdir
            download_folder.mkdir(parents=True, exist_ok=True)

            # Generate filename
            if filename:
                final_filename = filename
            else:
                # Use message ID + extension
                final_filename = f"{message_id}.{ext}"

            # Save file
            file_path = download_folder / final_filename
            with open(file_path, "wb") as f:
                f.write(media_data)

            logger.info(f"Media downloaded: {file_path} ({len(media_data)} bytes)")

            # Format size for display
            size_mb = len(media_data) / (1024 * 1024)
            size_str = f"{size_mb:.2f} MB" if size_mb >= 1 else f"{len(media_data) / 1024:.2f} KB"

            return f"✅ Media downloaded successfully\nFile: {file_path}\nSize: {size_str}"

        except Exception as e:
            logger.error(f"Failed to download media for message {message_id}: {e}")
            return f"❌ Failed to download media: {str(e)}"


# =============================================================================
# CATEGORY 1: WHO AM I (Identity & Context)
# =============================================================================


    @mcp.tool()
    async def find_message(
        trace_id: str, instance_name: str = "genie", include_payload: bool = False
,
        ctx: Optional[Context] = None,) -> str:
        """Get message details by trace ID. Args: trace_id, instance_name, include_payload. Returns: message details with status."""
        client = get_client(ctx)

        try:
            trace = await client.get_trace(trace_id)

            result = ["📱 MESSAGE DETAILS"]
            result.append(f"Trace ID: {trace.trace_id}")
            result.append(f"From: {trace.sender_name or trace.sender_phone}")
            result.append(f"Type: {trace.message_type or 'unknown'}")
            result.append(f"Status: {trace.status}")
            result.append(f"Received: {trace.received_at}")

            if trace.has_media:
                result.append("Media: Yes")

            if trace.error_message:
                result.append(f"Error: {trace.error_message}")

            if include_payload:
                payloads = await client.get_trace_payloads(trace_id, include_payload=True)
                result.append("")
                result.append(f"PAYLOADS ({len(payloads)} total):")
                for payload in payloads:
                    result.append(f"  Stage: {payload.stage}")
                    result.append(f"  Type: {payload.payload_type}")
                    result.append(f"  Time: {payload.timestamp}")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error finding message: {e}")
            return f"❌ Failed to find message: {str(e)}"


    @mcp.tool()
    async def find_person(search: str, instance_name: str = "genie",
        ctx: Optional[Context] = None,) -> str:
        """Find person by name with fuzzy search (handles typos, accents, case). Searches local DB + WhatsApp. Args: search (name), instance_name. Returns: matching contacts sorted by relevance."""
        all_contacts = {}  # phone_number -> {name, source, original_name, score}
        normalized_search = _normalize_search(search)
        MIN_SCORE = 60  # Minimum fuzzy match score (0-100)

        # 1. Search local contacts database first
        try:
            db = sqlite3.connect(_get_db_path())
            cursor = db.cursor()
            cursor.execute("SELECT phone_number, name, nickname FROM contacts")

            for phone, name, nickname in cursor.fetchall():
                # Normalize for fuzzy matching
                norm_name = _normalize_search(name)
                norm_nickname = _normalize_search(nickname) if nickname else ""

                # Calculate fuzzy scores
                name_score = fuzz.partial_ratio(normalized_search, norm_name)
                nickname_score = fuzz.partial_ratio(normalized_search, norm_nickname) if norm_nickname else 0

                # Use best score
                best_score = max(name_score, nickname_score)

                if best_score >= MIN_SCORE:
                    display_name = f"{name}" + (f" ({nickname})" if nickname else "")
                    all_contacts[phone] = {
                        "name": display_name,
                        "source": "local",
                        "original_name": name,
                        "score": best_score
                    }

            db.close()
        except Exception as e:
            logger.warning(f"Failed to search local contacts: {e}")

        # 2. Search Evolution API contacts
        client = get_client(ctx)
        try:
            contacts = await client.list_contacts(
                instance_name=instance_name, page=1, page_size=20, search_query=search
            )

            if contacts.contacts:
                for contact in contacts.contacts:
                    # Skip groups
                    if contact.id.endswith("@g.us"):
                        continue

                    phone = contact.id.replace("@s.whatsapp.net", "")

                    # Normalize and score
                    norm_contact_name = _normalize_search(contact.name)
                    score = fuzz.partial_ratio(normalized_search, norm_contact_name)

                    if score >= MIN_SCORE:
                        # Only add if not already in local contacts (local takes priority)
                        if phone not in all_contacts:
                            all_contacts[phone] = {
                                "name": contact.name,
                                "source": "whatsapp",
                                "original_name": contact.name,
                                "score": score
                            }

        except Exception as e:
            logger.warning(f"Failed to search Evolution contacts: {e}")

        # 3. Format results - SORTED BY SCORE (best match first)
        if not all_contacts:
            return f"📱 No contacts found matching '{search}'\n\n💡 Try: partial name, nickname, or phone number"

        result = [f"🔍 CONTACTS MATCHING '{search}' ({len(all_contacts)} found)"]
        result.append("")

        # Sort by score (highest first), then by name
        sorted_contacts = sorted(
            all_contacts.items(),
            key=lambda x: (-x[1]["score"], x[1]["original_name"].lower())
        )

        for phone, data in sorted_contacts:
            source_icon = "💾" if data["source"] == "local" else "📱"
            score_display = f"{data['score']}%" if data["score"] < 100 else ""
            result.append(f"{source_icon} {data['name']} {score_display}".strip())
            result.append(f"   📞 {phone}")
            result.append("")

        return "\n".join(result)


    @mcp.tool()
    async def search(query: str, instance_name: str = "genie",
        ctx: Optional[Context] = None,) -> str:
        """Universal search across people, groups, messages, and group members. Args: query (name/phone/keyword), instance_name. Returns: categorized results sorted by relevance."""
        MIN_SCORE = 60
        normalized_query = _normalize_search(query)

        # Results containers
        people_results = {}  # phone -> {name, source, score}
        group_results = {}   # group_id -> {name, members, score}
        message_results = [] # [{sender, text, time, mention}]

        client = get_client(ctx)

        # 1. Search People (Local + WhatsApp + Group Members)
        try:
            # Local contacts
            db = sqlite3.connect(_get_db_path())
            cursor = db.cursor()
            cursor.execute("SELECT phone_number, name, nickname FROM contacts")

            for phone, name, nickname in cursor.fetchall():
                norm_name = _normalize_search(name)
                norm_nickname = _normalize_search(nickname) if nickname else ""

                name_score = fuzz.partial_ratio(normalized_query, norm_name)
                nickname_score = fuzz.partial_ratio(normalized_query, norm_nickname) if norm_nickname else 0
                best_score = max(name_score, nickname_score)

                if best_score >= MIN_SCORE:
                    display_name = f"{name}" + (f" ({nickname})" if nickname else "")
                    people_results[phone] = {"name": display_name, "source": "local", "score": best_score}

            db.close()
        except Exception as e:
            logger.warning(f"Local search failed: {e}")

        try:
            # WhatsApp contacts
            contacts = await client.list_contacts(
                instance_name=instance_name, page=1, page_size=20, search_query=query
            )

            if contacts.contacts:
                for contact in contacts.contacts:
                    if contact.id.endswith("@g.us"):
                        continue

                    phone = contact.id.replace("@s.whatsapp.net", "")
                    norm_name = _normalize_search(contact.name)
                    score = fuzz.partial_ratio(normalized_query, norm_name)

                    if score >= MIN_SCORE and phone not in people_results:
                        people_results[phone] = {"name": contact.name, "source": "whatsapp", "score": score}
        except Exception as e:
            logger.warning(f"WhatsApp contacts search failed: {e}")

        # 2. Search Groups
        try:
            groups_response = await client.evolution_fetch_all_groups(
                instance_name=instance_name, get_participants=True
            )
            groups = groups_response if isinstance(groups_response, list) else groups_response.get("groups", [])

            for group in groups:
                group_name = group.get("subject") or group.get("name") or ""
                group_id = group.get("id") or group.get("remoteJid") or ""
                participants = group.get("participants", [])

                norm_group_name = _normalize_search(group_name)
                score = fuzz.partial_ratio(normalized_query, norm_group_name)

                if score >= MIN_SCORE:
                    member_count = len(participants) if isinstance(participants, list) else 0
                    group_results[group_id] = {"name": group_name, "members": member_count, "score": score}

                # Search group members
                if isinstance(participants, list):
                    for participant in participants:
                        participant_id = participant.get("id", "")
                        participant_phone = participant_id.replace("@s.whatsapp.net", "")

                        if participant_phone and participant_phone not in people_results:
                            # Try to match participant ID with query
                            score = fuzz.partial_ratio(normalized_query, participant_phone)
                            if score >= MIN_SCORE:
                                people_results[participant_phone] = {
                                    "name": f"Member of {group_name}",
                                    "source": "group",
                                    "score": score
                                }
        except Exception as e:
            logger.warning(f"Group search failed: {e}")

        # 3. Format Results
        if not people_results and not group_results and not message_results:
            return f"🔍 No results for '{query}'"

        result = [f"🔍 SEARCH: '{query}'", ""]

        # People
        if people_results:
            result.append(f"👤 PEOPLE ({len(people_results)})")
            sorted_people = sorted(people_results.items(), key=lambda x: (-x[1]["score"], x[1]["name"].lower()))
            for phone, data in sorted_people[:10]:
                icon = "💾" if data["source"] == "local" else "📱" if data["source"] == "whatsapp" else "👥"
                score_str = f" {data['score']}%" if data["score"] < 100 else ""
                result.append(f"{icon} {data['name']} - {phone}{score_str}")
            if len(sorted_people) > 10:
                result.append(f"... and {len(sorted_people) - 10} more")
            result.append("")

        # Groups
        if group_results:
            result.append(f"👥 GROUPS ({len(group_results)})")
            sorted_groups = sorted(group_results.items(), key=lambda x: (-x[1]["score"], x[1]["name"].lower()))
            for group_id, data in sorted_groups[:10]:
                score_str = f" {data['score']}%" if data["score"] < 100 else ""
                result.append(f"📱 {data['name']} - {group_id} ({data['members']} members){score_str}")
            if len(sorted_groups) > 10:
                result.append(f"... and {len(sorted_groups) - 10} more")
            result.append("")

        return "\n".join(result)


    @mcp.tool()
    async def find_chats(instance_name: str = "genie",
        ctx: Optional[Context] = None,) -> str:
        """Find all chat conversations in WhatsApp. Args: instance_name. Returns: list of chats with details."""
        client = get_client(ctx)

        try:
            response = await client.evolution_find_chats(instance_name=instance_name)

            # Evolution API returns different structures, handle both
            chats = response if isinstance(response, list) else response.get("chats", [])

            if not chats:
                return "💬 No chats found"

            result = [f"💬 ALL CHATS ({len(chats)} total)"]
            result.append("")

            for chat in chats[:50]:  # Limit to first 50 for readability
                # Extract chat info from various possible structures
                chat_id = chat.get("id") or chat.get("remoteJid") or "Unknown"
                chat_name = chat.get("name") or chat.get("pushName") or chat_id
                unread = chat.get("unreadCount") or 0
                is_group = "@g.us" in str(chat_id)

                icon = "👥" if is_group else "👤"
                result.append(f"{icon} {chat_name}")
                result.append(f"  ID: {chat_id}")
                if unread and unread > 0:
                    result.append(f"  Unread: {unread}")
                result.append("")

            if len(chats) > 50:
                result.append(f"... and {len(chats) - 50} more chats")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error finding chats: {e}")
            return f"❌ Failed to find chats: {str(e)}"


    @mcp.tool()
    async def list_all_groups(instance_name: str = "genie",
        ctx: Optional[Context] = None,) -> str:
        """List all WhatsApp groups you're a member of. Args: instance_name. Returns: groups with member counts."""
        client = get_client(ctx)

        try:
            response = await client.evolution_fetch_all_groups(
                instance_name=instance_name, get_participants=True
            )

            # Evolution API returns different structures
            groups = response if isinstance(response, list) else response.get("groups", [])

            if not groups:
                return "👥 No groups found"

            result = [f"👥 ALL GROUPS ({len(groups)} total)"]
            result.append("")

            for group in groups:
                # Extract group info
                group_id = group.get("id") or group.get("remoteJid") or "Unknown"
                group_name = group.get("subject") or group.get("name") or "Unnamed Group"
                participants = group.get("participants", [])
                participant_count = len(participants) if isinstance(participants, list) else group.get("size", 0)

                result.append(f"👥 {group_name}")
                result.append(f"  ID: {group_id}")
                result.append(f"  Members: {participant_count}")

                # Show creator if available
                owner = group.get("owner") or group.get("creator")
                if owner:
                    result.append(f"  Creator: {owner}")

                result.append("")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error listing groups: {e}")
            return f"❌ Failed to list groups: {str(e)}"


    @mcp.tool()
    async def get_group_members(group_jid: str, instance_name: str = "genie",
        ctx: Optional[Context] = None,) -> str:
        """Get members of a WhatsApp group with real phone numbers. Args: group_jid (from list_all_groups), instance_name. Returns: members with roles, LID, and real phone numbers."""
        client = get_client(ctx)

        try:
            response = await client.evolution_find_group_members(
                instance_name=instance_name, group_jid=group_jid
            )

            # Evolution API returns different structures
            participants = response if isinstance(response, list) else response.get("participants", [])

            if not participants:
                return f"👥 No members found in group {group_jid}"

            result = [f"👥 GROUP MEMBERS ({len(participants)} total)"]
            result.append(f"Group: {group_jid}")
            result.append("")

            for participant in participants:
                # Extract participant info
                lid = participant.get("id", "Unknown")
                phone = participant.get("phoneNumber", "Unknown")
                name = participant.get("name", "")
                is_admin = participant.get("admin") == "admin"
                is_super_admin = participant.get("admin") == "superadmin"

                # Clean phone number (remove @s.whatsapp.net suffix)
                if phone and "@" in phone:
                    phone = phone.split("@")[0]

                # Determine role
                if is_super_admin:
                    role = "👑 Super Admin"
                elif is_admin:
                    role = "⭐ Admin"
                else:
                    role = "👤 Member"

                # Format output with real phone number
                if name:
                    result.append(f"{role} {name}")
                    result.append(f"  LID: {lid}")
                    result.append(f"  Phone: {phone}")
                else:
                    result.append(f"{role} LID: {lid}")
                    result.append(f"  Phone: {phone}")
                result.append("")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error getting group members: {e}")
            return f"❌ Failed to get group members: {str(e)}"
