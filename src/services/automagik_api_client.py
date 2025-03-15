"""
Automagik API Client
Handles interactions with the Automagik API for users, sessions, and memories.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List, Union
import requests
from requests.exceptions import RequestException, Timeout
import time

from src.config import config

# Configure logging
logger = logging.getLogger("src.services.automagik_api_client")

class AutomagikAPIClient:
    """Client for interacting with the Automagik API."""
    
    def __init__(self):
        """Initialize the API client."""
        self.api_url = config.agent_api.url
        self.api_key = config.agent_api.api_key
        
        # Verify required configuration
        if not self.api_key:
            logger.warning("API key not set. API requests will likely fail.")
            
        # Default timeout in seconds
        self.timeout = 30
        
        logger.info(f"Automagik API client initialized with URL: {self.api_url}")
    
    def _make_headers(self) -> Dict[str, str]:
        """Make headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key
        }
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
                url,
                headers=self._make_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"User not found: {user_identifier}")
                return None
            else:
                logger.error(f"Error getting user: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def list_users(self, page: int = 1, page_size: int = 50, sort_desc: bool = True) -> Optional[Dict[str, Any]]:
        """List users with pagination."""
        try:
            url = f"{self.api_url}/api/v1/users"
            params = {
                "page": page,
                "page_size": page_size,
                "sort_desc": sort_desc
            }
            
            response = requests.get(
                url,
                headers=self._make_headers(),
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error listing users: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return None
    
    def find_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Find a user by phone number by listing all users and checking matches."""
        try:
            # First try direct lookup (faster)
            direct_user = self.get_user(phone_number)
            if direct_user:
                logger.info(f"Found user directly with phone number: {phone_number}")
                return direct_user
                
            # If that fails, list all users and check each one
            logger.info(f"Direct lookup failed for {phone_number}, searching in all users")
            users_response = self.list_users(page_size=100)
            
            if not users_response or "users" not in users_response:
                logger.warning("Failed to list users or no users found")
                return None
                
            # Check each user for phone number match
            for user in users_response["users"]:
                if user.get("phone_number") == phone_number:
                    logger.info(f"Found user with matching phone number: {phone_number}")
                    return user
                
            # Check for more pages if needed
            total_pages = users_response.get("total_pages", 1)
            if total_pages > 1:
                for page in range(2, min(total_pages + 1, 10)):  # Limit to 10 pages to avoid too many requests
                    users_response = self.list_users(page=page, page_size=100)
                    if not users_response or "users" not in users_response:
                        continue
                        
                    for user in users_response["users"]:
                        if user.get("phone_number") == phone_number:
                            logger.info(f"Found user with matching phone number on page {page}: {phone_number}")
                            return user
                
            # No matching user found
            logger.info(f"No user found with phone number: {phone_number}")
            return None
                
        except Exception as e:
            logger.error(f"Error finding user by phone: {e}")
            return None
    
    def create_user(self, email: Optional[str] = None, phone_number: Optional[str] = None, 
                   user_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
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
                url,
                headers=self._make_headers(),
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error creating user: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_or_create_user_by_phone(self, phone_number: str, user_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Get a user by phone number or create if not found."""
        # First, try to find the user by phone number
        user = self.find_user_by_phone(phone_number)
        if user:
            logger.info(f"Found existing user with phone {phone_number}: {user.get('id')}")
            return user
        
        # If not found, create a new user
        logger.info(f"No user found with phone {phone_number}, creating new user")
        new_user = self.create_user(phone_number=phone_number, user_data=user_data)
        
        if new_user:
            logger.info(f"Created new user with ID: {new_user.get('id')}")
            return new_user
        
        # If user creation failed due to conflict, try finding the user one more time
        if "409" in str(new_user) or "Conflict" in str(new_user):
            logger.info(f"Conflict creating user with phone {phone_number}, trying to find again")
            time.sleep(0.5)  # Small delay
            user = self.find_user_by_phone(phone_number)
            if user:
                return user
                
        # If all else fails, return a known valid user (typically ID 1)
        logger.warning(f"Failed to get or create user for {phone_number}, using default user")
        return {"id": 1}
    
    # Session endpoints
    def get_session(self, session_id: str, page: int = 1, page_size: int = 50, sort_desc: bool = True, 
                   hide_tools: bool = False) -> Optional[Dict[str, Any]]:
        """Get a session by ID."""
        try:
            url = f"{self.api_url}/api/v1/sessions/{session_id}"
            params = {
                "page": page,
                "page_size": page_size,
                "sort_desc": sort_desc,
                "hide_tools": hide_tools
            }
            
            response = requests.get(
                url,
                headers=self._make_headers(),
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Session not found: {session_id}")
                return None
            else:
                logger.error(f"Error getting session: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    # Memory endpoints
    def create_memory(self, name: str, content: str, user_id: Optional[int] = None, 
                     session_id: Optional[str] = None, agent_id: Optional[int] = None,
                     description: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a new memory."""
        try:
            url = f"{self.api_url}/api/v1/memories"
            payload = {
                "name": name,
                "content": content
            }
            
            if user_id:
                payload["user_id"] = user_id
            if session_id:
                payload["session_id"] = session_id
            if agent_id:
                payload["agent_id"] = agent_id
            if description:
                payload["description"] = description
            if metadata:
                payload["metadata"] = metadata
            
            response = requests.post(
                url,
                headers=self._make_headers(),
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error creating memory: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating memory: {e}")
            return None
    
    def list_memories(self, user_id: Optional[int] = None, agent_id: Optional[int] = None,
                     session_id: Optional[str] = None, page: int = 1, page_size: int = 50,
                     sort_desc: bool = True) -> Optional[Dict[str, Any]]:
        """List memories with optional filters."""
        try:
            url = f"{self.api_url}/api/v1/memories"
            params = {
                "page": page,
                "page_size": page_size,
                "sort_desc": sort_desc
            }
            
            if user_id:
                params["user_id"] = user_id
            if agent_id:
                params["agent_id"] = agent_id
            if session_id:
                params["session_id"] = session_id
            
            response = requests.get(
                url,
                headers=self._make_headers(),
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error listing memories: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return None

# Singleton instance
automagik_api_client = AutomagikAPIClient() 