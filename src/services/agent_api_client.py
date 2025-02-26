"""
Agent API Client
Handles interaction with the Automagik Agents API.
"""

import logging
import httpx
import json
from typing import Dict, Any, Optional, List, Union

from src.config import config

# Configure logging
logger = logging.getLogger("src.services.agent_api_client")

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
    
    def run_agent(self, 
                 agent_name: str,
                 message_content: str,
                 message_type: Optional[str] = None,
                 media_url: Optional[str] = None,
                 mime_type: Optional[str] = None,
                 channel_payload: Optional[Dict[str, Any]] = None,
                 session_id: Optional[str] = None,
                 user_id: str = "default_user",
                 message_limit: int = 10,
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
            user_id: User ID
            message_limit: Maximum number of messages to return
            context: Additional context for the agent
            
        Returns:
            The agent's response as a dictionary
        """
        endpoint = f"{self.api_url}/api/v1/agent/{agent_name}/run"
        
        # Prepare headers
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
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
        
        # Log the request (without sensitive information)
        logger.info(f"Making API request to {endpoint}")
        logger.debug(f"Request payload: {json.dumps({k:v for k,v in payload.items() if k != 'channel_payload'})}")
        
        try:
            # Make the request
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    endpoint,
                    headers=headers,
                    json=payload
                )
                
            # Check for successful response
            response.raise_for_status()
            
            # Parse and return response
            result = response.json()
            logger.info(f"Received successful response from API")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during API request: {e.response.status_code} - {e.response.text}")
            return {"error": f"HTTP error: {e.response.status_code}", "details": e.response.text}
            
        except httpx.RequestError as e:
            logger.error(f"Request error during API request: {str(e)}")
            return {"error": "Request error", "details": str(e)}
            
        except Exception as e:
            logger.error(f"Unexpected error during API request: {str(e)}", exc_info=True)
            return {"error": "Unexpected error", "details": str(e)}
    
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
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
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