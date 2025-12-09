"""
Database configuration and session management.
"""

import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
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


# SQLite support removed - PostgreSQL only (embedded via pgserve)


_DATABASE_URL: str | None = None
_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None

# Base class for models
Base = declarative_base()


def _initialize_engine() -> None:
    """Initialize the SQLAlchemy engine and session factory lazily (PostgreSQL only)."""

    global _DATABASE_URL, _engine, _SessionLocal

    if _engine is not None and _SessionLocal is not None:
        return

    database_url = get_database_url()
    _DATABASE_URL = database_url

    if not initialize_database(database_url):
        logger.error("Failed to initialize database. Please check your database configuration and permissions.")
        # Continue anyway - let SQLAlchemy fail with a more specific error if needed

    # PostgreSQL only - use connection pooling
    from src.config import config
    _engine = create_engine(
        database_url,
        pool_size=config.database.pool_size,
        max_overflow=config.database.pool_max_overflow,
        pool_pre_ping=True,
        pool_recycle=config.database.pool_recycle,
    )

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


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
