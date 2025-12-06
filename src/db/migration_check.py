"""
SQLite Migration Detection and Warning System.

Detects old SQLite databases and warns users about the PostgreSQL-only migration.
Provides migration recommendations and prevents data loss.
"""

import logging
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class MigrationCheckResult(TypedDict):
    """Result of SQLite migration check."""

    sqlite_found: bool
    sqlite_path: str | None
    migration_recommended: bool
    warning_message: str | None


def check_sqlite_migration_needed() -> MigrationCheckResult:
    """
    Check if user has old SQLite database that needs migration.

    Searches for common SQLite database file locations and returns
    migration status and warning message if found.

    Returns:
        MigrationCheckResult: Detection status and migration recommendation
    """
    # Common SQLite database paths to check
    sqlite_paths = [
        Path("./data/automagik-omni.db"),
        Path("./automagik-omni.db"),
        Path("./omni.db"),
        Path("./data/omni.db"),
    ]

    for sqlite_path in sqlite_paths:
        if sqlite_path.exists():
            logger.warning(f"SQLite database found at {sqlite_path}")

            return MigrationCheckResult(
                sqlite_found=True,
                sqlite_path=str(sqlite_path),
                migration_recommended=True,
                warning_message=(
                    "⚠️  SQLite database detected! "
                    "Automagik Omni now uses PostgreSQL-only (embedded pgserve). "
                    "Your old data is NOT automatically migrated. "
                    "Please backup your SQLite database and manually migrate if needed. "
                    "See migration guide: https://github.com/namastexlabs/automagik-omni/blob/main/docs/sqlite-to-postgresql-migration.md"
                ),
            )

    # No SQLite database found
    return MigrationCheckResult(
        sqlite_found=False,
        sqlite_path=None,
        migration_recommended=False,
        warning_message=None,
    )


def log_migration_warning_on_startup() -> None:
    """
    Log migration warning on API startup if SQLite database detected.

    This function is called during application startup to warn about
    SQLite databases that may need migration.
    """
    result = check_sqlite_migration_needed()

    if result["sqlite_found"]:
        # Log prominent warning message
        logger.warning("=" * 80)
        logger.warning("SQLITE DATABASE DETECTED - MIGRATION REQUIRED")
        logger.warning("=" * 80)
        logger.warning(result["warning_message"])
        logger.warning(f"SQLite database location: {result['sqlite_path']}")
        logger.warning("=" * 80)
        logger.warning("")
        logger.warning("Next steps:")
        logger.warning("1. Backup your SQLite database: cp %s %s.backup", result["sqlite_path"], result["sqlite_path"])
        logger.warning("2. Review migration guide (link above)")
        logger.warning("3. Consider exporting data before proceeding")
        logger.warning("")
        logger.warning("PostgreSQL will be used for new data. SQLite data will NOT be imported automatically.")
        logger.warning("=" * 80)
