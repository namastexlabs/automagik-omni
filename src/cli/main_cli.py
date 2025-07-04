"""
Main CLI application for Omni-Hub with telemetry support.
"""

import typer
from typing import Optional
import time
import os

from src.core.telemetry import track_command, disable_telemetry, telemetry_client
from src.cli.instance_cli import app as instance_app
from src.cli.telemetry_cli import app as telemetry_app

# Create main app
app = typer.Typer(help="Automagik Omni: Multi-tenant omnichannel messaging hub")

# Add sub-commands
app.add_typer(instance_app, name="instance", help="Instance management commands")
app.add_typer(telemetry_app, name="telemetry", help="Telemetry management commands")


@app.callback()
def main(
    no_telemetry: bool = typer.Option(
        False, "--no-telemetry", help="Disable telemetry for this session"
    ),
    version: bool = typer.Option(
        False, "--version", help="Show version information"
    ),
):
    """
    Automagik Omni: Multi-tenant omnichannel messaging hub
    
    A platform for managing multiple messaging channels with per-instance configuration.
    """
    if no_telemetry:
        # Temporarily disable telemetry for this session
        telemetry_client.enabled = False
    
    if version:
        typer.echo(f"Automagik Omni version {telemetry_client.project_version}")
        raise typer.Exit()


@app.command("start")
def start_api(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8882, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
):
    """Start the Automagik Omni API server."""
    start_time = time.time()
    
    try:
        # Track API start command
        track_command("api_start", success=True, host=host, port=port, reload=reload)
        
        # Start the API server
        import uvicorn
        uvicorn.run(
            "src.api.app:app",
            host=host,
            port=port,
            reload=reload,
        )
        
    except Exception as e:
        track_command("api_start", success=False, error=str(e), duration_ms=(time.time() - start_time) * 1000)
        raise


@app.command("health")
def health_check():
    """Check the health of the Automagik Omni system."""
    start_time = time.time()
    
    try:
        from src.db.database import SessionLocal, engine
        from src.config import config
        
        # Check database connection
        try:
            with SessionLocal() as db:
                db.execute("SELECT 1")
            db_status = "✅ Connected"
        except Exception as e:
            db_status = f"❌ Error: {e}"
        
        # Check configuration
        config_status = "✅ Valid" if config.is_valid else "❌ Invalid"
        
        # Display results
        typer.echo(f"Database: {db_status}")
        typer.echo(f"Configuration: {config_status}")
        typer.echo(f"Telemetry: {'✅ Enabled' if telemetry_client.is_enabled() else '❌ Disabled'}")
        
        success = "Error" not in db_status and "Invalid" not in config_status
        track_command("health_check", success=success, duration_ms=(time.time() - start_time) * 1000)
        
    except Exception as e:
        track_command("health_check", success=False, error=str(e), duration_ms=(time.time() - start_time) * 1000)
        raise


@app.command("init")
def init_project():
    """Initialize a new Automagik Omni project."""
    start_time = time.time()
    
    try:
        from src.db.database import create_tables
        
        typer.echo("🚀 Initializing Automagik Omni project...")
        
        # Create database tables
        create_tables()
        typer.echo("✅ Database tables created")
        
        # Check if this is first run
        from src.db.database import SessionLocal
        from src.db.models import InstanceConfig
        
        with SessionLocal() as db:
            instance_count = db.query(InstanceConfig).count()
            
        if instance_count == 0:
            typer.echo("📋 No instances found. Create your first instance with:")
            typer.echo("   automagik-omni instance add <name> [options]")
            
            # Track first run
            track_command("init_project", success=True, first_run=True, duration_ms=(time.time() - start_time) * 1000)
            telemetry_client.track_installation("manual", first_run=True)
        else:
            typer.echo(f"📊 Found {instance_count} existing instances")
            track_command("init_project", success=True, first_run=False, duration_ms=(time.time() - start_time) * 1000)
        
        typer.echo("✅ Automagik Omni project initialized successfully!")
        
    except Exception as e:
        track_command("init_project", success=False, error=str(e), duration_ms=(time.time() - start_time) * 1000)
        raise


@app.command("status")
def show_status():
    """Show overall system status."""
    start_time = time.time()
    
    try:
        from src.db.database import SessionLocal
        from src.db.models import InstanceConfig
        from src.config import config
        
        typer.echo("📊 Automagik Omni Status")
        typer.echo("=" * 50)
        
        # Configuration status
        typer.echo(f"Configuration: {'✅ Valid' if config.is_valid else '❌ Invalid'}")
        typer.echo(f"API Host: {config.api.host}")
        typer.echo(f"API Port: {config.api.port}")
        typer.echo(f"Database: {config.database.database_url}")
        typer.echo(f"Telemetry: {'✅ Enabled' if telemetry_client.is_enabled() else '❌ Disabled'}")
        
        # Instance status
        with SessionLocal() as db:
            instances = db.query(InstanceConfig).all()
            
        typer.echo(f"\n📱 Instances: {len(instances)}")
        for instance in instances:
            status = "🌟 DEFAULT" if instance.is_default else "📱"
            typer.echo(f"  {status} {instance.name} ({instance.whatsapp_instance})")
        
        track_command("show_status", success=True, instance_count=len(instances), duration_ms=(time.time() - start_time) * 1000)
        
    except Exception as e:
        track_command("show_status", success=False, error=str(e), duration_ms=(time.time() - start_time) * 1000)
        raise


if __name__ == "__main__":
    app()