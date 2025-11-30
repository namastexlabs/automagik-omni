"""
API key management CLI commands for Automagik Omni.
"""

import typer
import secrets
import json
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from src.core.telemetry import track_command

app = typer.Typer(help="API key management commands")
console = Console()


def mask_key(key: str) -> str:
    """Mask API key showing only first 8 and last 4 characters."""
    if len(key) <= 12:
        return "*" * len(key)
    return f"{key[:8]}{'*' * (len(key) - 12)}{key[-4:]}"


@app.command("show")
def show_key(
    no_mask: bool = typer.Option(
        False, "--no-mask", help="Show full API key (unmasked)"
    ),
    regenerate: bool = typer.Option(
        False, "--regenerate", help="Generate a new API key"
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json, env"
    ),
):
    """
    Show or regenerate the API key.

    Requires console/localhost access for security.

    Examples:
        omni key show                 # Show masked key
        omni key show --no-mask       # Show full key
        omni key show --regenerate    # Generate new key
        omni key show --format env    # Output as environment variable
    """
    from src.db.database import SessionLocal
    from src.services.settings_service import settings_service
    from src.db.models import SettingValueType

    try:
        with SessionLocal() as db:
            # Handle regeneration
            if regenerate:
                console.print()
                console.print(Panel.fit(
                    "[bold yellow]API Key Regeneration[/bold yellow]",
                    border_style="yellow"
                ))
                console.print()
                console.print("[yellow]Warning:[/yellow] This will invalidate your current API key.")
                console.print("All existing browser sessions will be logged out.")
                console.print()

                if not Confirm.ask("Generate new key?", default=False):
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Abort()

                # Generate new key
                new_key = f"sk-omni-{secrets.token_urlsafe(32)}"

                # Update in database
                existing = settings_service.get_setting("omni_api_key", db)
                if existing:
                    settings_service.update_setting("omni_api_key", new_key, db)
                else:
                    settings_service.create_setting(
                        key="omni_api_key",
                        value=new_key,
                        value_type=SettingValueType.SECRET,
                        category="security",
                        description="Omni API authentication key (regenerated)",
                        is_secret=True,
                        is_required=True,
                        db=db,
                        created_by="cli_regenerate"
                    )

                console.print()
                console.print("[green]New API key generated:[/green]")
                console.print()
                console.print(Panel.fit(
                    f"[bold green]{new_key}[/bold green]",
                    border_style="green"
                ))
                console.print()
                console.print("[yellow]Old key is now invalid.[/yellow]")
                console.print()
                console.print("Next steps:")
                console.print("  1. Update browser localStorage (clear and re-login)")
                console.print("  2. Update .env file if you have one")
                console.print("  3. Update any external integrations")

                track_command("key_regenerate", success=True)
                return

            # Get current key
            setting = settings_service.get_setting("omni_api_key", db)

            if not setting or not setting.value:
                console.print("[red]No API key found.[/red]")
                console.print("Run [cyan]omni start[/cyan] to auto-generate one.")
                track_command("key_show", success=False, reason="not_found")
                raise typer.Exit(1)

            api_key = setting.value

            # Output based on format
            if format == "json":
                output = {"api_key": api_key if no_mask else mask_key(api_key)}
                console.print(json.dumps(output))

            elif format == "env":
                key_value = api_key if no_mask else mask_key(api_key)
                console.print(f'AUTOMAGIK_OMNI_API_KEY="{key_value}"')

            else:  # text format
                console.print()
                console.print(Panel.fit(
                    "[bold]API Key Recovery[/bold]",
                    border_style="blue"
                ))
                console.print()

                if no_mask:
                    console.print("Your API key [yellow](KEEP SECRET)[/yellow]:")
                    console.print()
                    console.print(Panel.fit(
                        f"[bold green]{api_key}[/bold green]",
                        border_style="green"
                    ))
                else:
                    console.print("Your current API key:")
                    console.print()
                    console.print(Panel.fit(
                        f"[bold]{mask_key(api_key)}[/bold]",
                        border_style="blue"
                    ))
                    console.print()
                    console.print("To see full key: [cyan]omni key show --no-mask[/cyan]")

                console.print()

            track_command("key_show", success=True, masked=not no_mask, format=format)

    except typer.Abort:
        raise
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        track_command("key_show", success=False, error=str(e))
        raise typer.Exit(1)
