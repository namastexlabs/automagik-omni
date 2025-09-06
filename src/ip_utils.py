"""Utility functions for Omni-Hub."""

import socket
from typing import Optional
from urllib.parse import urlparse


def get_local_ipv4() -> str:
    """Get the local network IPv4 address of the current machine.

    For WSL2, returns the WSL2 IP address for better container accessibility.
    For other systems, prioritizes local network addresses (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    over Docker/WSL internal addresses.

    Returns:
        str: The local network IPv4 address, or '127.0.0.1' if unable to determine
    """
    import subprocess
    import platform

    def is_local_network_ip(ip: str) -> bool:
        """Check if IP is in local network ranges."""
        if ip.startswith("192.168."):
            return True
        elif ip.startswith("10."):
            # Exclude some common Docker/internal ranges
            if ip.startswith(("10.0.2.", "10.255.")):
                return False
            return True
        elif ip.startswith("172."):
            parts = ip.split(".")
            if len(parts) >= 2:
                try:
                    second_octet = int(parts[1])
                    return 16 <= second_octet <= 31
                except ValueError:
                    return False
        return False

    def is_docker_wsl_internal_ip(ip: str) -> bool:
        """Check if IP is likely Docker/WSL internal (but allow WSL2 bridge network)."""
        # Don't consider WSL2 bridge network as internal if it's the main interface
        if ip.startswith("172.19.") and is_wsl():
            return False  # WSL2 bridge network is accessible from containers

        return ip.startswith(
            (
                "127.",
                "169.254.",
                "172.17.",  # Docker default bridge
                "172.18.",  # Docker custom bridge
                "172.20.",
                "172.21.",
                "10.0.2.",  # VirtualBox
                "10.255.",  # WSL2 internal
            )
        )

    def is_wsl() -> bool:
        """Check if running in WSL."""
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
        except (OSError, IOError):
            return False

    try:
        # For WSL2, prioritize WSL2 IP for better container accessibility
        if is_wsl():
            # First, try to get the WSL2 IP address (better for containers)
            try:
                # Get WSL2 IP from eth0 interface
                result = subprocess.run(
                    ["ip", "addr", "show", "eth0"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    lines = result.stdout.split("\n")
                    for line in lines:
                        if "inet " in line and "scope global" in line:
                            parts = line.strip().split()
                            for part in parts:
                                if "/" in part and not part.startswith("inet"):
                                    ip = part.split("/")[0]
                                    # Use WSL2 IP if it's accessible and not localhost
                                    if (
                                        ip
                                        and ip != "127.0.0.1"
                                        and not ip.startswith("169.254.")
                                    ):
                                        return ip
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            # Fallback: Try to get Windows host IP via PowerShell (for external access)
            try:
                # Method 1: Try to get Windows host IP via PowerShell
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-Command",
                        "Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi*','Ethernet*' -PrefixOrigin Dhcp | Select-Object IPAddress | Format-Table -HideTableHeaders",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        ip = line.strip()
                        if (
                            ip
                            and is_local_network_ip(ip)
                            and not is_docker_wsl_internal_ip(ip)
                        ):
                            return ip
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ):
                pass

            try:
                # Method 2: Alternative PowerShell command
                result = subprocess.run(
                    [
                        "powershell.exe",
                        "-Command",
                        "(Get-NetIPConfiguration | Where-Object {$_.NetAdapter.Status -eq 'Up' -and $_.IPv4Address.IPAddress -like '192.168.*'}).IPv4Address.IPAddress",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    ip = result.stdout.strip()
                    if ip and is_local_network_ip(ip):
                        return ip
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ):
                pass

        # Standard method for non-WSL or WSL fallback
        all_ips = []

        # Method 1: Try using system commands
        try:
            if platform.system() == "Windows":
                # Windows ipconfig
                result = subprocess.run(
                    ["ipconfig"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.split("\n")
                    for line in lines:
                        if "IPv4 Address" in line and ":" in line:
                            ip = line.split(":")[1].strip()
                            if ip and "(" in ip:
                                ip = ip.split("(")[0].strip()
                            if ip and ip != "127.0.0.1":
                                all_ips.append(ip)
            else:
                # Linux/Unix systems
                try:
                    # Try ip command first
                    result = subprocess.run(
                        ["ip", "addr", "show"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split("\n")
                        for line in lines:
                            if "inet " in line and "scope global" in line:
                                parts = line.strip().split()
                                for part in parts:
                                    if "/" in part and not part.startswith("inet"):
                                        ip = part.split("/")[0]
                                        if ip and ip != "127.0.0.1":
                                            all_ips.append(ip)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback to ifconfig
                    try:
                        result = subprocess.run(
                            ["ifconfig"], capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            lines = result.stdout.split("\n")
                            for line in lines:
                                if "inet " in line:
                                    parts = line.strip().split()
                                    for i, part in enumerate(parts):
                                        if part == "inet" and i + 1 < len(parts):
                                            ip = parts[i + 1]
                                            if ip and ip != "127.0.0.1":
                                                all_ips.append(ip)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        pass
        except Exception:
            pass

        # Method 2: Socket method as additional source
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                socket_ip = s.getsockname()[0]
                if socket_ip and socket_ip != "127.0.0.1":
                    all_ips.append(socket_ip)
        except Exception:
            pass

        # Remove duplicates while preserving order
        unique_ips = []
        for ip in all_ips:
            if ip not in unique_ips:
                unique_ips.append(ip)

        # Priority 1: Look for 192.168.x.x addresses first (most common home networks)
        for ip in unique_ips:
            if ip.startswith("192.168.") and not is_docker_wsl_internal_ip(ip):
                return ip

        # Priority 2: Look for other local network ranges (but exclude common internal ones)
        for ip in unique_ips:
            if is_local_network_ip(ip) and not is_docker_wsl_internal_ip(ip):
                return ip

        # Priority 3: Any non-localhost, non-docker IP
        for ip in unique_ips:
            if not is_docker_wsl_internal_ip(ip):
                return ip

        # Priority 4: Any IP that's not localhost
        for ip in unique_ips:
            if ip != "127.0.0.1":
                return ip

    except Exception:
        pass

    # Final fallback
    return "127.0.0.1"


def replace_localhost_with_ipv4(url: str) -> str:
    """Replace localhost/0.0.0.0 in a URL with the actual IPv4 address.

    This function ONLY replaces localhost, 127.0.0.1, and 0.0.0.0 hostnames.
    Proper domains like 'agentsapi.com' or 'api.example.com' are preserved unchanged.

    Args:
        url: The URL that may contain localhost, 127.0.0.1, or 0.0.0.0

    Returns:
        str: The URL with localhost/0.0.0.0 replaced by actual IPv4 address.
             Domain names and external IPs are preserved unchanged.

    Examples:
        >>> replace_localhost_with_ipv4('http://localhost:58881')
        'http://172.19.209.168:58881'
        >>> replace_localhost_with_ipv4('https://agentsapi.com:8080')
        'https://agentsapi.com:8080'  # Unchanged
        >>> replace_localhost_with_ipv4('http://192.168.1.100:3000')
        'http://192.168.1.100:3000'  # Unchanged
    """
    if not url:
        return url

    # Parse the URL to check if it contains localhost or 0.0.0.0
    parsed = urlparse(url)
    hostname = parsed.hostname

    # Only replace specific localhost-style hostnames
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
        ipv4_address = get_local_ipv4()
        # Replace localhost/127.0.0.1/0.0.0.0 with actual IPv4
        return url.replace(hostname, ipv4_address)

    # Return unchanged for:
    # - Domain names (e.g., agentsapi.com, api.example.com)
    # - External IP addresses (e.g., 192.168.1.100, 10.0.0.1)
    # - Any other valid hostname
    return url


def get_container_accessible_ip() -> str:
    """Get IP address that's accessible from both WSL2 and Docker containers.

    Returns:
        str: IP address that works for cross-container communication
    """
    # For WSL2, the eth0 IP is accessible from Docker containers
    import subprocess

    try:
        # Try to get WSL2 eth0 IP first
        result = subprocess.run(
            ["ip", "addr", "show", "eth0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            for line in lines:
                if "inet " in line and "scope global" in line:
                    parts = line.strip().split()
                    for part in parts:
                        if "/" in part and not part.startswith("inet"):
                            ip = part.split("/")[0]
                            if ip and ip != "127.0.0.1":
                                return ip
    except Exception:
        pass

    # Fallback to standard detection
    return get_local_ipv4()


def is_localhost_url(url: str) -> bool:
    """Check if a URL uses localhost-style hostname that should be replaced.

    Args:
        url: The URL to check

    Returns:
        bool: True if URL uses localhost/127.0.0.1/0.0.0.0, False for domains/external IPs
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        return parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0")
    except Exception:
        return False


def ensure_ipv4_in_config(config_dict: dict, url_fields: Optional[list] = None) -> dict:
    """Ensure all localhost URLs in a config dictionary use actual IPv4 addresses.

    This function ONLY replaces localhost-style URLs. Domain names and external IPs
    are preserved unchanged to support cloud-hosted and external agent APIs.

    Args:
        config_dict: Dictionary containing configuration values
        url_fields: List of field names that contain URLs to process

    Returns:
        dict: Updated configuration with localhost replaced by IPv4 addresses.
              Domain names like 'agentsapi.com' are preserved unchanged.

    Examples:
        >>> ensure_ipv4_in_config({'agent_api_url': 'http://localhost:58881'})
        {'agent_api_url': 'http://172.19.209.168:58881'}
        >>> ensure_ipv4_in_config({'agent_api_url': 'https://agentsapi.com:8080'})
        {'agent_api_url': 'https://agentsapi.com:8080'}  # Unchanged
    """
    if url_fields is None:
        # Common URL field names
        url_fields = ["evolution_url", "agent_api_url", "webhook_url", "api_url"]

    updated_config = config_dict.copy()

    for field in url_fields:
        if field in updated_config and updated_config[field]:
            original_url = updated_config[field]
            # Only replace if it's a localhost-style URL
            if is_localhost_url(original_url):
                updated_config[field] = replace_localhost_with_ipv4(original_url)

    return updated_config
