"""Admin tools - Manage connections and configuration."""

import logging
from typing import Callable, Optional
from fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, get_client: Callable):
    """Register admin tools with the MCP server."""
# =============================================================================
# CATEGORY 5: ADMIN (Manage Connections - when needed)
# =============================================================================


    @mcp.tool()
    async def my_connections(
        ctx: Optional[Context] = None,) -> str:
        """List WhatsApp instances. Returns: all instances with status."""
        client = get_client(ctx)

        try:
            instances = await client.list_instances(skip=0, limit=100, include_status=True)

            if not instances:
                return "📱 No WhatsApp connections configured"

            result = [f"📱 MY WHATSAPP CONNECTIONS ({len(instances)} total)"]
            result.append("")

            for instance in instances:
                status = "✅ Connected" if instance.is_active else "❌ Disconnected"
                default = " (DEFAULT)" if instance.is_default else ""

                result.append(f"• {instance.name}{default}")
                result.append(f"  Number: {instance.phone_number or 'Not set'}")
                result.append(f"  Status: {status}")
                result.append(f"  Type: {instance.channel_type}")
                result.append("")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error listing connections: {e}")
            return f"❌ Failed to list connections: {str(e)}"


    @mcp.tool()
    async def connection_status(instance_name: str = "genie",
        ctx: Optional[Context] = None,) -> str:
        """Check WhatsApp instance connection status. Args: instance_name. Returns: detailed status."""
        client = get_client(ctx)

        try:
            status = await client.get_instance_status(instance_name)

            result = [f"📱 CONNECTION STATUS: {instance_name}"]
            result.append(f"Status: {status.status}")
            result.append(f"Type: {status.channel_type}")

            if status.channel_data:
                for key, value in status.channel_data.items():
                    result.append(f"{key}: {value}")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return f"❌ Failed to get connection status: {str(e)}"
