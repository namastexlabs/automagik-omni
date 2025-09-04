"""
CLI commands for managing user allowlists across instances and channels.
"""

import typer
from typing import Optional
import logging
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from src.db.database import SessionLocal
from src.services.allowlist_service import AllowlistService
from src.db.models import InstanceConfig

# Create Typer app
app = typer.Typer(help="Manage user allowlists for instances")

# Rich console for better output
console = Console()
logger = logging.getLogger(__name__)


@app.command("add")
def add_user(
    instance_name: str = typer.Argument(..., help="Instance name"),
    channel_type: str = typer.Argument(..., help="Channel type (whatsapp, discord, etc.)"),
    user_identifier: str = typer.Argument(..., help="Channel-specific user identifier"),
    display_name: Optional[str] = typer.Option(None, "--name", "-n", help="Display name for the user"),
    added_by: Optional[str] = typer.Option(None, "--added-by", "-b", help="Who is adding this user"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Optional notes about this user"),
):
    """Add a user to the allowlist for an instance."""
    try:
        with SessionLocal() as db:
            allowlist_service = AllowlistService(db)

            # Add the user
            allowlist_service.add_user(
                instance_name=instance_name,
                channel_type=channel_type,
                user_identifier=user_identifier,
                display_name=display_name,
                added_by=added_by,
                notes=notes,
            )

            rprint("✅ [green]Successfully added user to allowlist[/green]")
            rprint(f"   Instance: [bold]{instance_name}[/bold]")
            rprint(f"   Channel: [bold]{channel_type}[/bold]")
            rprint(f"   User: [bold]{user_identifier}[/bold]")
            if display_name:
                rprint(f"   Name: {display_name}")
            if notes:
                rprint(f"   Notes: {notes}")

    except ValueError as e:
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Unexpected error adding user: {str(e)}")
        rprint(f"❌ [red]Unexpected error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("remove")
def remove_user(
    instance_name: str = typer.Argument(..., help="Instance name"),
    channel_type: str = typer.Argument(..., help="Channel type (whatsapp, discord, etc.)"),
    user_identifier: str = typer.Argument(..., help="Channel-specific user identifier"),
):
    """Remove a user from the allowlist for an instance."""
    try:
        with SessionLocal() as db:
            allowlist_service = AllowlistService(db)

            # Remove the user
            success = allowlist_service.remove_user(
                instance_name=instance_name, channel_type=channel_type, user_identifier=user_identifier
            )

            if success:
                rprint("✅ [green]Successfully removed user from allowlist[/green]")
                rprint(f"   Instance: [bold]{instance_name}[/bold]")
                rprint(f"   Channel: [bold]{channel_type}[/bold]")
                rprint(f"   User: [bold]{user_identifier}[/bold]")
            else:
                rprint("⚠️  [yellow]User not found in allowlist[/yellow]")
                rprint(f"   Instance: {instance_name}")
                rprint(f"   Channel: {channel_type}")
                rprint(f"   User: {user_identifier}")

    except Exception as e:
        logger.error(f"Error removing user: {str(e)}")
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_users(
    instance_name: Optional[str] = typer.Option(None, "--instance", "-i", help="Filter by instance name"),
    channel_type: Optional[str] = typer.Option(None, "--channel", "-c", help="Filter by channel type"),
    show_inactive: bool = typer.Option(False, "--include-inactive", help="Include inactive users"),
):
    """List allowed users with optional filtering."""
    try:
        with SessionLocal() as db:
            allowlist_service = AllowlistService(db)

            # Get users
            users = allowlist_service.list_users(
                instance_name=instance_name, channel_type=channel_type, active_only=not show_inactive
            )

            if not users:
                rprint("📝 [yellow]No allowed users found with the specified filters[/yellow]")
                return

            # Create table
            table = Table(title="Allowed Users")
            table.add_column("Instance", style="cyan")
            table.add_column("Channel", style="magenta")
            table.add_column("User ID", style="green")
            table.add_column("Display Name", style="blue")
            table.add_column("Added By", style="yellow")
            table.add_column("Status", justify="center")
            table.add_column("Created", style="dim")

            for user in users:
                status = "🟢 Active" if user.is_active else "🔴 Inactive"
                display_name = user.display_name or "—"
                added_by = user.added_by or "—"
                created = user.created_at.strftime("%Y-%m-%d %H:%M")

                table.add_row(
                    user.instance_name, user.channel_type, user.user_identifier, display_name, added_by, status, created
                )

            console.print(table)
            rprint(f"\n📊 Total users: [bold]{len(users)}[/bold]")

    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("enable")
def enable_allowlist(
    instance_name: str = typer.Argument(..., help="Instance name"),
):
    """Enable the allowlist for an instance."""
    try:
        with SessionLocal() as db:
            allowlist_service = AllowlistService(db)

            # Enable allowlist
            success = allowlist_service.enable_allowlist(instance_name)

            if success:
                rprint(f"✅ [green]Allowlist enabled for instance[/green] [bold]{instance_name}[/bold]")
                rprint("⚠️  [yellow]Note: Only users in the allowlist will be able to send messages[/yellow]")
            else:
                rprint(f"❌ [red]Failed to enable allowlist for instance {instance_name}[/red]")

    except ValueError as e:
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error enabling allowlist: {str(e)}")
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("disable")
def disable_allowlist(
    instance_name: str = typer.Argument(..., help="Instance name"),
):
    """Disable the allowlist for an instance."""
    try:
        with SessionLocal() as db:
            allowlist_service = AllowlistService(db)

            # Disable allowlist
            success = allowlist_service.disable_allowlist(instance_name)

            if success:
                rprint(f"✅ [green]Allowlist disabled for instance[/green] [bold]{instance_name}[/bold]")
                rprint("ℹ️  [blue]All users can now send messages to this instance[/blue]")
            else:
                rprint(f"❌ [red]Failed to disable allowlist for instance {instance_name}[/red]")

    except ValueError as e:
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error disabling allowlist: {str(e)}")
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("status")
def show_status(
    instance_name: Optional[str] = typer.Option(None, "--instance", "-i", help="Show status for specific instance"),
):
    """Show allowlist status and statistics."""
    try:
        with SessionLocal() as db:
            allowlist_service = AllowlistService(db)

            if instance_name:
                # Show status for specific instance
                try:
                    stats = allowlist_service.get_instance_status(instance_name)

                    rprint(f"📊 [bold]Allowlist Status for {instance_name}[/bold]")
                    rprint(f"   Status: {'🟢 Enabled' if stats['allowlist_enabled'] else '🔴 Disabled'}")
                    rprint(f"   Total allowed users: [bold]{stats['total_allowed_users']}[/bold]")

                    if stats["users_by_channel"]:
                        rprint("   Users by channel:")
                        for channel, count in stats["users_by_channel"].items():
                            if count > 0:
                                rprint(f"     • {channel}: {count}")

                except ValueError as e:
                    rprint(f"❌ [red]Error: {str(e)}[/red]")
                    raise typer.Exit(1)
            else:
                # Show status for all instances - build stats manually
                instances = db.query(InstanceConfig).all()
                stats = {
                    "total_instances": len(instances),
                    "instances_with_allowlist": sum(1 for i in instances if i.allowlist_enabled),
                    "instances": [],
                }

                for instance in instances:
                    try:
                        instance_stats = allowlist_service.get_instance_status(instance.name)
                        stats["instances"].append(instance_stats)
                    except Exception as e:
                        logger.error(f"Error getting stats for instance {instance.name}: {str(e)}")

                rprint("📊 [bold]Global Allowlist Status[/bold]")
                rprint(f"   Total instances: [bold]{stats['total_instances']}[/bold]")
                rprint(f"   Instances with allowlist enabled: [bold]{stats['instances_with_allowlist']}[/bold]")

                if stats["instances"]:
                    # Create table for all instances
                    table = Table(title="Instance Status")
                    table.add_column("Instance", style="cyan")
                    table.add_column("Status", justify="center")
                    table.add_column("Allowed Users", justify="right", style="green")
                    table.add_column("WhatsApp", justify="right", style="blue")
                    table.add_column("Discord", justify="right", style="magenta")

                    for instance_stats in stats["instances"]:
                        status = "🟢 Enabled" if instance_stats["allowlist_enabled"] else "🔴 Disabled"
                        whatsapp_count = instance_stats["users_by_channel"].get("whatsapp", 0)
                        discord_count = instance_stats["users_by_channel"].get("discord", 0)

                        table.add_row(
                            instance_stats["instance_name"],
                            status,
                            str(instance_stats["total_allowed_users"]),
                            str(whatsapp_count) if whatsapp_count > 0 else "—",
                            str(discord_count) if discord_count > 0 else "—",
                        )

                    console.print(table)

    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command("check")
def check_user(
    instance_name: str = typer.Argument(..., help="Instance name"),
    channel_type: str = typer.Argument(..., help="Channel type (whatsapp, discord, etc.)"),
    user_identifier: str = typer.Argument(..., help="Channel-specific user identifier"),
):
    """Check if a user would be allowed to send messages."""
    try:
        with SessionLocal() as db:
            allowlist_service = AllowlistService(db)

            # Check if user is allowed
            is_allowed = allowlist_service.is_user_allowed(
                instance_name=instance_name, channel_type=channel_type, user_identifier=user_identifier
            )

            if is_allowed:
                rprint("✅ [green]User is ALLOWED[/green]")
            else:
                rprint("❌ [red]User is BLOCKED[/red]")

            rprint(f"   Instance: [bold]{instance_name}[/bold]")
            rprint(f"   Channel: [bold]{channel_type}[/bold]")
            rprint(f"   User: [bold]{user_identifier}[/bold]")

            # Show instance allowlist status
            try:
                stats = allowlist_service.get_instance_status(instance_name)
                if not stats["allowlist_enabled"]:
                    rprint("   ℹ️  [blue]Note: Allowlist is disabled - all users are allowed[/blue]")
            except Exception:
                pass  # Ignore errors getting instance status

    except Exception as e:
        logger.error(f"Error checking user: {str(e)}")
        rprint(f"❌ [red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
