"""
Instance status service with caching and parallel fetching.

Provides live connection status for instances by querying channel handlers
with timeouts and in-memory caching to prevent hammering external APIs.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from src.db.models import InstanceConfig
from src.channels.base import ChannelHandlerFactory

logger = logging.getLogger(__name__)

# Simple in-memory cache: {instance_name: (status, timestamp)}
_status_cache: Dict[str, Tuple[str, datetime]] = {}
CACHE_TTL_SECONDS = 5
STATUS_TIMEOUT_SECONDS = 3


async def get_live_status(instance: InstanceConfig) -> str:
    """
    Fetch live connection status for a single instance with caching.

    Returns: "connected" | "disconnected" | "connecting" | "error" | "unknown"
    """
    instance_name = instance.name

    # Check cache first
    if instance_name in _status_cache:
        cached_status, cached_at = _status_cache[instance_name]
        if datetime.utcnow() - cached_at < timedelta(seconds=CACHE_TTL_SECONDS):
            logger.debug(f"Cache hit for {instance_name}: {cached_status}")
            return cached_status

    try:
        handler = ChannelHandlerFactory.get_handler(instance.channel_type)

        # Fetch with timeout
        status_response = await asyncio.wait_for(
            handler.get_status(instance),
            timeout=STATUS_TIMEOUT_SECONDS
        )

        # Normalize status to standard values
        status = status_response.status
        if status == "open":
            status = "connected"
        elif status == "close":
            status = "disconnected"
        elif status not in ["connected", "disconnected", "connecting", "error"]:
            # Handle channel-specific status values
            if status in ["ready"]:
                status = "connected"
            elif status in ["closed", "offline"]:
                status = "disconnected"
            else:
                status = "unknown"

        # Cache the result
        _status_cache[instance_name] = (status, datetime.utcnow())
        logger.debug(f"Live status for {instance_name}: {status}")

        return status

    except asyncio.TimeoutError:
        logger.warning(f"Status fetch timeout for {instance_name}")
        return "unknown"
    except ValueError as e:
        # Unsupported channel type
        logger.warning(f"Unsupported channel type for {instance_name}: {e}")
        return "unknown"
    except Exception as e:
        logger.warning(f"Failed to get live status for {instance_name}: {e}")
        return "error"


async def get_live_statuses(instances: List[InstanceConfig]) -> Dict[str, str]:
    """
    Fetch live statuses for multiple instances in parallel.

    Returns: {instance_name: status}
    """
    if not instances:
        return {}

    async def fetch_one(instance: InstanceConfig) -> Tuple[str, str]:
        status = await get_live_status(instance)
        return (instance.name, status)

    # Execute all fetches in parallel
    results = await asyncio.gather(
        *[fetch_one(inst) for inst in instances],
        return_exceptions=True
    )

    status_map = {}
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Should not happen due to try/except in get_live_status
            logger.error(f"Unexpected exception in parallel fetch: {result}")
            status_map[instances[i].name] = "error"
        else:
            name, status = result
            status_map[name] = status

    return status_map


def clear_cache():
    """Clear the status cache (useful for testing)."""
    global _status_cache
    _status_cache = {}
    logger.debug("Status cache cleared")
