"""Utility functions for Omni-Hub."""

import socket
from urllib.parse import urlparse


def get_local_ipv4() -> str:
    """Get the local network IPv4 address of the current machine.

    For WSL2, attempts to get the host Windows machine's local network IP.
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
        """Check if IP is likely Docker/WSL internal."""
        return ip.startswith(
            (
                "127.",
                "169.254.",
                "172.17.",
                "172.18.",
                "172.19.",
                "172.20.",
                "172.21.",
                "10.0.2.",
                "10.255.",
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
        # For WSL2, try to get the Windows host IP
        if is_wsl():
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

            try:
                # Method 3: Try cmd ipconfig via WSL
                result = subprocess.run(
                    ["cmd.exe", "/c", "ipconfig"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    lines = result.stdout.split("\n")
                    for line in lines:
                        if "IPv4 Address" in line and ":" in line:
                            ip = line.split(":")[1].strip()
                            if ip and "(" in ip:
                                ip = ip.split("(")[0].strip()
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

    Args:
        url: The URL that may contain localhost, 127.0.0.1, or 0.0.0.0

    Returns:
        str: The URL with localhost/0.0.0.0 replaced by actual IPv4 address
    """
    if not url:
        return url

    # Parse the URL to check if it contains localhost or 0.0.0.0
    parsed = urlparse(url)
    if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
        ipv4_address = get_local_ipv4()
        # Replace localhost/127.0.0.1/0.0.0.0 with actual IPv4
        return url.replace(parsed.hostname, ipv4_address)

    return url


def ensure_ipv4_in_config(config_dict: dict, url_fields: list = None) -> dict:
    """Ensure all localhost URLs in a config dictionary use actual IPv4 addresses.

    Args:
        config_dict: Dictionary containing configuration values
        url_fields: List of field names that contain URLs to process

    Returns:
        dict: Updated configuration with localhost replaced by IPv4 addresses
    """
    if url_fields is None:
        # Common URL field names
        url_fields = ["evolution_url", "agent_api_url", "webhook_url", "api_url"]

    updated_config = config_dict.copy()

    for field in url_fields:
        if field in updated_config and updated_config[field]:
            updated_config[field] = replace_localhost_with_ipv4(updated_config[field])

    return updated_config
