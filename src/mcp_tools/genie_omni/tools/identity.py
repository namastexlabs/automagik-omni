"""Identity tools - Who am I on WhatsApp?"""

import logging
from typing import Callable, Optional
from fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, get_client: Callable):
    """Register identity tools with the MCP server."""

    @mcp.tool()
    async def my_whatsapp_info(instance_name: str = "genie",
        ctx: Optional[Context] = None,) -> str:
        """Get WhatsApp identity and connection status. Args: instance_name. Returns: number, status, profile info."""
        client = get_client(ctx)

        try:
            # Get instance details
            instance = await client.get_instance(instance_name, include_status=True)

            result = []
            result.append("📱 MY WHATSAPP IDENTITY")
            result.append(f"Instance: {instance.name}")
            result.append(f"Number: {instance.phone_number or 'Not configured'}")
            result.append(f"Type: {instance.channel_type}")
            result.append(
                f"Status: {instance.evolution_status.get('state', 'unknown') if instance.evolution_status else 'unknown'}"
            )
            result.append(f"Connected: {'✅ Yes' if instance.is_active else '❌ No'}")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error getting WhatsApp info: {e}")
            return f"❌ Failed to get WhatsApp info: {str(e)}"
