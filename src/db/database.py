"""
Database configuration and session management.
"""

import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from configuration."""
    from src.config import config

    return config.database.database_url


def ensure_sqlite_directory(database_url: str) -> None:
    """Ensure SQLite directory exists."""
    if database_url.startswith("sqlite"):
        sqlite_path = database_url.replace("sqlite:///", "")
        sqlite_dir = Path(sqlite_path).parent
        sqlite_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SQLite database directory ensured: {sqlite_dir}")
        logger.info(f"SQLite database file: {sqlite_path}")


# Get database URL and ensure directory exists
DATABASE_URL = get_database_url()
ensure_sqlite_directory(DATABASE_URL)

# SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}  # Needed for SQLite
    )
else:
    engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Used by FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
