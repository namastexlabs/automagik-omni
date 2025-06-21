"""
Database bootstrap functionality.
Creates default instance from environment variables for backward compatibility.
"""

import logging
from sqlalchemy.orm import Session
from .models import InstanceConfig
from src.config import config

logger = logging.getLogger(__name__)


def ensure_default_instance(db: Session) -> InstanceConfig:
    """
    Ensure a default instance exists for backward compatibility.
    
    If no instances exist in the database, create one from current environment variables
    and mark it as the default instance.
    
    Args:
        db: Database session
        
    Returns:
        The default InstanceConfig
    """
    # Check if any instances exist
    existing_count = db.query(InstanceConfig).count()
    
    if existing_count == 0:
        logger.info("No instances found, creating default instance from environment variables")
        
        # Create default instance from current config
        default_instance = InstanceConfig(
            name="default",
            channel_type="whatsapp",  # Default to WhatsApp for backward compatibility
            evolution_url="",  # Evolution URL comes from webhook payload
            evolution_key="",  # Evolution key comes from webhook payload
            whatsapp_instance=config.whatsapp.instance,
            session_id_prefix=config.whatsapp.session_id_prefix,
            agent_api_url=config.agent_api.url,
            agent_api_key=config.agent_api.api_key,
            default_agent=config.agent_api.default_agent_name,
            agent_timeout=config.agent_api.timeout,
            is_default=True
        )
        
        db.add(default_instance)
        db.commit()
        db.refresh(default_instance)
        
        logger.info(f"Created default instance: {default_instance.name}")
        return default_instance
    
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


def create_instance_from_env(db: Session, name: str, make_default: bool = False) -> InstanceConfig:
    """
    Create a new instance from current environment variables.
    
    Args:
        db: Database session
        name: Instance name
        make_default: Whether to make this the default instance
        
    Returns:
        The created InstanceConfig
    """
    # Check if instance already exists
    existing = db.query(InstanceConfig).filter_by(name=name).first()
    if existing:
        logger.warning(f"Instance '{name}' already exists")
        return existing
    
    instance = InstanceConfig(
        name=name,
        channel_type="whatsapp",  # Default to WhatsApp for backward compatibility
        evolution_url="",  # Will be set from webhook payload
        evolution_key="",  # Will be set from webhook payload
        whatsapp_instance=config.whatsapp.instance,
        session_id_prefix=config.whatsapp.session_id_prefix,
        agent_api_url=config.agent_api.url,
        agent_api_key=config.agent_api.api_key,
        default_agent=config.agent_api.default_agent_name,
        agent_timeout=config.agent_api.timeout,
        is_default=make_default
    )
    
    # If making this default, unset other defaults
    if make_default:
        db.query(InstanceConfig).filter_by(is_default=True).update({"is_default": False})
    
    db.add(instance)
    db.commit()
    db.refresh(instance)
    
    logger.info(f"Created instance '{name}' (default: {make_default})")
    return instance