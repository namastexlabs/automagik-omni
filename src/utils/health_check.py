"""Health check utilities for service dependencies."""

import asyncio
import logging
import aiohttp


logger = logging.getLogger(__name__)


async def wait_for_api_health(
    api_url: str = "http://localhost:8882", timeout: int = 60, check_interval: float = 2.0
) -> bool:
    """
    Wait for API to become healthy.

    Args:
        api_url: Base URL of the API to check
        timeout: Maximum time to wait in seconds
        check_interval: Time between health checks in seconds

    Returns:
        True if API becomes healthy, False if timeout
    """
    health_endpoint = f"{api_url}/health"
    start_time = asyncio.get_event_loop().time()

    logger.info(f"Waiting for API health at {health_endpoint}")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(health_endpoint, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "healthy":
                            logger.info("API is healthy!")
                            return True
                        else:
                            logger.debug(f"API not healthy yet: {data}")

            except Exception as e:
                logger.debug(f"Health check failed: {e}")

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                logger.error(f"API health check timed out after {timeout}s")
                return False

            # Wait before next check
            await asyncio.sleep(check_interval)


def check_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available (not in use).

    Args:
        host: Host to check
        port: Port number to check

    Returns:
        True if port is available, False if in use
    """
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Port available if connection fails
    except Exception:
        return False
