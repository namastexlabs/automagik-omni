"""
Version utilities for automagik-omni.

This module provides a centralized way to access the package version
from pyproject.toml using importlib.metadata.
"""

import importlib.metadata
from typing import Optional


def get_version() -> str:
    """
    Get the package version from pyproject.toml.
    
    Returns:
        str: The version string (e.g., "0.3.0")
        
    Raises:
        PackageNotFoundError: If the package is not installed
    """
    try:
        return importlib.metadata.version("automagik-omni")
    except importlib.metadata.PackageNotFoundError:
        # Fallback to a default version if package is not installed
        return "0.3.0-dev"


def get_version_safe() -> str:
    """
    Get the package version with safe fallback.
    
    Returns:
        str: The version string, with fallback to development version
    """
    try:
        return get_version()
    except Exception:
        return "0.3.0-dev"


# For backward compatibility
__version__ = get_version_safe()