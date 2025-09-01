#!/usr/bin/env python3
"""
Discord command wrapper - provides a clean interface to Discord bot management.
This script provides a simple command interface that integrates with the CLI system.
"""
import sys
import logging
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from src.services.discord_service import discord_service
from core.telemetry import track_command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def start_discord_bot(instance_name: str) -> bool:
    """Start a Discord bot for the specified instance."""
    logger.info(f"Starting Discord bot for instance: {instance_name}")

    try:
        # Ensure Discord service is running
        if not discord_service.get_service_status()['service_running']:
            logger.info("Starting Discord service...")
            if not discord_service.start():
                logger.error("Failed to start Discord service")
                return False

        # Start the bot
        success = discord_service.start_bot(instance_name)

        if success:
            logger.info(f"✅ Discord bot '{instance_name}' started successfully!")
            track_command("discord_start_wrapper", success=True, instance_name=instance_name)
            return True
        else:
            logger.error(f"❌ Failed to start Discord bot '{instance_name}'")
            track_command("discord_start_wrapper", success=False, instance_name=instance_name)
            return False

    except Exception as e:
        logger.error(f"Error starting Discord bot '{instance_name}': {e}", exc_info=True)
        track_command("discord_start_wrapper", success=False, error=str(e))
        return False


def main():
    """Main entry point for Discord command wrapper."""
    if len(sys.argv) < 3:
        print("Usage: python src/commands/discord.py <command> <instance_name>")
        print("Commands: start, stop, restart, status")
        sys.exit(1)

    command = sys.argv[1]
    instance_name = sys.argv[2]

    logger.info(f"Discord command: {command} for instance: {instance_name}")

    try:
        if command == "start":
            success = start_discord_bot(instance_name)
            if success:
                print(f"Discord bot '{instance_name}' started successfully!")
                # Keep running to maintain the bot
                try:
                    print("Bot is running. Press Ctrl+C to stop...")
                    while True:
                        import time
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nShutting down Discord bot...")
                    discord_service.stop_bot(instance_name)
                    print("Discord bot stopped.")
            else:
                print(f"Failed to start Discord bot '{instance_name}'")
                sys.exit(1)

        elif command == "stop":
            success = discord_service.stop_bot(instance_name)
            if success:
                print(f"Discord bot '{instance_name}' stopped successfully!")
            else:
                print(f"Failed to stop Discord bot '{instance_name}' (may not be running)")
                sys.exit(1)

        elif command == "restart":
            success = discord_service.restart_bot(instance_name)
            if success:
                print(f"Discord bot '{instance_name}' restarted successfully!")
            else:
                print(f"Failed to restart Discord bot '{instance_name}'")
                sys.exit(1)

        elif command == "status":
            status = discord_service.get_bot_status(instance_name)
            if status:
                print(f"Discord bot '{instance_name}' status:")
                print(f"  Status: {status.get('status', 'unknown')}")
                print(f"  Guilds: {status.get('guild_count', 0)}")
                print(f"  Users: {status.get('user_count', 0)}")
                if status.get('latency'):
                    print(f"  Latency: {status['latency']:.2f}ms")
            else:
                print(f"Discord bot '{instance_name}' is not running or not found")

        else:
            print(f"Unknown command: {command}")
            print("Available commands: start, stop, restart, status")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
