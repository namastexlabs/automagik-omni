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
            logger.info(
                f"Agent API client initialized for instance '{config_override.name}' with URL: {self.api_url}"
            )
        else:
            # Use default values for backward compatibility
            self.api_url = ""
            self.api_key = ""
            self.default_agent_name = ""
            self.timeout = 60
            logger.warning(
                "Agent API client initialized without instance config - will not function without valid configuration"
            )

        # Verify required configuration
        if not self.api_key:
            logger.warning("Agent API key not set. API requests will likely fail.")

        # Flag for health check
        self.is_healthy = False

    def _make_headers(self) -> Dict[str, str]:
        """Make headers for API requests."""
        headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
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

    def run_agent(
        self,
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
        preserve_system_prompt: bool = False,
    ) -> Dict[str, Any]:
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
        payload = {"message_content": message_content, "message_limit": message_limit}

        # Handle user identification - prefer user dict over user_id
        if user:
            # Use the user dict for automatic user creation
            payload["user"] = user
            logger.info(
                f"Using user dict for automatic user creation: {user.get('phone_number', 'N/A')}"
            )
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
                        user_id = 1  # Default anonymous user ID
                    else:
                        # If it's not a digit or "anonymous", log warning and use default
                        logger.warning(
                            f"Invalid user_id format: {user_id}, using default user ID 1"
                        )
                        user_id = 1
            elif not isinstance(user_id, int):
                # If it's not a string or int, log warning and use default
                logger.warning(
                    f"Unexpected user_id type: {type(user_id)}, using default user ID 1"
                )
                user_id = 1

            payload["user_id"] = user_id
        else:
            # Handle case where both user and user_id are None
            logger.warning(
                "Neither user dict nor user_id provided, using default user ID 1"
            )
            payload["user_id"] = 1  # Assign a default if None is not allowed by API

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
        # Log payload summary without full content to avoid log clutter
        payload_summary = {
            "message_length": len(payload.get("message", "")),
            "user_id": payload.get("user_id"),
            "session_name": payload.get("session_name"),
            "message_type": payload.get("message_type"),
            "media_contents_count": len(payload.get("media_contents", [])),
            "has_context": bool(payload.get("context")),
        }
        logger.debug(f"Request payload summary: {json.dumps(payload_summary)}")

        try:
            # Send request to the agent API
            response = requests.post(
                endpoint, headers=headers, json=payload, timeout=self.timeout
            )

            # Log the response status
            logger.info(f"API response status: {response.status_code}")

            if response.status_code == 200:
                # Parse the response
                try:
                    response_data = response.json()

                    # Return the full response structure to preserve all fields
                    if isinstance(response_data, dict):
                        # Log success with message info if available
                        message_text = response_data.get("message", "")
                        session_id = response_data.get("session_id", "unknown")
                        success = response_data.get("success", True)

                        message_length = (
                            len(message_text)
                            if isinstance(message_text, str)
                            else "non-string message"
                        )
                        logger.info(
                            f"Received response from agent ({message_length} chars), session: {session_id}, success: {success}"
                        )

                        # Return the complete response structure
                        return response_data
                    else:
                        # If response is not a dict, wrap it in the expected format
                        logger.warning(
                            f"Agent response is not a dict, wrapping: {type(response_data)}"
                        )
                        return {
                            "message": str(response_data),
                            "success": True,
                            "session_id": None,
                            "tool_calls": [],
                            "tool_outputs": [],
                            "usage": {},
                        }
                except json.JSONDecodeError:
                    # Not a JSON response, try to use the raw text
                    text_response = response.text
                    logger.warning(
                        f"Response was not valid JSON, using raw text: {text_response[:100]}..."
                    )
                    return {
                        "message": text_response,
                        "success": True,
                        "session_id": None,
                        "tool_calls": [],
                        "tool_outputs": [],
                        "usage": {},
                    }
            else:
                # Log error
                logger.error(
                    f"Error from agent API: {response.status_code} (response: {len(response.text)} chars)"
                )
                return {
                    "error": f"Desculpe, encontrei um erro (status {response.status_code}).",
                    "details": f"Response length: {len(response.text)} chars",
                }

        except Timeout:
            logger.error(f"Timeout calling agent API after {self.timeout}s")
            return {
                "error": "Desculpe, está demorando mais do que o esperado para responder. Por favor, tente novamente."
            }

        except RequestException as e:
            logger.error(f"Error calling agent API: {e}")
            return {
                "error": "Desculpe, encontrei um erro ao me comunicar com meu cérebro. Por favor, tente novamente."
            }

        except Exception as e:
            logger.error(f"Unexpected error calling agent API: {e}", exc_info=True)
            return {
                "error": "Desculpe, encontrei um erro inesperado. Por favor, tente novamente."
            }

    def get_session_info(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Get session information from the agent API.

        Args:
            session_name: Name of the session to retrieve

        Returns:
            Session information dictionary if successful, None otherwise
        """
        endpoint = f"{self.api_url}/api/v1/sessions/{session_name}"

        try:
            # Make the request
            response = requests.get(
                endpoint, headers=self._make_headers(), timeout=self.timeout
            )

            # Check for successful response
            if response.status_code == 200:
                session_data = response.json()
                logger.debug(
                    f"Retrieved session info for {session_name}: user_id={session_data.get('user_id')}"
                )
                return session_data
            elif response.status_code == 404:
                logger.warning(f"Session {session_name} not found")
                return None
            else:
                logger.warning(
                    f"Unexpected response getting session {session_name}: {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting session info for {session_name}: {str(e)}")
            return None

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
                endpoint, headers=self._make_headers(), timeout=self.timeout
            )

            # Check for successful response
            response.raise_for_status()

            # Parse and return response
            result = response.json()
            return result

        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            return []

    def process_message(
        self,
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
        preserve_system_prompt: bool = False,
        trace_context=None,
    ) -> Dict[str, Any]:
        """
        Process a message using the agent API.
        This is a wrapper around run_agent that returns the full response structure.

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
            The full response structure from the agent including message, session_id, success, tool_calls, usage, etc.
        """
        if not agent_name:
            agent_name = self.default_agent_name

        # Log agent request if tracing enabled
        if trace_context:
            agent_request_payload = {
                "agent_name": agent_name,
                "message_content": message,
                "user_id": user_id,
                "user": user,
                "session_name": session_name,
                "message_type": message_type,
                "media_url": media_url,
                "media_contents": media_contents,
                "mime_type": mime_type,
                "context": context,
                "channel_payload": channel_payload,
                "session_origin": session_origin,
                "preserve_system_prompt": preserve_system_prompt,
            }
            trace_context.log_agent_request(agent_request_payload)

        # Record timing
        import time

        start_time = time.time()

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
            preserve_system_prompt=preserve_system_prompt,
        )

        # Record processing time and log response
        processing_time = int((time.time() - start_time) * 1000)
        if trace_context:
            trace_context.log_agent_response(result, processing_time)

        # Fetch current session info to get the authoritative user_id
        current_user_id = None
        if session_name:
            try:
                session_info = self.get_session_info(session_name)
                if session_info and "user_id" in session_info:
                    current_user_id = session_info["user_id"]
                    logger.info(
                        f"Session {session_name} current user_id: {current_user_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch session info for {session_name}: {e}")

        # Return the full response structure
        if isinstance(result, dict):
            if "error" in result:
                # Convert error to agent response format
                response = {
                    "message": result.get("error", "Desculpe, encontrei um erro."),
                    "success": False,
                    "session_id": None,
                    "tool_calls": [],
                    "tool_outputs": [],
                    "usage": {},
                    "error": result.get("details", ""),
                }
            else:
                # Return the full response (already in correct format from run_agent)
                response = result
        else:
            # Convert non-dict result to agent response format
            response = {
                "message": str(result),
                "success": True,
                "session_id": None,
                "tool_calls": [],
                "tool_outputs": [],
                "usage": {},
            }

        # Add the current user_id from session to the response
        if current_user_id:
            response["current_user_id"] = current_user_id

        return response


# Singleton instance
agent_api_client = AgentApiClient()
