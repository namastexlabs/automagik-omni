"""
Database connection and session management.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from typing import Iterator

from src.config import config

logger = logging.getLogger("src.db.engine")

# Create engine with connection pooling
engine = create_engine(
    str(config.database.uri),
    pool_size=config.database.pool_size,
    max_overflow=config.database.max_overflow,
    pool_timeout=config.database.pool_timeout,
    pool_pre_ping=True  # Verify connections before using them
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a scoped session to handle thread safety
Session = scoped_session(SessionLocal)

@contextmanager
def get_session() -> Iterator[scoped_session]:
    """
    Get a database session as a context manager.
    Usage:
        with get_session() as db:
            # Use db session
            user = db.query(User).filter(User.id == user_id).first()
    """
    db = Session()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

def init_db() -> None:
    """Initialize the database connection."""
    logger.info("Initializing database connection")

def create_tables() -> None:
    """Create all tables defined in the models."""
    logger.info("Creating database tables")
    from src.db.models import Base
    Base.metadata.create_all(bind=engine) 