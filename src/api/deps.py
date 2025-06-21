"""
FastAPI dependency injection for database and services.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import InstanceConfig
from src.db.bootstrap import ensure_default_instance
from src.config import config

# Security scheme for API key authentication
security = HTTPBearer()


def get_database() -> Generator[Session, None, None]:
    """Database dependency."""
    yield from get_db()


def get_instance_by_name(
    instance_name: str, 
    db: Session = Depends(get_database)
) -> InstanceConfig:
    """
    Get instance configuration by name.
    
    Args:
        instance_name: Name of the instance
        db: Database session
        
    Returns:
        InstanceConfig for the instance
        
    Raises:
        HTTPException: If instance not found
    """
    instance = db.query(InstanceConfig).filter_by(name=instance_name).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance '{instance_name}' not found"
        )
    return instance


def get_default_instance(db: Session = Depends(get_database)) -> InstanceConfig:
    """
    Get the default instance configuration.
    
    Args:
        db: Database session
        
    Returns:
        Default InstanceConfig
        
    Raises:
        HTTPException: If no default instance found
    """
    # Ensure default instance exists (creates from env if needed)
    default_instance = ensure_default_instance(db)
    
    if not default_instance:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No default instance configured"
        )
    
    return default_instance


def get_instance_or_default(
    instance_name: Optional[str] = None,
    db: Session = Depends(get_database)
) -> InstanceConfig:
    """
    Get instance by name or default if no name provided.
    
    Args:
        instance_name: Optional instance name
        db: Database session
        
    Returns:
        InstanceConfig for named instance or default
    """
    if instance_name:
        return get_instance_by_name(instance_name, db)
    else:
        return get_default_instance(db)


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify API key authentication.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        str: The verified API key
        
    Raises:
        HTTPException: If API key is invalid or missing
        
    Example:
        @app.get("/protected/")
        def protected_endpoint(api_key: str = Depends(verify_api_key)):
            return {"message": "Access granted"}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not config.api.api_key:
        # If no API key is configured, allow access (development mode)
        logger.info("No API key configured, allowing access (development mode)")
        return "development"
    
    logger.debug(f"Expected API key: [{config.api.api_key}]")
    logger.debug(f"Received credentials: [{credentials.credentials}]")
    
    if credentials.credentials != config.api.api_key:
        logger.warning(f"API key mismatch. Expected: [{config.api.api_key}], Got: [{credentials.credentials}]")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("API key verified successfully")
    return credentials.credentials