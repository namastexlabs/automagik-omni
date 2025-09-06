"""
CLI commands for Discord bot management using Typer.
"""

import typer
import time
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.services.discord_service import discord_service
from src.core.telemetry import track_command

app = typer.Typer(help="Discord bot management commands")
console = Console()


@app.command("start")
def start_bot(
    instance_name: str = typer.Argument(
        ..., help="Name of the Discord instance to start"
    )
):
    """Start a Discord bot for the specified instance."""
    start_time = time.time()

    try:
        console.print(
            f"[yellow]Starting Discord bot for instance: {instance_name}[/yellow]"
        )

        # Ensure Discord service is running
        if not discord_service.get_service_status()["service_running"]:
            console.print("[blue]Starting Discord service...[/blue]")
            if not discord_service.start():
                console.print("[red]❌ Failed to start Discord service[/red]")
                track_command(
                    "discord_start",
                    success=False,
                    error="Service start failed",
                    duration_ms=(time.time() - start_time) * 1000,
                )
                raise typer.Exit(1)

        # Start the bot
        success = discord_service.start_bot(instance_name)

        if success:
            console.print(
                f"[green]✅ Discord bot '{instance_name}' started successfully![/green]"
            )
            console.print("[dim]The bot will continue running in the background.[/dim]")
            track_command(
                "discord_start",
                success=True,
                instance_name=instance_name,
                duration_ms=(time.time() - start_time) * 1000,
            )
        else:
            console.print(
                f"[red]❌ Failed to start Discord bot '{instance_name}'[/red]"
            )
            track_command(
                "discord_start",
                success=False,
                instance_name=instance_name,
                duration_ms=(time.time() - start_time) * 1000,
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        track_command(
            "discord_start",
            success=False,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )
        raise typer.Exit(1)


@app.command("stop")
def stop_bot(
    instance_name: str = typer.Argument(
        ..., help="Name of the Discord instance to stop"
    )
):
    """Stop a Discord bot for the specified instance."""
    start_time = time.time()

    try:
        console.print(
            f"[yellow]Stopping Discord bot for instance: {instance_name}[/yellow]"
        )

        success = discord_service.stop_bot(instance_name)

        if success:
            console.print(
                f"[green]✅ Discord bot '{instance_name}' stopped successfully[/green]"
            )
            track_command(
                "discord_stop",
                success=True,
                instance_name=instance_name,
                duration_ms=(time.time() - start_time) * 1000,
            )
        else:
            console.print(
                f"[red]❌ Failed to stop Discord bot '{instance_name}' (may not be running)[/red]"
            )
            track_command(
                "discord_stop",
                success=False,
                instance_name=instance_name,
                duration_ms=(time.time() - start_time) * 1000,
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        track_command(
            "discord_stop",
            success=False,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )
        raise typer.Exit(1)


@app.command("restart")
def restart_bot(
    instance_name: str = typer.Argument(
        ..., help="Name of the Discord instance to restart"
    )
):
    """Restart a Discord bot for the specified instance."""
    start_time = time.time()

    try:
        console.print(
            f"[yellow]Restarting Discord bot for instance: {instance_name}[/yellow]"
        )

        # Ensure Discord service is running
        if not discord_service.get_service_status()["service_running"]:
            console.print("[blue]Starting Discord service...[/blue]")
            if not discord_service.start():
                console.print("[red]❌ Failed to start Discord service[/red]")
                track_command(
                    "discord_restart",
                    success=False,
                    error="Service start failed",
                    duration_ms=(time.time() - start_time) * 1000,
                )
                raise typer.Exit(1)

        success = discord_service.restart_bot(instance_name)

        if success:
            console.print(
                f"[green]✅ Discord bot '{instance_name}' restarted successfully[/green]"
            )
            track_command(
                "discord_restart",
                success=True,
                instance_name=instance_name,
                duration_ms=(time.time() - start_time) * 1000,
            )
        else:
            console.print(
                f"[red]❌ Failed to restart Discord bot '{instance_name}'[/red]"
            )
            track_command(
                "discord_restart",
                success=False,
                instance_name=instance_name,
                duration_ms=(time.time() - start_time) * 1000,
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        track_command(
            "discord_restart",
            success=False,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )
        raise typer.Exit(1)


@app.command("status")
def status_bot(
    instance_name: Optional[str] = typer.Argument(
        None, help="Name of the Discord instance to check (optional)"
    ),
):
    """Show status of Discord bot(s)."""
    start_time = time.time()

    try:
        if instance_name:
            # Show status for specific instance
            console.print(
                f"[blue]Checking status for Discord bot: {instance_name}[/blue]"
            )

            bot_status = discord_service.get_bot_status(instance_name)
            if bot_status:
                _display_bot_status(instance_name, bot_status)
            else:
                console.print(
                    f"[red]Discord bot '{instance_name}' is not running or not found[/red]"
                )

        else:
            # Show status for all bots
            console.print("[blue]Discord Service Status[/blue]")

            service_status = discord_service.get_service_status()
            _display_service_status(service_status)

            # Show running bots
            running_bots = discord_service.list_running_bots()
            if running_bots:
                console.print("\n[blue]Running Discord Bots:[/blue]")
                for bot_name in running_bots:
                    bot_status = discord_service.get_bot_status(bot_name)
                    if bot_status:
                        _display_bot_status(bot_name, bot_status, compact=True)
            else:
                console.print("\n[dim]No Discord bots currently running[/dim]")

        track_command(
            "discord_status",
            success=True,
            duration_ms=(time.time() - start_time) * 1000,
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        track_command(
            "discord_status",
            success=False,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )
        raise typer.Exit(1)


@app.command("list")
def list_instances():
    """List all available Discord instances."""
    start_time = time.time()

    try:
        console.print("[blue]Discord Instances[/blue]")

        instances = discord_service.list_available_instances()
        if not instances:
            console.print("[yellow]No Discord instances found in database[/yellow]")
            track_command(
                "discord_list",
                success=True,
                instance_count=0,
                duration_ms=(time.time() - start_time) * 1000,
            )
            return

        table = Table(title="Available Discord Instances")
        table.add_column("Name", style="cyan")
        table.add_column("Client ID", style="blue")
        table.add_column("Has Token", style="green")
        table.add_column("Status", style="magenta")
        table.add_column("Agent API URL", style="dim")
        table.add_column("Default Agent", style="dim")

        for instance in instances:
            status = "🟢 Running" if instance["is_running"] else "⚫ Stopped"
            token_status = "✓" if instance["has_token"] else "❌"

            table.add_row(
                instance["name"],
                instance["discord_client_id"] or "Not set",
                token_status,
                status,
                instance["agent_api_url"] or "Not set",
                instance["default_agent"] or "Not set",
            )

        console.print(table)
        track_command(
            "discord_list",
            success=True,
            instance_count=len(instances),
            duration_ms=(time.time() - start_time) * 1000,
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        track_command(
            "discord_list",
            success=False,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000,
        )
        raise typer.Exit(1)


def _display_service_status(service_status: dict):
    """Display Discord service status in a panel."""
    status_text = Text()

    if service_status["service_running"]:
        status_text.append("🟢 Service Running\n", style="green")
    else:
        status_text.append("🔴 Service Stopped\n", style="red")

    status_text.append(
        f"Event Loop: {'Active' if service_status['loop_thread_alive'] else 'Inactive'}\n"
    )
    status_text.append(f"Running Bots: {service_status['running_bots']}\n")

    if service_status["bot_instances"]:
        status_text.append(
            f"Bot Instances: {', '.join(service_status['bot_instances'])}"
        )

    console.print(
        Panel(status_text, title="Discord Service Status", border_style="blue")
    )


def _display_bot_status(instance_name: str, bot_status: dict, compact: bool = False):
    """Display bot status information."""
    if compact:
        # Compact display for list view
        status_emoji = {
            "connected": "🟢",
            "starting": "🟡",
            "disconnected": "🔴",
            "error": "❌",
        }.get(bot_status.get("status", "unknown"), "⚫")

        console.print(
            f"{status_emoji} {instance_name} - {bot_status.get('guild_count', 0)} guilds, {bot_status.get('user_count', 0)} users"
        )
        return

    # Detailed display
    status_text = Text()

    # Basic info
    status_text.append(f"Instance: {instance_name}\n", style="bold cyan")

    # Status with color coding
    status = bot_status.get("status", "unknown")
    status_style = {
        "connected": "green",
        "starting": "yellow",
        "disconnected": "red",
        "error": "red bold",
    }.get(status, "dim")

    status_text.append(f"Status: {status.title()}\n", style=status_style)

    # Connection info
    if status == "connected":
        status_text.append(
            f"Guilds: {bot_status.get('guild_count', 0)}\n", style="blue"
        )
        status_text.append(f"Users: {bot_status.get('user_count', 0)}\n", style="blue")
        status_text.append(
            f"Latency: {bot_status.get('latency', 0):.2f}ms\n", style="dim"
        )

    # Timestamps
    if bot_status.get("started_at"):
        started_at = bot_status["started_at"]
        if isinstance(started_at, str):
            status_text.append(f"Started: {started_at}\n", style="dim")
        else:
            status_text.append(
                f"Started: {started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
                style="dim",
            )

    if bot_status.get("last_heartbeat"):
        heartbeat = bot_status["last_heartbeat"]
        if isinstance(heartbeat, str):
            status_text.append(f"Last Heartbeat: {heartbeat}\n", style="dim")
        else:
            status_text.append(
                f"Last Heartbeat: {heartbeat.strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
                style="dim",
            )

    # Error message if any
    if bot_status.get("error_message"):
        status_text.append(f"Error: {bot_status['error_message']}\n", style="red")

    console.print(
        Panel(
            status_text,
            title=f"Discord Bot Status: {instance_name}",
            border_style="blue",
        )
    )
