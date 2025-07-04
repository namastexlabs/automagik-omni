"""
CLI commands for telemetry management in Automagik Omni.
"""

import typer
from rich.console import Console

from src.core.telemetry import telemetry_client

app = typer.Typer(help="Manage telemetry settings")
console = Console()


@app.command("enable")
def enable_telemetry():
    """Enable telemetry data collection."""
    telemetry_client.enable()
    console.print("✅ Telemetry enabled", style="green")


@app.command("disable")
def disable_telemetry():
    """Disable telemetry data collection permanently."""
    telemetry_client.disable()
    console.print("❌ Telemetry disabled", style="red")


if __name__ == "__main__":
    app()