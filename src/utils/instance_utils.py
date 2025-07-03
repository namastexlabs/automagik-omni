"""
Utility functions for instance management.
"""

import re
import logging

logger = logging.getLogger(__name__)


def normalize_instance_name(name: str) -> str:
    """
    Normalize an instance name to be safe for URLs and Evolution API.

    Rules:
    - Replace spaces with hyphens
    - Convert to lowercase
    - Remove special characters except hyphens and underscores
    - Ensure it starts and ends with alphanumeric characters
    - Limit length to 50 characters

    Args:
        name: Original instance name

    Returns:
        str: Normalized instance name safe for URLs and APIs
    """
    if not name:
        return "default-instance"

    # Convert to lowercase and replace spaces with hyphens
    normalized = name.lower().strip()
    normalized = re.sub(r"\s+", "-", normalized)

    # Remove special characters except hyphens, underscores, and alphanumeric
    normalized = re.sub(r"[^a-z0-9\-_]", "", normalized)

    # Remove consecutive hyphens/underscores
    normalized = re.sub(r"[-_]+", "-", normalized)

    # Ensure it starts and ends with alphanumeric characters
    normalized = re.sub(r"^[-_]+|[-_]+$", "", normalized)

    # Ensure minimum length
    if len(normalized) < 2:
        normalized = f"instance-{normalized}" if normalized else "instance"

    # Limit length
    if len(normalized) > 50:
        normalized = normalized[:50]
        # Ensure it doesn't end with a hyphen after truncation
        normalized = re.sub(r"-+$", "", normalized)

    logger.debug(f"Normalized instance name: '{name}' -> '{normalized}'")
    return normalized


def validate_instance_name(name: str) -> tuple[bool, str]:
    """
    Validate an instance name for Evolution API compatibility.

    Args:
        name: Instance name to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not name:
        return False, "Instance name cannot be empty"

    if len(name) < 2:
        return False, "Instance name must be at least 2 characters long"

    if len(name) > 50:
        return False, "Instance name must be 50 characters or less"

    # Check for invalid characters that could cause URL issues
    if re.search(r"[^a-zA-Z0-9\-_]", name):
        return (
            False,
            "Instance name can only contain letters, numbers, hyphens, and underscores",
        )

    # Check for leading/trailing hyphens
    if name.startswith("-") or name.endswith("-"):
        return False, "Instance name cannot start or end with a hyphen"

    # Check for consecutive hyphens
    if "--" in name:
        return False, "Instance name cannot contain consecutive hyphens"

    return True, ""
