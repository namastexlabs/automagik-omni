"""
Factory reset CLI commands for Automagik Omni.
"""

import typer
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from src.core.telemetry import track_command

app = typer.Typer(help="Reset and maintenance commands")
console = Console()


@app.command("factory")
def factory_reset(
    keep_instances: bool = typer.Option(
        False, "--keep-instances", help="Preserve Evolution API instances"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip all confirmation prompts"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview what would be deleted without executing"
    ),
):
    """
    Factory reset Automagik Omni to fresh install state.

    This will delete:
    - PostgreSQL tables (omni_* and evo_* - API keys regenerate on next start)
    - Evolution API instances (unless --keep-instances)
    - Log files

    PostgreSQL only - SQLite is NOT supported.

    Examples:
        omni reset factory              # Interactive reset
        omni reset factory --dry-run    # Preview only
        omni reset factory --force      # No prompts (for CI/CD)
    """
    from src.db.database import SessionLocal
    from src.services.reset_service import reset_service, FactoryResetResult

    try:
        with SessionLocal() as db:
            # Get preview
            preview = reset_service.get_preview(db)

            # Display current state
            console.print()
            console.print(Panel.fit(
                "[bold]Factory Reset - Automagik Omni[/bold]",
                border_style="red"
            ))
            console.print()

            # Current state table
            state_table = Table(title="Current State", show_header=False)
            state_table.add_column("Item", style="cyan")
            state_table.add_column("Value", style="white")

            state_table.add_row("PostgreSQL", f"{len(preview.postgres_tables)} tables (omni_*, evo_*)")
            state_table.add_row("Instances", f"{preview.instance_count} ({', '.join(preview.instances[:3])}{'...' if len(preview.instances) > 3 else ''})")
            state_table.add_row("Users", str(preview.user_count))
            state_table.add_row("Message Traces", str(preview.trace_count))
            state_table.add_row("Access Rules", str(preview.access_rule_count))
            state_table.add_row("Settings", str(preview.setting_count))
            state_table.add_row("Logs", f"{preview.log_path} ({preview.log_size_mb} MB)")

            console.print(state_table)
            console.print()

            # What will be deleted
            console.print("[bold]This will:[/bold]")
            console.print(f"  [green]✓[/green] Clear PostgreSQL tables ({len(preview.postgres_tables)} tables)")
            if not keep_instances and preview.instance_count > 0:
                console.print(f"  [green]✓[/green] Delete {preview.instance_count} Evolution API instance(s)")
            elif keep_instances:
                console.print("  [yellow]○[/yellow] Keep Evolution API instances (--keep-instances)")
            console.print("  [green]✓[/green] Delete log files")
            console.print()

            # Default to clearing PostgreSQL tables (primary database)
            clear_postgres = True

            if dry_run:
                console.print()
                console.print("[yellow]DRY RUN - No changes made[/yellow]")
                console.print()
                track_command("factory_reset", success=True, dry_run=True)
                return

            # Final confirmation
            if not force:
                console.print()
                if not Confirm.ask("[red]Proceed with reset?[/red]", default=False):
                    console.print("[yellow]Reset cancelled[/yellow]")
                    raise typer.Abort()

            # Execute reset
            console.print()
            console.print("[bold]Resetting...[/bold]")

            # Run async reset
            results: FactoryResetResult = asyncio.run(
                reset_service.factory_reset(
                    db=db,
                    keep_instances=keep_instances,
                    clear_postgres=clear_postgres,
                )
            )

            # Display results
            if results["evolution_instances"]:
                deleted = sum(1 for v in results["evolution_instances"].values() if v == "deleted")
                console.print(f"  [green]✓[/green] Deleted {deleted} Evolution instance(s)")

            if results["postgres_tables"]:
                console.print(f"  [green]✓[/green] Cleared {len(results['postgres_tables'])} PostgreSQL table(s)")

            if results["logs_deleted"]:
                console.print(f"  [green]✓[/green] Deleted {results['logs_deleted']} log file(s)")

            console.print()
            console.print(Panel.fit(
                "[green bold]Factory reset complete![/green bold]\n\n"
                "API keys will regenerate on next start.\n"
                "Run: [cyan]omni start[/cyan]",
                border_style="green"
            ))

            track_command(
                "factory_reset",
                success=True,
                keep_instances=keep_instances,
                clear_postgres=clear_postgres,
                instances_deleted=len(results["evolution_instances"]),
            )

    except typer.Abort:
        track_command("factory_reset", success=False, reason="cancelled")
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        track_command("factory_reset", success=False, error=str(e))
        raise typer.Exit(1)
