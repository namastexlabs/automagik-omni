"""
Database bootstrap functionality.
Creates default instance from environment variables for backward compatibility.
"""

import logging
import os
from typing import Optional
from sqlalchemy.orm import Session
from .models import InstanceConfig
from src.config import config
from src.ip_utils import ensure_ipv4_in_config

logger = logging.getLogger(__name__)


def ensure_default_instance(db: Session) -> Optional[InstanceConfig]:
    """
    Get the default instance if one exists.

    Args:
        db: Database session

    Returns:
        The default InstanceConfig, or None if no instances exist
    """
    # Check if any instances exist
    existing_count = db.query(InstanceConfig).count()

    if existing_count == 0:
        logger.info(
            "No instances found. Use the CLI to create instances: './claude-flow instances create'"
        )
        return None

    # Return existing default instance
    default_instance = db.query(InstanceConfig).filter_by(is_default=True).first()
    if not default_instance:
        # No default instance found, make the first one default
        first_instance = db.query(InstanceConfig).first()
        if first_instance:
            first_instance.is_default = True
            db.commit()
            logger.info(f"Made instance '{first_instance.name}' the default")
            return first_instance

    return default_instance


# Function removed - instances should be created via CLI/API with explicit configuration
