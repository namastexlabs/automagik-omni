"""Contact and conversation tools - Who do I know? Who am I talking to?"""

import logging
import sqlite3
import os
from typing import Callable, Optional, Literal
from fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)

# Track if we've already initialized the contacts table
_contacts_table_initialized = False

def _get_db_path() -> str:
    """Get the SQLite database path from environment."""
    db_path = os.getenv("AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH", "/home/namastex/data/automagik-omni.db")
    return db_path

def _ensure_contacts_table():
    """Ensure contacts table exists. Runs once per process, safe to call multiple times."""
    global _contacts_table_initialized

    if _contacts_table_initialized:
        return

    try:
        db = sqlite3.connect(_get_db_path())
        db.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                nickname TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        db.close()
        _contacts_table_initialized = True
        logger.info("✅ Contacts table initialized")
    except Exception as e:
        logger.error(f"Failed to initialize contacts table: {e}")
        raise


def register_tools(mcp: FastMCP, get_client: Callable):
    """Register contact and conversation tools with the MCP server."""

    @mcp.tool()
    async def my_contacts(
        instance_name: str = "genie", search: Optional[str] = None, limit: int = 50
    ,
        ctx: Optional[Context] = None,) -> str:
        """Get contacts from WhatsApp. Args: instance_name, search query, limit. Returns: list of contacts with names and phone numbers."""
        client = get_client(ctx)

        try:
            contacts = await client.list_contacts(
                instance_name=instance_name, page=1, page_size=limit, search_query=search
            )

            if not contacts.contacts:
                return "📱 No contacts found" + (f" matching '{search}'" if search else "")

            result = [f"📱 CONTACTS ({contacts.total_count} total)"]
            if search:
                result[0] += f" - Search: '{search}'"
            result.append("")

            for contact in contacts.contacts:
                result.append(f"• {contact.name}")
                result.append(f"  {contact.id}")
                if contact.status:
                    result.append(f"  Status: {contact.status}")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return f"❌ Failed to get contacts: {str(e)}"

    @mcp.tool()
    async def my_conversations(
        instance_name: str = "genie",
        conversation_type: Optional[Literal["direct", "group", "all"]] = "all",
        limit: int = 20,
    
        ctx: Optional[Context] = None,) -> str:
        """Get active WhatsApp conversations. Args: instance_name, conversation_type filter, limit. Returns: list of active chats."""
        client = get_client(ctx)

        try:
            chat_filter = None if conversation_type == "all" else conversation_type

            chats = await client.list_chats(
                instance_name=instance_name,
                page=1,
                page_size=limit,
                chat_type_filter=chat_filter,
            )

            if not chats.chats:
                return "💬 No conversations found" + (
                    f" (type: {conversation_type})" if conversation_type != "all" else ""
                )

            result = [f"💬 CONVERSATIONS ({chats.total_count} total)"]
            if conversation_type != "all":
                result[0] += f" - Type: {conversation_type}"
            result.append("")

            for chat in chats.chats:
                emoji = "👤" if chat.chat_type == "direct" else "👥"
                unread = f" ({chat.unread_count} unread)" if chat.unread_count and chat.unread_count > 0 else ""
                result.append(f"{emoji} {chat.name}{unread}")
                if chat.last_message_at:
                    result.append(f"  Last: {chat.last_message_at}")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return f"❌ Failed to get conversations: {str(e)}"

    @mcp.tool()
    async def add_contact(
        phone_number: str,
        name: str,
        nickname: Optional[str] = None,
        notes: Optional[str] = None
    ,
        ctx: Optional[Context] = None,) -> str:
        """Add contact to local database. Args: phone_number, name, nickname, notes. Returns: confirmation."""
        _ensure_contacts_table()

        try:
            db = sqlite3.connect(_get_db_path())
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO contacts (phone_number, name, nickname, notes)
                VALUES (?, ?, ?, ?)
            """, (phone_number, name, nickname, notes))

            db.commit()
            db.close()

            result = [f"✅ Contact added: {name}"]
            result.append(f"📞 Phone: {phone_number}")
            if nickname:
                result.append(f"🏷️  Nickname: {nickname}")
            if notes:
                result.append(f"📝 Notes: {notes}")

            return "\n".join(result)

        except sqlite3.IntegrityError:
            return f"❌ Contact already exists with phone number: {phone_number}"
        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            return f"❌ Failed to add contact: {str(e)}"

    @mcp.tool()
    async def update_contact(
        phone_number: str,
        name: Optional[str] = None,
        nickname: Optional[str] = None,
        notes: Optional[str] = None
    ,
        ctx: Optional[Context] = None,) -> str:
        """Update existing contact in local database. Args: phone_number, name, nickname, notes. Returns: confirmation."""
        _ensure_contacts_table()

        if not any([name, nickname, notes]):
            return "❌ Must provide at least one field to update (name, nickname, or notes)"

        try:
            db = sqlite3.connect(_get_db_path())
            cursor = db.cursor()

            # Build dynamic UPDATE query
            updates = []
            values = []

            if name is not None:
                updates.append("name = ?")
                values.append(name)
            if nickname is not None:
                updates.append("nickname = ?")
                values.append(nickname)
            if notes is not None:
                updates.append("notes = ?")
                values.append(notes)

            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(phone_number)

            query = f"UPDATE contacts SET {', '.join(updates)} WHERE phone_number = ?"
            cursor.execute(query, values)

            if cursor.rowcount == 0:
                db.close()
                return f"❌ No contact found with phone number: {phone_number}"

            db.commit()
            db.close()

            result = [f"✅ Contact updated: {phone_number}"]
            if name:
                result.append(f"📝 Name: {name}")
            if nickname:
                result.append(f"🏷️  Nickname: {nickname}")
            if notes:
                result.append(f"📝 Notes: {notes}")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return f"❌ Failed to update contact: {str(e)}"

    @mcp.tool()
    async def remove_contact(phone_number: str,
        ctx: Optional[Context] = None,) -> str:
        """Remove contact from local database. Args: phone_number. Returns: confirmation."""
        _ensure_contacts_table()

        try:
            db = sqlite3.connect(_get_db_path())
            cursor = db.cursor()

            # Get contact info before deleting
            cursor.execute("SELECT name FROM contacts WHERE phone_number = ?", (phone_number,))
            row = cursor.fetchone()

            if not row:
                db.close()
                return f"❌ No contact found with phone number: {phone_number}"

            contact_name = row[0]

            cursor.execute("DELETE FROM contacts WHERE phone_number = ?", (phone_number,))
            db.commit()
            db.close()

            return f"✅ Contact removed: {contact_name} ({phone_number})"

        except Exception as e:
            logger.error(f"Error removing contact: {e}")
            return f"❌ Failed to remove contact: {str(e)}"
