"""
Agent API Client
Handles interaction with the Automagik Agents API.
"""

import logging
import os
import time
import uuid
import json
from typing import Dict, Any, Optional, List, Union

import requests
from requests.exceptions import RequestException, Timeout

from src.config import config

# Configure logging
logger = logging.getLogger("src.services.agent_api_client")

# Custom JSON encoder that handles UUID objects
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # Convert UUID to string
            return str(obj)
        return super().default(obj)

class AgentApiClient:
    """Client for interacting with the Automagik Agents API."""
    
    def __init__(self):
        """Initialize the API client."""
        self.api_url = config.agent_api.url
        self.api_key = config.agent_api.api_key
        self.default_agent_name = config.agent_api.default_agent_name
        
        # Verify required configuration
        if not self.api_key:
            logger.warning("Agent API key not set. API requests will likely fail.")
        
        # Get timeout settings from config or use defaults
        self.timeout = getattr(config.agent_api, 'timeout', 60)
        
        # Flag for health check
        self.is_healthy = False
        
        logger.info(f"Agent API client initialized with URL: {self.api_url}")
    
    def _make_headers(self) -> Dict[str, str]:
        """Make headers for API requests."""
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add API key if available
        if self.api_key:
            headers['X-API-Key'] = self.api_key
            
        return headers
        
    def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            url = f"{self.api_url}/health"
            response = requests.get(url, timeout=5)
            self.is_healthy = response.status_code == 200
            return self.is_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False
            return False
    
    def run_agent(self, 
                 agent_name: str,
                 message_content: str,
                 message_type: Optional[str] = None,
                 media_url: Optional[str] = None,
                 mime_type: Optional[str] = None,
                 channel_payload: Optional[Dict[str, Any]] = None,
                 session_id: Optional[str] = None,
                 user_id: Optional[Union[str, int]] = "default_user",
                 message_limit: int = 10,
                 session_origin: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run an agent with the provided parameters.
        
        Args:
            agent_name: Name of the agent to run
            message_content: The message content
            message_type: The message type (text, image, etc.)
            media_url: URL to media if present
            mime_type: MIME type of the media
            channel_payload: Additional channel-specific payload
            session_id: Optional session ID for conversation continuity
            user_id: User ID (will be converted to integer if not None)
            message_limit: Maximum number of messages to return
            session_origin: Origin of the session
            context: Additional context for the agent
            
        Returns:
            The agent's response as a dictionary
        """
        endpoint = f"{self.api_url}/api/v1/pyagent/{agent_name}/run"
        
        # Prepare headers
        headers = self._make_headers()
        
        # Convert user_id to integer if it's not None
        if user_id is not None and user_id != "default_user":
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert user_id '{user_id}' to integer, using as is")
        
        # Prepare payload
        payload = {
            "message_content": message_content,
            "user_id": user_id,
            "message_limit": message_limit
        }
        
        # Add optional parameters if provided
        if message_type:
            payload["message_type"] = message_type
            
        if media_url:
            payload["mediaUrl"] = media_url
            
        if mime_type:
            payload["mime_type"] = mime_type
            
        if channel_payload:
            payload["channel_payload"] = channel_payload
            
        if session_id:
            payload["session_id"] = session_id
            
        if context:
            payload["context"] = context
            
        if session_origin:
            payload["session_origin"] = session_origin
        
        # Log the request (without sensitive information)
        logger.info(f"Making API request to {endpoint}")
        logger.debug(f"Request payload: {json.dumps({k:v for k,v in payload.items()}, cls=UUIDEncoder)}")
        
        try:
            # Send request to the agent API
            response = requests.post(
                endpoint, 
                headers=headers, 
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                # Parse the response
                response_data = response.json()
                
                # Extract message from response
                agent_message = response_data.get('message', 'No response from agent')
                
                # Log success
                logger.info(f"Received response from agent ({len(agent_message)} chars)")
                
                return {"response": agent_message}
            else:
                # Log error
                logger.error(f"Error from agent API: {response.status_code} {response.text}")
                return {"error": f"I'm sorry, I encountered an error (status {response.status_code}).", "details": response.text}
                
        except Timeout:
            logger.error(f"Timeout calling agent API after {self.timeout}s")
            return {"error": "I'm sorry, it's taking me longer than expected to respond. Please try again."}
            
        except RequestException as e:
            logger.error(f"Error calling agent API: {e}")
            return {"error": "I'm sorry, I encountered an error communicating with my brain. Please try again."}
            
        except Exception as e:
            logger.error(f"Unexpected error calling agent API: {e}", exc_info=True)
            return {"error": "I'm sorry, I encountered an unexpected error. Please try again."}
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Get a list of available agents.
        
        Returns:
            List of agent information dictionaries
        """
        endpoint = f"{self.api_url}/api/v1/agent/list"
        
        # Prepare headers
        headers = {
            "x-api-key": self.api_key
        }
        
        try:
            # Make the request
            with requests.Session() as session:
                response = session.get(
                    endpoint,
                    headers=headers
                )
                
            # Check for successful response
            response.raise_for_status()
            
            # Parse and return response
            result = response.json()
            return result
            
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            return []

# Singleton instance
agent_api_client = AgentApiClient() 