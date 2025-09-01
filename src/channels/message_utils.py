"""Utility functions for message processing across channels."""

import logging
from typing import Any, Dict, Union


logger = logging.getLogger(__name__)


def extract_response_text(response: Union[str, Dict[str, Any]]) -> str:
    """
    Extract text content from various response formats.

    Args:
        response: Response data from message router or API

    Returns:
        Extracted text content
    """
    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        # Check common response fields
        for field in ["message", "text", "content", "response"]:
            if field in response and response[field]:
                return str(response[field])

        # Check nested content
        if "data" in response and isinstance(response["data"], dict):
            return extract_response_text(response["data"])

        # If all else fails, convert to string
        return str(response)

    # Fallback for other types
    return str(response)
