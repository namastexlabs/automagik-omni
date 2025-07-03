"""
User Management Service
Handles interaction with the User Management API for user creation and verification.
"""

import logging
import requests
from typing import Dict, Any, Optional
from requests.exceptions import RequestException, Timeout

from src.config import config

# Configure logging
logger = logging.getLogger("src.services.user_management_service")


class UserManagementService:
    """Service for interacting with the User Management API."""

    def __init__(self):
        """Initialize the User Management Service."""
        # Use the same API URL and key as the agent API since they're the same service
        # Default to localhost:18881 if not configured
        self.api_url = config.agent_api.url or "http://localhost:18881"
        self.api_key = config.agent_api.api_key or "namastex888"
        self.timeout = getattr(config.agent_api, "timeout", 30)

        # Verify required configuration
        if not self.api_key:
            logger.warning(
                "Agent API key not set. User management API requests will likely fail."
            )

        logger.info(f"User Management Service initialized with URL: {self.api_url}")

    def _make_headers(self) -> Dict[str, str]:
        """Make headers for API requests."""
        headers = {"Content-Type": "application/json", "X-API-Key": self.api_key}
        return headers

    def check_user_exists(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Check if a user exists by phone number.

        Args:
            phone_number: The user's phone number

        Returns:
            User information dictionary if user exists, None otherwise
        """
        if not phone_number:
            logger.warning("No phone number provided for user existence check")
            return None

        endpoint = f"{self.api_url}/api/v1/users/{phone_number}"

        try:
            logger.info(f"Checking if user exists: {phone_number}")
            response = requests.get(
                endpoint, headers=self._make_headers(), timeout=self.timeout
            )

            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"User exists: {phone_number} -> ID: {user_data.get('id')}")
                return user_data
            elif response.status_code == 404:
                logger.info(f"User does not exist: {phone_number}")
                return None
            else:
                logger.warning(
                    f"Unexpected response when checking user existence: {response.status_code}"
                )
                return None

        except Timeout:
            logger.error(f"Timeout checking user existence for {phone_number}")
            return None
        except RequestException as e:
            logger.error(f"Error checking user existence for {phone_number}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error checking user existence for {phone_number}: {e}"
            )
            return None

    def create_user(
        self,
        phone_number: str,
        email: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new user.

        Args:
            phone_number: The user's phone number
            email: The user's email (optional)
            user_data: Additional user data (optional)

        Returns:
            Created user information dictionary if successful, None otherwise
        """
        if not phone_number:
            logger.warning("No phone number provided for user creation")
            return None

        endpoint = f"{self.api_url}/api/v1/users"

        payload = {"phone_number": phone_number}

        if email:
            payload["email"] = email
        if user_data:
            payload["user_data"] = user_data

        try:
            logger.info(f"Creating new user: {phone_number}")
            response = requests.post(
                endpoint,
                headers=self._make_headers(),
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                user_data = response.json()
                logger.info(
                    f"User created successfully: {phone_number} -> ID: {user_data.get('id')}"
                )
                return user_data
            else:
                logger.error(
                    f"Failed to create user {phone_number}: {response.status_code} - {response.text}"
                )
                return None

        except Timeout:
            logger.error(f"Timeout creating user {phone_number}")
            return None
        except RequestException as e:
            logger.error(f"Error creating user {phone_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating user {phone_number}: {e}")
            return None

    def get_or_create_user(
        self,
        phone_number: str,
        email: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get an existing user or create a new one if it doesn't exist.

        Args:
            phone_number: The user's phone number
            email: The user's email (optional)
            user_data: Additional user data (optional)

        Returns:
            User information dictionary if successful, None otherwise
        """
        # First, check if user exists
        existing_user = self.check_user_exists(phone_number)
        if existing_user:
            return existing_user

        # If user doesn't exist, create them
        return self.create_user(phone_number, email, user_data)


# Create a singleton instance
user_management_service = UserManagementService()
