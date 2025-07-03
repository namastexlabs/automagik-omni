"""
CLI commands for instance management using Typer.
"""

import typer
from typing import Optional
from sqlalchemy.orm import Session
from rich.console import Console
from rich.table import Table
import time

from src.db.database import SessionLocal, create_tables
from src.db.models import InstanceConfig
from src.core.telemetry import track_command

app = typer.Typer(help="Instance management commands")
console = Console()


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


@app.command("list")
def list_instances():
    """List all instance configurations."""
    start_time = time.time()
    success = True
    
    try:
        create_tables()
        db = get_db()
        try:
            instances = db.query(InstanceConfig).all()

            if not instances:
                console.print("[yellow]No instances found[/yellow]")
                track_command("instance_list", success=True, instance_count=0, duration_ms=(time.time() - start_time) * 1000)
                return

            table = Table(title="Instance Configurations")
            table.add_column("Name", style="cyan")
            table.add_column("WhatsApp Instance", style="green")
            table.add_column("Agent API URL", style="blue")
            table.add_column("Default Agent", style="magenta")
            table.add_column("Is Default", style="red")

            for instance in instances:
                table.add_row(
                    instance.name,
                    instance.whatsapp_instance,
                    instance.agent_api_url,
                    instance.default_agent,
                    "✓" if instance.is_default else "",
                )

            console.print(table)
            track_command("instance_list", success=True, instance_count=len(instances), duration_ms=(time.time() - start_time) * 1000)
        finally:
            db.close()
    except Exception as e:
        success = False
        track_command("instance_list", success=False, duration_ms=(time.time() - start_time) * 1000)
        raise


@app.command("show")
def show_instance(name: str):
    """Show detailed configuration for a specific instance."""
    create_tables()
    db = get_db()
    try:
        instance = db.query(InstanceConfig).filter_by(name=name).first()

        if not instance:
            console.print(f"[red]Instance '{name}' not found[/red]")
            raise typer.Exit(1)

        console.print(f"\n[bold]Instance Configuration: {instance.name}[/bold]")
        console.print(f"ID: {instance.id}")
        console.print(
            f"Evolution URL: {instance.evolution_url or '[dim]Not set[/dim]'}"
        )
        console.print(
            f"Evolution Key: {'*' * len(instance.evolution_key) if instance.evolution_key else '[dim]Not set[/dim]'}"
        )
        console.print(f"WhatsApp Instance: {instance.whatsapp_instance}")
        console.print(
            f"Session ID Prefix: {instance.session_id_prefix or '[dim]None[/dim]'}"
        )
        console.print(f"Agent API URL: {instance.agent_api_url}")
        console.print(
            f"Agent API Key: {'*' * len(instance.agent_api_key) if instance.agent_api_key else '[dim]Not set[/dim]'}"
        )
        console.print(f"Default Agent: {instance.default_agent}")
        console.print(f"Agent Timeout: {instance.agent_timeout}s")
        console.print(f"Is Default: {instance.is_default}")
        console.print(f"Created: {instance.created_at}")
        console.print(f"Updated: {instance.updated_at}")
    finally:
        db.close()


@app.command("add")
def add_instance(
    name: str = typer.Argument(..., help="Instance name"),
    evolution_url: str = typer.Option("", help="Evolution API URL"),
    evolution_key: str = typer.Option("", help="Evolution API key"),
    whatsapp_instance: str = typer.Option(..., help="WhatsApp instance name"),
    session_id_prefix: Optional[str] = typer.Option(None, help="Session ID prefix"),
    agent_api_url: str = typer.Option(..., help="Agent API URL"),
    agent_api_key: str = typer.Option(..., help="Agent API key"),
    default_agent: str = typer.Option(..., help="Default agent name"),
    agent_timeout: int = typer.Option(60, help="Agent API timeout in seconds"),
    make_default: bool = typer.Option(
        False, "--default", help="Make this the default instance"
    ),
):
    """Add a new instance configuration."""
    start_time = time.time()
    
    try:
        create_tables()
        db = get_db()
        try:
            # Check if instance already exists
            existing = db.query(InstanceConfig).filter_by(name=name).first()
            if existing:
                console.print(f"[red]Instance '{name}' already exists[/red]")
                track_command("instance_add", success=False, error="instance_exists", duration_ms=(time.time() - start_time) * 1000)
                raise typer.Exit(1)

            # If making this default, unset other defaults
            if make_default:
                db.query(InstanceConfig).filter_by(is_default=True).update(
                    {"is_default": False}
                )

            # Create new instance
            instance = InstanceConfig(
                name=name,
                evolution_url=evolution_url,
                evolution_key=evolution_key,
                whatsapp_instance=whatsapp_instance,
                session_id_prefix=session_id_prefix,
                agent_api_url=agent_api_url,
                agent_api_key=agent_api_key,
                default_agent=default_agent,
                agent_timeout=agent_timeout,
                is_default=make_default,
            )

            db.add(instance)
            db.commit()

            console.print(f"[green]Instance '{name}' created successfully[/green]")
            if make_default:
                console.print(f"[green]Instance '{name}' set as default[/green]")
            
            track_command("instance_add", success=True, is_default=make_default, duration_ms=(time.time() - start_time) * 1000)
        finally:
            db.close()
    except typer.Exit:
        raise
    except Exception as e:
        track_command("instance_add", success=False, error=str(e), duration_ms=(time.time() - start_time) * 1000)
        raise


@app.command("update")
def update_instance(
    name: str = typer.Argument(..., help="Instance name"),
    evolution_url: Optional[str] = typer.Option(None, help="Evolution API URL"),
    evolution_key: Optional[str] = typer.Option(None, help="Evolution API key"),
    whatsapp_instance: Optional[str] = typer.Option(
        None, help="WhatsApp instance name"
    ),
    session_id_prefix: Optional[str] = typer.Option(None, help="Session ID prefix"),
    agent_api_url: Optional[str] = typer.Option(None, help="Agent API URL"),
    agent_api_key: Optional[str] = typer.Option(None, help="Agent API key"),
    default_agent: Optional[str] = typer.Option(None, help="Default agent name"),
    agent_timeout: Optional[int] = typer.Option(
        None, help="Agent API timeout in seconds"
    ),
    make_default: bool = typer.Option(
        False, "--default", help="Make this the default instance"
    ),
):
    """Update an existing instance configuration."""
    create_tables()
    db = get_db()
    try:
        # Get existing instance
        instance = db.query(InstanceConfig).filter_by(name=name).first()
        if not instance:
            console.print(f"[red]Instance '{name}' not found[/red]")
            raise typer.Exit(1)

        # Update fields if provided
        if evolution_url is not None:
            instance.evolution_url = evolution_url
        if evolution_key is not None:
            instance.evolution_key = evolution_key
        if whatsapp_instance is not None:
            instance.whatsapp_instance = whatsapp_instance
        if session_id_prefix is not None:
            instance.session_id_prefix = session_id_prefix
        if agent_api_url is not None:
            instance.agent_api_url = agent_api_url
        if agent_api_key is not None:
            instance.agent_api_key = agent_api_key
        if default_agent is not None:
            instance.default_agent = default_agent
        if agent_timeout is not None:
            instance.agent_timeout = agent_timeout

        # Handle default flag
        if make_default:
            db.query(InstanceConfig).filter_by(is_default=True).update(
                {"is_default": False}
            )
            instance.is_default = True

        db.commit()

        console.print(f"[green]Instance '{name}' updated successfully[/green]")
        if make_default:
            console.print(f"[green]Instance '{name}' set as default[/green]")
    finally:
        db.close()


@app.command("delete")
def delete_instance(
    name: str = typer.Argument(..., help="Instance name"),
    force: bool = typer.Option(
        False, "--force", help="Force deletion without confirmation"
    ),
):
    """Delete an instance configuration."""
    create_tables()
    db = get_db()
    try:
        # Get existing instance
        instance = db.query(InstanceConfig).filter_by(name=name).first()
        if not instance:
            console.print(f"[red]Instance '{name}' not found[/red]")
            raise typer.Exit(1)

        # Check if it's the only instance
        instance_count = db.query(InstanceConfig).count()
        if instance_count == 1:
            console.print("[red]Cannot delete the only remaining instance[/red]")
            raise typer.Exit(1)

        # Confirm deletion unless forced
        if not force:
            is_default_text = " (DEFAULT)" if instance.is_default else ""
            confirm = typer.confirm(f"Delete instance '{name}'{is_default_text}?")
            if not confirm:
                console.print("Deletion cancelled")
                raise typer.Exit(0)

        db.delete(instance)
        db.commit()

        console.print(f"[green]Instance '{name}' deleted successfully[/green]")
    finally:
        db.close()


@app.command("set-default")
def set_default_instance(name: str = typer.Argument(..., help="Instance name")):
    """Set an instance as the default."""
    create_tables()
    db = get_db()
    try:
        # Get the instance
        instance = db.query(InstanceConfig).filter_by(name=name).first()
        if not instance:
            console.print(f"[red]Instance '{name}' not found[/red]")
            raise typer.Exit(1)

        # Unset other defaults
        db.query(InstanceConfig).filter_by(is_default=True).update(
            {"is_default": False}
        )

        # Set this as default
        instance.is_default = True
        db.commit()

        console.print(f"[green]Instance '{name}' set as default[/green]")
    finally:
        db.close()


# Bootstrap command removed - instances should be created with explicit configuration using 'create' command


if __name__ == "__main__":
    app()
