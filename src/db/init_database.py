"""
Database initialization with automatic PostgreSQL database creation.
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def create_postgres_database_if_needed(database_url: str) -> bool:
    """
    Attempt to create PostgreSQL database if it doesn't exist.
    Returns True if database exists or was created, False otherwise.
    """
    if not database_url.startswith("postgresql://"):
        return True  # Not PostgreSQL, no need to create

    # Parse the database URL
    parsed = urlparse(database_url)
    database_name = parsed.path.lstrip("/")

    # Create connection URL to postgres database (default maintenance database)
    postgres_url_parts = (
        parsed.scheme,
        parsed.netloc,
        "/postgres",  # Connect to default postgres database
        parsed.params,
        parsed.query,
        parsed.fragment,
    )
    postgres_url = urlunparse(postgres_url_parts)

    try:
        # Try to connect to the target database first
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Database '{database_name}' already exists")
        engine.dispose()
        return True
    except OperationalError:
        # Database doesn't exist, try to create it
        logger.info(f"Database '{database_name}' does not exist, attempting to create...")

        try:
            # Connect to postgres database to create the target database
            engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
            with engine.connect() as conn:
                # Check if database exists
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": database_name},
                )
                if result.fetchone() is None:
                    # Create database
                    conn.execute(text(f'CREATE DATABASE "{database_name}"'))
                    logger.info(f"Successfully created database '{database_name}'")
                else:
                    logger.info(f"Database '{database_name}' already exists")
            engine.dispose()
            return True
        except (OperationalError, ProgrammingError) as e:
            logger.warning(
                f"Could not create database '{database_name}'. "
                f"This might be due to insufficient permissions. "
                f"Please create the database manually or ensure the user has CREATEDB permission. "
                f"Error: {str(e)}"
            )
            return False
    except Exception as e:
        logger.error(f"Unexpected error checking/creating database: {str(e)}")
        return False


def initialize_database(database_url: str) -> bool:
    """
    Initialize database, creating it if necessary for PostgreSQL.
    Returns True if successful, False otherwise.
    """
    # For SQLite, no need to create database
    if database_url.startswith("sqlite"):
        return True

    # For PostgreSQL, attempt to create if needed
    if database_url.startswith("postgresql://"):
        return create_postgres_database_if_needed(database_url)

    # Unknown database type
    logger.warning(f"Unknown database type in URL: {database_url}")
    return True  # Assume it's OK and let SQLAlchemy handle it
