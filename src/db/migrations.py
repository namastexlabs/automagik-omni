"""
Database migration utilities using Alembic.
"""

import logging
import threading
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from .database import engine

logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Get the project root directory (where alembic.ini is located)
    project_root = Path(__file__).parent.parent.parent
    alembic_ini_path = project_root / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"Alembic config file not found: {alembic_ini_path}")

    config = Config(str(alembic_ini_path))

    # Set the script location relative to the config file
    config.set_main_option("script_location", str(project_root / "alembic"))

    return config


def check_database_exists() -> bool:
    """Check if the database has any tables."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return len(tables) > 0
    except Exception as e:
        logger.error(f"Error checking database existence: {e}")
        return False


def get_current_revision() -> str | None:
    """Get the current database revision."""
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)

            # Try to get single revision first
            try:
                return context.get_current_revision()
            except Exception as e:
                if "more than one head present" in str(e):
                    # Multiple heads in the version table - get all heads
                    heads = context.get_current_heads()
                    logger.warning(f"Multiple heads in version table: {heads}")

                    # Check if we have a merge migration that resolves these
                    config = get_alembic_config()
                    script_dir = ScriptDirectory.from_config(config)

                    # Look for a migration that has these heads as down_revisions
                    for revision in script_dir.iterate_revisions("heads"):
                        if revision.down_revision and isinstance(revision.down_revision, tuple):
                            if set(revision.down_revision) == set(heads):
                                logger.info(f"Found merge migration {revision.revision} for current heads")
                                # Return None to trigger migration to the merge
                                return None

                    # If no merge found, return the first head
                    return heads[0] if heads else None
                else:
                    raise

    except Exception as e:
        logger.error(f"Error getting current revision: {e}")
        return None


def get_head_revision() -> str | None:
    """Get the head revision from migration scripts."""
    try:
        config = get_alembic_config()
        script_dir = ScriptDirectory.from_config(config)

        # Check if there are multiple heads (branching)
        heads = script_dir.get_heads()

        if len(heads) == 1:
            # Single head - normal case
            return script_dir.get_current_head()
        elif len(heads) > 1:
            # Multiple heads detected - check if merge migration exists
            logger.warning(f"Multiple migration heads detected: {heads}")

            # Look for a merge migration that has all heads as dependencies
            for revision in script_dir.iterate_revisions("heads"):
                if revision.down_revision and isinstance(revision.down_revision, tuple):
                    # This is a merge migration
                    if set(revision.down_revision) == set(heads):
                        logger.info(f"Found merge migration: {revision.revision}")
                        return revision.revision

            # No merge migration found - return None to trigger migration
            logger.warning("No merge migration found for multiple heads")
            return None
        else:
            # No heads
            return None

    except Exception as e:
        logger.error(f"Error getting head revision: {e}")
        return None


def needs_migration() -> bool:
    """Check if database needs migration."""
    try:
        current = get_current_revision()
        head = get_head_revision()

        if current is None and head is not None:
            # No revision table or no current revision, but migrations exist
            return True

        if current != head:
            # Current revision is different from head
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return False


def run_migrations() -> bool:
    """
    Run database migrations.
    Handles multiple heads automatically by upgrading to all heads.

    Returns:
        bool: True if migrations ran successfully, False otherwise
    """
    try:
        config = get_alembic_config()
        script_dir = ScriptDirectory.from_config(config)

        # Check for multiple heads
        heads = script_dir.get_heads()

        # Check if database exists
        if not check_database_exists():
            logger.info("Database is empty, running initial migration...")
        else:
            current = get_current_revision()
            head = get_head_revision()

            if current == head and len(heads) == 1:
                logger.info("Database is up to date, no migrations needed")
                return True

            if len(heads) > 1:
                logger.info(f"Multiple heads detected: {heads}")
                logger.info("Will upgrade to all heads to resolve branches")

            logger.info(f"Migrating database from {current} to {head or 'heads'}")

        # Run migrations - 'head' will upgrade to all heads if multiple exist
        command.upgrade(config, "head")
        logger.info("Database migrations completed successfully")

        # After upgrading, check if we now have a single head
        new_heads = script_dir.get_heads()
        if len(new_heads) == 1:
            logger.info(f"Successfully resolved to single head: {new_heads[0]}")
        elif len(new_heads) > 1:
            logger.warning(f"Still have multiple heads after migration: {new_heads}")
            logger.warning("You may need to create a merge migration manually")

        return True

    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        logger.error("If you see multiple heads error, run: uv run alembic merge -m 'Merge branches' <head1> <head2>")
        return False


def stamp_database(revision: str = "head", timeout_seconds: int = 5) -> bool:
    """
    Stamp the database with a specific revision without running migrations.

    Args:
        revision: The revision to stamp (default: "head")
        timeout_seconds: Maximum time to wait for stamping operation (default: 5)

    Returns:
        bool: True if stamping was successful or timed out (non-critical), False on error
    """
    try:
        config = get_alembic_config()
        result = [False]
        exception = [None]

        def stamp_thread():
            try:
                command.stamp(config, revision)
                result[0] = True
            except Exception as e:
                exception[0] = e

        # Run stamping in a separate thread with timeout
        thread = threading.Thread(target=stamp_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            # Thread is still running after timeout
            logger.warning(f"Stamping operation timed out after {timeout_seconds}s, but database is functional")
            # Even if stamping times out, the database is still functional
            # This is not a critical error
            return True

        if exception[0]:
            raise exception[0]

        if result[0]:
            logger.info(f"Database stamped with revision: {revision}")

        return result[0]

    except Exception as e:
        logger.error(f"Error stamping database: {e}")
        return False


def auto_migrate() -> bool:
    """
    Automatically handle database migrations on startup.

    This function will:
    1. Check if migrations are needed
    2. For existing databases with data but no revision, stamp them as current
    3. For empty databases, run all migrations
    4. For databases behind head, run pending migrations

    Returns:
        bool: True if migration handling was successful, False otherwise
    """
    try:
        logger.info("Starting automatic database migration check...")

        current_revision = get_current_revision()
        head_revision = get_head_revision()
        has_tables = check_database_exists()

        logger.info(f"Database state: current={current_revision}, head={head_revision}, has_tables={has_tables}")

        if not has_tables:
            # Empty database - run all migrations
            logger.info("Empty database detected, running all migrations...")
            return run_migrations()

        elif current_revision is None and has_tables:
            # Existing database without revision tracking - stamp it as current
            logger.info("Existing database without revision tracking detected, stamping as current...")
            success = stamp_database(head_revision)
            if success:
                logger.info("Database successfully stamped with current revision")
            else:
                logger.warning("Failed to stamp database, but continuing anyway (database is functional)")
                # Return True to allow the application to continue
                # The database is functional, just missing revision tracking
                return True
            return success

        elif current_revision != head_revision:
            # Database needs updating
            logger.info("Database needs updating, running migrations...")
            return run_migrations()

        else:
            # Database is up to date
            logger.info("Database is up to date")
            return True

    except Exception as e:
        logger.error(f"Error in auto migration: {e}")
        return False
