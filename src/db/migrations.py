"""
Database migration utilities using Alembic.
"""

import logging
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
            return context.get_current_revision()
    except Exception as e:
        logger.error(f"Error getting current revision: {e}")
        return None


def get_head_revision() -> str | None:
    """Get the head revision from migration scripts."""
    try:
        config = get_alembic_config()
        script_dir = ScriptDirectory.from_config(config)
        return script_dir.get_current_head()
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
    
    Returns:
        bool: True if migrations ran successfully, False otherwise
    """
    try:
        config = get_alembic_config()
        
        # Check if database exists
        if not check_database_exists():
            logger.info("Database is empty, running initial migration...")
        else:
            current = get_current_revision()
            head = get_head_revision()
            
            if current == head:
                logger.info("Database is up to date, no migrations needed")
                return True
            
            logger.info(f"Migrating database from {current} to {head}")
        
        # Run migrations
        command.upgrade(config, "head")
        logger.info("Database migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False


def stamp_database(revision: str = "head") -> bool:
    """
    Stamp the database with a specific revision without running migrations.
    
    Args:
        revision: The revision to stamp (default: "head")
        
    Returns:
        bool: True if stamping was successful, False otherwise
    """
    try:
        config = get_alembic_config()
        command.stamp(config, revision)
        logger.info(f"Database stamped with revision: {revision}")
        return True
        
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
            return stamp_database(head_revision)
        
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