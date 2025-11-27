"""
Database configuration and session management.

Supports dual database architecture:
- SQLite: Global settings (bootstrap safety, always available)
- PostgreSQL: Runtime data with omni_ prefix (shared with Evolution API)
"""

import logging
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
from .init_database import initialize_database

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from configuration."""

    test_override = os.getenv("TEST_DATABASE_URL")
    if test_override:
        logger.info("Using TEST_DATABASE_URL override for database connection")
        return test_override

    from src.config import config

    return config.database.database_url


def get_global_settings_url() -> str:
    """Get SQLite URL for global settings (bootstrap database)."""
    from src.config import config
    return config.database.global_settings_url


def get_table_prefix() -> str:
    """Get table prefix for PostgreSQL tables."""
    from src.config import config
    return config.database.table_prefix if config.database.use_postgres else ""


def is_postgres() -> bool:
    """Check if using PostgreSQL for runtime data."""
    from src.config import config
    return config.database.use_postgres


def ensure_sqlite_directory(database_url: str) -> None:
    """Ensure SQLite directory exists."""
    if database_url.startswith("sqlite"):
        sqlite_path = database_url.replace("sqlite:///", "")
        sqlite_dir = Path(sqlite_path).parent
        sqlite_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SQLite database directory ensured: {sqlite_dir}")
        logger.info(f"SQLite database file: {sqlite_path}")


def _get_pool_config() -> dict:
    """Get connection pool configuration for PostgreSQL."""
    from src.config import config
    return {
        "pool_size": config.database.pool_size,
        "max_overflow": config.database.pool_max_overflow,
        "pool_recycle": config.database.pool_recycle,
        "pool_pre_ping": True,  # Verify connections before use
    }


_DATABASE_URL: str | None = None
_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None

# Global settings engine (always SQLite)
_global_settings_engine: Engine | None = None
_GlobalSettingsSession: sessionmaker | None = None

# Base class for models
Base = declarative_base()


def _initialize_engine() -> None:
    """Initialize the SQLAlchemy engine and session factory lazily."""

    global _DATABASE_URL, _engine, _SessionLocal

    if _engine is not None and _SessionLocal is not None:
        return

    database_url = get_database_url()
    _DATABASE_URL = database_url

    # Always ensure SQLite directory for global settings
    ensure_sqlite_directory(get_global_settings_url())

    # Also ensure directory for main database if SQLite
    if database_url.startswith("sqlite"):
        ensure_sqlite_directory(database_url)

    if not initialize_database(database_url):
        logger.error("Failed to initialize database. Please check your database configuration and permissions.")
        # Continue anyway - let SQLAlchemy fail with a more specific error if needed

    if database_url.startswith("sqlite"):
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},  # Needed for SQLite
        )
        logger.info("Initialized SQLite database engine")
    else:
        # PostgreSQL with connection pooling
        pool_config = _get_pool_config()
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            **pool_config
        )
        logger.info(
            f"Initialized PostgreSQL database engine with pool_size={pool_config['pool_size']}, "
            f"max_overflow={pool_config['max_overflow']}"
        )

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _initialize_global_settings_engine() -> None:
    """Initialize the global settings SQLite engine (bootstrap database)."""

    global _global_settings_engine, _GlobalSettingsSession

    if _global_settings_engine is not None and _GlobalSettingsSession is not None:
        return

    settings_url = get_global_settings_url()
    ensure_sqlite_directory(settings_url)

    _global_settings_engine = create_engine(
        settings_url,
        connect_args={"check_same_thread": False},
    )
    _GlobalSettingsSession = sessionmaker(autocommit=False, autoflush=False, bind=_global_settings_engine)
    logger.info(f"Initialized global settings SQLite engine: {settings_url}")


def get_engine() -> Engine:
    """Return the lazily initialized SQLAlchemy engine."""

    _initialize_engine()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the lazily initialized session factory."""

    _initialize_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Used by FastAPI dependency injection.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def SessionLocal(*args, **kwargs):
    """Backwards-compatible callable returning a new database session."""

    session_factory = get_session_factory()
    return session_factory(*args, **kwargs)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=get_engine())


def get_global_settings_engine() -> Engine:
    """Return the global settings SQLite engine."""
    _initialize_global_settings_engine()
    assert _global_settings_engine is not None
    return _global_settings_engine


def get_global_settings_session_factory() -> sessionmaker:
    """Return the global settings session factory."""
    _initialize_global_settings_engine()
    assert _GlobalSettingsSession is not None
    return _GlobalSettingsSession


def get_global_settings_db() -> Generator[Session, None, None]:
    """
    Dependency function to get global settings database session.
    Always uses SQLite for bootstrap safety.
    """
    _initialize_global_settings_engine()
    assert _GlobalSettingsSession is not None
    db = _GlobalSettingsSession()
    try:
        yield db
    finally:
        db.close()


def create_global_settings_tables():
    """Create global settings tables in SQLite."""
    from .models import GlobalSetting, SettingChangeHistory
    # Only create global_settings and setting_change_history tables
    GlobalSetting.__table__.create(bind=get_global_settings_engine(), checkfirst=True)
    SettingChangeHistory.__table__.create(bind=get_global_settings_engine(), checkfirst=True)
