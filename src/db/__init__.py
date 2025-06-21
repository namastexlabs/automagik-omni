"""
Database module for multi-tenant instance configuration.
"""

from .database import engine, SessionLocal, get_db, Base
from .models import InstanceConfig
from .bootstrap import ensure_default_instance

__all__ = [
    "engine",
    "SessionLocal", 
    "get_db",
    "Base",
    "InstanceConfig",
    "ensure_default_instance"
]