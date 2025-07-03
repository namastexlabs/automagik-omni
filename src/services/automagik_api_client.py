"""
Automagik API Client
Handles interactions with the Automagik API for users, sessions, and memories.
"""

import logging
from typing import Dict, Any, Optional
import requests
import time

from src.config import config

# Configure logging
logger = logging.getLogger("src.services.automagik_api_client")


class AutomagikAPIClient:
    """Client for interacting with the Automagik API."""

    def __init__(self, api_url: str = None, api_key: str = None):
        """Initialize the API client."""
        self.api_url = api_url or config.agent_api.url
        self.api_key = api_key or config.agent_api.api_key

        # Verify required configuration
        if not self.api_key:
            logger.warning("API key not set. API requests will likely fail.")
        if not self.api_url:
            logger.warning("API URL not set. API requests will fail.")

        # Default timeout in seconds
        self.timeout = 30

        if self.api_url:
            logger.info(f"Automagik API client initialized with URL: {self.api_url}")

    def _make_headers(self) -> Dict[str, str]:
        """Make headers for API requests."""
        headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
        return headers

    def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            url = f"{self.api_url}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    # User endpoints
    def get_user(self, user_identifier: str) -> Optional[Dict[str, Any]]:
        """Get user by ID, email, or phone number."""
        try:
            url = f"{self.api_url}/api/v1/users/{user_identifier}"
            response = requests.get(
                url, headers=self._make_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"User not found: {user_identifier}")
                return None
            else:
                logger.error(
                    f"Error getting user: {response.status_code} (response: {len(response.text)} chars)"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def list_users(
        self, page: int = 1, page_size: int = 50, sort_desc: bool = True
    ) -> Optional[Dict[str, Any]]:
        """List users with pagination."""
        try:
            url = f"{self.api_url}/api/v1/users"
            params = {"page": page, "page_size": page_size, "sort_desc": sort_desc}

            response = requests.get(
                url, headers=self._make_headers(), params=params, timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Error listing users: {response.status_code} (response: {len(response.text)} chars)"
                )
                return None
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return None

    def create_user(
        self,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new user."""
        try:
            url = f"{self.api_url}/api/v1/users"
            payload = {}

            if email:
                payload["email"] = email
            if phone_number:
                payload["phone_number"] = phone_number
            if user_data:
                payload["user_data"] = user_data

            response = requests.post(
                url, headers=self._make_headers(), json=payload, timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Error creating user: {response.status_code} (response: {len(response.text)} chars)"
                )
                return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def get_or_create_user_by_phone(
        self, phone_number: str, user_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a user by phone number or create if not found."""
        # First, try to find the user directly by phone number
        user = self.get_user(phone_number)
        if user:
            logger.info(
                f"Found existing user with phone {phone_number}: {user.get('id')}"
            )
            return user

        # If not found directly, try getting all users and search by phone_number
        logger.info(f"Direct lookup failed for {phone_number}, searching in all users")
        all_users = self.list_users(page_size=100)
        if all_users and "users" in all_users:
            # Check for any number formatting variations
            clean_phone = self._clean_phone_number(phone_number)
            for existing_user in all_users["users"]:
                if existing_user.get("phone_number"):
                    existing_clean = self._clean_phone_number(
                        existing_user["phone_number"]
                    )
                    if existing_clean == clean_phone:
                        logger.info(
                            f"Found user with matching phone after cleaning: {existing_user.get('id')}"
                        )
                        return existing_user

        # If still not found, try to create a new user
        logger.info(f"No user found with phone {phone_number}, creating new user")
        new_user = self.create_user(phone_number=phone_number, user_data=user_data)

        if new_user:
            logger.info(f"Created new user with ID: {new_user.get('id')}")
            return new_user

        # If user creation failed due to conflict (already exists but we couldn't find it),
        # make one more attempt to find the user
        logger.info(
            "User creation failed, trying to search by phone again after conflict"
        )
        time.sleep(0.5)  # Small delay before retrying

        # Try direct lookup one more time
        user = self.get_user(phone_number)
        if user:
            logger.info(f"Found user on second lookup: {user.get('id')}")
            return user

        # If all else fails, use user ID 1
        logger.warning(
            f"Failed to get or create user for {phone_number}, using default user"
        )
        return {"id": 1}

    def _clean_phone_number(self, phone: str) -> str:
        """Clean phone number by removing all non-digit characters."""
        if not phone:
            return ""
        return "".join(filter(str.isdigit, phone))

    # Session endpoints
    def get_session(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 50,
        sort_desc: bool = True,
        hide_tools: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        try:
            url = f"{self.api_url}/api/v1/sessions/{session_id}"
            params = {
                "page": page,
                "page_size": page_size,
                "sort_desc": sort_desc,
                "hide_tools": hide_tools,
            }

            response = requests.get(
                url, headers=self._make_headers(), params=params, timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Session not found: {session_id}")
                return None
            else:
                logger.error(
                    f"Error getting session: {response.status_code} (response: {len(response.text)} chars)"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None


# Global instance - only initialized if configuration is available
automagik_api_client = None


def get_automagik_api_client() -> AutomagikAPIClient:
    """Get or create the global automagik API client."""
    global automagik_api_client

    if automagik_api_client is None:
        # Global agent API configuration no longer available
        logger.info(
            "Automagik API client not initialized - no global configuration available"
        )
        raise RuntimeError(
            "Automagik API client not configured. Use instance-specific configuration instead."
        )

    return automagik_api_client


# Global instance initialization disabled - using instance-specific configurations only
