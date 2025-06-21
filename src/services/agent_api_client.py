"""
Agent API Client
Handles interaction with the Automagik Agents API.
"""

import logging
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
    
    def __init__(self, config_override=None):
        """
        Initialize the API client.
        
        Args:
            config_override: Optional InstanceConfig object for per-instance configuration
        """
        if config_override:
            # Use per-instance configuration
            self.api_url = config_override.agent_api_url
            self.api_key = config_override.agent_api_key
            self.default_agent_name = config_override.default_agent
            self.timeout = config_override.agent_timeout
            logger.info(f"Agent API client initialized for instance '{config_override.name}' with URL: {self.api_url}")
        else:
            # Use global configuration (backward compatibility)
            self.api_url = config.agent_api.url
            self.api_key = config.agent_api.api_key
            self.default_agent_name = config.agent_api.default_agent_name
            self.timeout = getattr(config.agent_api, 'timeout', 60)
            logger.info(f"Agent API client initialized with global config, URL: {self.api_url}")
        
        # Verify required configuration
        if not self.api_key:
            logger.warning("Agent API key not set. API requests will likely fail.")
        
        # Flag for health check
        self.is_healthy = False
    
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
                 media_contents: Optional[List[Dict[str, Any]]] = None,
                 channel_payload: Optional[Dict[str, Any]] = None,
                 session_id: Optional[str] = None,
                 session_name: Optional[str] = None,
                 user_id: Optional[Union[str, int]] = None,
                 user: Optional[Dict[str, Any]] = None,
                 message_limit: int = 100,
                 session_origin: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 preserve_system_prompt: bool = False) -> Dict[str, Any]:
        """
        Run an agent with the provided parameters.
        
        Args:
            agent_name: Name of the agent to run
            message_content: The message content
            message_type: The message type (text, image, etc.)
            media_url: URL to media if present
            mime_type: MIME type of the media
            media_contents: List of media content objects
            channel_payload: Additional channel-specific payload
            session_id: Optional session ID for conversation continuity (legacy)
            session_name: Optional readable session name (preferred over session_id)
            user_id: User ID (optional if user dict is provided)
            user: User data dict with email, phone_number, and user_data for auto-creation
            message_limit: Maximum number of messages to return
            session_origin: Origin of the session
            context: Additional context for the agent
            preserve_system_prompt: Whether to preserve the system prompt
            
        Returns:
            The agent's response as a dictionary
        """
        endpoint = f"{self.api_url}/api/v1/agent/{agent_name}/run"
        
        # Prepare headers
        headers = self._make_headers()
        
        # Prepare payload
        payload = {
            "message_content": message_content,
            "message_limit": message_limit
        }
        
        # Handle user identification - prefer user dict over user_id
        if user:
            # Use the user dict for automatic user creation
            payload["user"] = user
            logger.info(f"Using user dict for automatic user creation: {user.get('phone_number', 'N/A')}")
        elif user_id is not None:
            # Fallback to existing user_id logic
            if isinstance(user_id, str):
                # First, check if it's a valid UUID string
                try:
                    uuid.UUID(user_id)
                    # If it's a valid UUID string, keep it as is
                    logger.debug(f"Using UUID string for user_id: {user_id}")
                except ValueError:
                    # If not a UUID, proceed with existing integer/anonymous logic
                    if user_id.isdigit():
                        user_id = int(user_id)
                    elif user_id.lower() == "anonymous":
                        user_id = 1 # Default anonymous user ID
                    else:
                        # If it's not a digit or "anonymous", log warning and use default
                        logger.warning(f"Invalid user_id format: {user_id}, using default user ID 1")
                        user_id = 1
            elif not isinstance(user_id, int):
                # If it's not a string or int, log warning and use default
                logger.warning(f"Unexpected user_id type: {type(user_id)}, using default user ID 1")
                user_id = 1

            payload["user_id"] = user_id
        else:
            # Handle case where both user and user_id are None
            logger.warning("Neither user dict nor user_id provided, using default user ID 1")
            payload["user_id"] = 1 # Assign a default if None is not allowed by API
        
        # Add optional parameters if provided
        if message_type:
            payload["message_type"] = message_type
            
        if media_url:
            payload["mediaUrl"] = media_url
            
        if mime_type:
            payload["mime_type"] = mime_type
            
        if media_contents:
            payload["media_contents"] = media_contents
            
        if channel_payload:
            payload["channel_payload"] = channel_payload
        
        # Prefer session_name over session_id if both are provided
        if session_name:
            payload["session_name"] = session_name
        elif session_id:
            payload["session_id"] = session_id
            
        if context:
            payload["context"] = context
            
        if session_origin:
            payload["session_origin"] = session_origin
            
        # Add preserve_system_prompt flag
        payload["preserve_system_prompt"] = preserve_system_prompt
        
        # Log the request (without sensitive information)
        logger.info(f"Making API request to {endpoint}")
        logger.debug(f"Request payload: {json.dumps({k:v for k,v in payload.items() if k != 'channel_payload'}, cls=UUIDEncoder)}")
        
        try:
            # Send request to the agent API
            response = requests.post(
                endpoint, 
                headers=headers, 
                json=payload,
                timeout=self.timeout
            )
            
            # Log the response status
            logger.info(f"API response status: {response.status_code}")
            
            if response.status_code == 200:
                # Parse the response
                try:
                    response_data = response.json()
                    
                    # Extract message from response - API returns either 'message' or directly the message content
                    if isinstance(response_data, dict) and 'message' in response_data:
                        agent_message = response_data.get('message')
                    else:
                        agent_message = response_data
                        
                    # Handle the case where agent_message might be a dict
                    if isinstance(agent_message, dict):
                        if 'content' in agent_message:
                            agent_message = agent_message.get('content', 'No response content')
                        else:
                            # Convert the dict to a string 
                            agent_message = json.dumps(agent_message)
                    
                    # Log success
                    message_length = len(agent_message) if isinstance(agent_message, str) else "non-string response"
                    logger.info(f"Received response from agent ({message_length} chars)")
                    
                    return {"response": agent_message}
                except json.JSONDecodeError:
                    # Not a JSON response, try to use the raw text
                    text_response = response.text
                    logger.warning(f"Response was not valid JSON, using raw text: {text_response[:100]}...")
                    return {"response": text_response}
            else:
                # Log error
                logger.error(f"Error from agent API: {response.status_code} {response.text}")
                return {"error": f"Desculpe, encontrei um erro (status {response.status_code}).", "details": response.text}
                
        except Timeout:
            logger.error(f"Timeout calling agent API after {self.timeout}s")
            return {"error": "Desculpe, está demorando mais do que o esperado para responder. Por favor, tente novamente."}
            
        except RequestException as e:
            logger.error(f"Error calling agent API: {e}")
            return {"error": "Desculpe, encontrei um erro ao me comunicar com meu cérebro. Por favor, tente novamente."}
            
        except Exception as e:
            logger.error(f"Unexpected error calling agent API: {e}", exc_info=True)
            return {"error": "Desculpe, encontrei um erro inesperado. Por favor, tente novamente."}
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Get a list of available agents.
        
        Returns:
            List of agent information dictionaries
        """
        endpoint = f"{self.api_url}/api/v1/agent/list"
        
        try:
            # Make the request
            response = requests.get(
                endpoint,
                headers=self._make_headers(),
                timeout=self.timeout
            )
                
            # Check for successful response
            response.raise_for_status()
            
            # Parse and return response
            result = response.json()
            return result
            
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            return []
            
    def process_message(self, 
                       message: str,
                       user_id: Optional[Union[str, int]] = None,
                       user: Optional[Dict[str, Any]] = None,
                       session_name: Optional[str] = None,
                       agent_name: Optional[str] = None,
                       message_type: str = "text",
                       media_url: Optional[str] = None,
                       media_contents: Optional[List[Dict[str, Any]]] = None,
                       mime_type: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None,
                       channel_payload: Optional[Dict[str, Any]] = None,
                       session_origin: Optional[str] = None,
                       preserve_system_prompt: bool = False) -> str:
        """
        Process a message using the agent API.
        This is a simplified wrapper around run_agent that returns just the response text.
        
        Args:
            message: The message to process
            user_id: User ID (optional if user dict is provided)
            user: User data dict with email, phone_number, and user_data for auto-creation
            session_name: Session name (preferred over session_id)
            agent_name: Optional agent name (defaults to self.default_agent_name)
            message_type: Message type (text, image, etc.)
            media_url: URL to media if present
            media_contents: List of media content objects
            mime_type: MIME type of the media
            context: Additional context
            channel_payload: Additional channel-specific payload
            session_origin: Origin of the session
            preserve_system_prompt: Whether to preserve the system prompt
            
        Returns:
            The response text from the agent
        """
        if not agent_name:
            agent_name = self.default_agent_name
            
        # Call run_agent
        result = self.run_agent(
            agent_name=agent_name,
            message_content=message,
            user_id=user_id,
            user=user,
            session_name=session_name,
            message_type=message_type,
            media_url=media_url,
            media_contents=media_contents,
            mime_type=mime_type,
            context=context,
            channel_payload=channel_payload,
            session_origin=session_origin,
            preserve_system_prompt=preserve_system_prompt
        )
        
        # Extract response
        if isinstance(result, dict):
            if "error" in result:
                return result.get("error", "Desculpe, encontrei um erro.")
            elif "response" in result:
                return result.get("response", "")
            else:
                return str(result)
        else:
            return str(result)

# Singleton instance
agent_api_client = AgentApiClient() 