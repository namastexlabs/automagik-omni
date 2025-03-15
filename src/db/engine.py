"""
Database connection and session management placeholder.
No actual database functionality remains in this file.
"""

import logging
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("src.db.engine")

@contextmanager
def get_session() -> Iterator:
    """
    Placeholder for database session.
    This function is kept as a placeholder but will raise an error if used.
    """
    raise NotImplementedError("Database functionality has been removed")

def init_db() -> None:
    """Initialize the database connection (placeholder)."""
    logger.info("Database functionality has been removed")

def create_tables() -> None:
    """Create all tables defined in the models (placeholder)."""
    logger.info("Database functionality has been removed") 