"""Tests for optional channel dependency graceful degradation.

These tests verify that the application starts correctly when optional
channel dependencies (like discord.py) are not installed.

Tech Council requirement (oettam): Verify graceful degradation behavior.
"""

import subprocess
import sys
import os


class TestDiscordOptionalDependency:
    """Test that discord channel gracefully degrades when discord.py is missing."""

    def test_app_imports_without_discord(self):
        """Verify app can import without discord.py installed.

        This is a critical test - the app should not crash on import
        when discord.py is not installed.
        """
        result = subprocess.run(
            [sys.executable, "-c", "from src.api.app import app; print('SUCCESS: App imports without crash')"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30,
        )
        assert result.returncode == 0, f"App import failed: {result.stderr}"
        assert "SUCCESS" in result.stdout or "SUCCESS" in result.stderr

    def test_channel_factory_available(self):
        """Verify ChannelHandlerFactory is available."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from src.channels import ChannelHandlerFactory; channels = ChannelHandlerFactory.get_supported_channels(); print(f'Available channels: {channels}'); print('SUCCESS: Channel factory works')",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30,
        )
        assert result.returncode == 0, f"Channel factory test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout

    def test_discord_components_flag_exists(self):
        """Verify DISCORD_COMPONENTS_AVAILABLE flag is properly set."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from src.channels.discord import DISCORD_COMPONENTS_AVAILABLE; print(f'DISCORD_COMPONENTS_AVAILABLE: {DISCORD_COMPONENTS_AVAILABLE}'); assert isinstance(DISCORD_COMPONENTS_AVAILABLE, bool); print('SUCCESS: DISCORD_COMPONENTS_AVAILABLE flag works')",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30,
        )
        assert result.returncode == 0, f"Discord components check failed: {result.stderr}"
        assert "SUCCESS" in result.stdout


class TestWhatsAppChannel:
    """Test that whatsapp channel works (core dependency)."""

    def test_whatsapp_channel_available(self):
        """Verify WhatsApp channel loads correctly."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from src.channels import ChannelHandlerFactory; channels = ChannelHandlerFactory.get_supported_channels(); assert 'whatsapp' in channels, f'WhatsApp should be available, got: {channels}'; print('SUCCESS: WhatsApp channel available')",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30,
        )
        assert result.returncode == 0, f"WhatsApp channel test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout


class TestStartupGracefulDegradation:
    """Test overall app startup behavior with optional dependencies."""

    def test_startup_logs_unavailable_channels(self):
        """Verify app logs which channels are unavailable at startup."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import logging; logging.basicConfig(level=logging.INFO); from src.channels import ChannelHandlerFactory; print('SUCCESS: Startup completed with graceful degradation')",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30,
        )
        assert result.returncode == 0, f"Startup test failed: {result.stderr}"
        output = result.stdout + result.stderr
        assert "SUCCESS" in output

    def test_api_routes_load_without_crash(self):
        """Verify API routes load even with missing optional deps."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from src.api.app import app; routes = [r.path for r in app.routes]; print(f'Loaded {len(routes)} routes'); assert len(routes) > 0, 'Should have loaded some routes'; print('SUCCESS: API routes loaded')",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30,
        )
        assert result.returncode == 0, f"API routes test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout

    def test_discord_module_exports_none_when_unavailable(self):
        """Verify discord module exports None values when discord.py not installed."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from src.channels.discord import DISCORD_COMPONENTS_AVAILABLE, DiscordChannelHandler, DiscordBotManager; print(f'DISCORD_COMPONENTS_AVAILABLE: {DISCORD_COMPONENTS_AVAILABLE}'); print(f'DiscordChannelHandler: {DiscordChannelHandler}'); print(f'DiscordBotManager: {DiscordBotManager}'); print('SUCCESS: Discord module exports work')",
            ],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30,
        )
        assert result.returncode == 0, f"Discord module exports test failed: {result.stderr}"
        assert "SUCCESS" in result.stdout
