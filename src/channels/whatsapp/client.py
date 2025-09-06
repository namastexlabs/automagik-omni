"""
DEPRECATED: Legacy WhatsApp client for Agent application.
This module is deprecated and no longer used. The system now uses HTTP webhooks.
Kept for reference only.
"""

import logging
import requests
from typing import Dict, Any, Optional, Union
import threading
from datetime import datetime, timezone
import time
import os
import mimetypes
import base64
import tempfile

from src.channels.whatsapp.evolution_api_client import (
    EvolutionAPIClient,
    RabbitMQConfig,
    EventType,
)
from src.config import config
from src.ip_utils import replace_localhost_with_ipv4

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.client")


class WhatsAppClient:
    """DEPRECATED: Legacy WhatsApp client for interacting with Evolution API."""

    def __init__(self):
        """Initialize the WhatsApp client."""
        logger.warning("WhatsAppClient is deprecated. Use HTTP webhooks instead.")
        raise RuntimeError(
            "WhatsAppClient is deprecated and no longer functional. Use HTTP webhooks instead."
        )
        self.evolution_config = RabbitMQConfig(
            uri=config.rabbitmq.uri,
            exchange_name=config.rabbitmq.exchange_name,
            instance_name=config.rabbitmq.instance_name,
            global_mode=config.rabbitmq.global_mode,
            events=[EventType.MESSAGES_UPSERT],
            # Add explicit connection settings
            heartbeat=30,
            connection_attempts=3,
            retry_delay=5,
        )

        self.client = EvolutionAPIClient(self.evolution_config)
        self.api_base_url = self._get_api_base_url()
        self.api_key = self._get_api_key()

        # Store the server URL and API key from incoming messages
        self.dynamic_server_url = None
        self.dynamic_api_key = None

        # Connection monitoring
        self._connection_monitor_thread = None
        self._should_monitor = False

        # Initialize the temp directory to ensure it exists
        self._ensure_temp_directory()

        # Log using the actual URI instead of constructing it from parts
        logger.info(f"Connecting to Evolution API RabbitMQ at {config.rabbitmq.uri}")
        logger.info(f"Using WhatsApp instance: {self.evolution_config.instance_name}")

    def _ensure_temp_directory(self):
        """Ensure the temporary directory exists and has proper permissions."""
        temp_dir = os.path.join(os.getcwd(), "temp")
        try:
            # Create the directory if it doesn't exist
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
                logger.info(f"Created temporary directory at {temp_dir}")

            # Check if the directory is writable
            test_file_path = os.path.join(temp_dir, "_test_write.tmp")
            with open(test_file_path, "w") as f:
                f.write("test")
            os.remove(test_file_path)
            logger.info(f"Temporary directory {temp_dir} is ready for media downloads")
            return temp_dir
        except Exception as e:
            logger.error(f"Error configuring temporary directory: {e}", exc_info=True)
            # Try to use system temp directory as fallback
            temp_dir = tempfile.gettempdir()
            logger.info(f"Using system temp directory as fallback: {temp_dir}")
            return temp_dir

    def _get_api_base_url(self) -> str:
        """Extract the API base URL from the RabbitMQ URI."""
        # Format: amqp://user:password@host:port/vhost
        # We need the host part to construct the API URL
        try:
            uri = str(config.rabbitmq.uri)
            if "@" in uri:
                host = uri.split("@")[1].split(":")[0]
                # Determine protocol based on config
                protocol = "https" if config.whatsapp.api_use_https else "http"
                return f"{protocol}://{host}:8080"
            else:
                logger.warning("RabbitMQ URI is not in expected format")
                return replace_localhost_with_ipv4("http://localhost:8080")
        except (IndexError, ValueError):
            logger.warning("Failed to extract host from RabbitMQ URI, using default")
            return replace_localhost_with_ipv4("http://localhost:8080")

    def _get_api_key(self) -> str:
        """Get the API key from environment variables or use default."""
        # Get API key from environment variable
        api_key = os.getenv("EVOLUTION_API_KEY", "")
        if not api_key:
            logger.warning("EVOLUTION_API_KEY not set in environment variables")
        return api_key

    def connect(self) -> bool:
        """Connect to Evolution API via RabbitMQ."""
        logger.info(f"Connecting to Evolution API RabbitMQ at {config.rabbitmq.uri}")
        logger.info(f"Using WhatsApp instance: {config.rabbitmq.instance_name}")

        # Subscribe to message events
        if self.client.connect():
            self.client.subscribe(EventType.MESSAGES_UPSERT, self._handle_message)
            logger.info("Successfully subscribed to WhatsApp messages")
            return True
        else:
            logger.error("Failed to connect to Evolution API RabbitMQ")
            return False

    def update_from_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """Update client configuration from webhook data.

        Args:
            webhook_data: Webhook payload containing server_url, apikey, and instance
        """
        if "server_url" in webhook_data and webhook_data["server_url"]:
            self.dynamic_server_url = webhook_data["server_url"]
            logger.info(f"Updated server URL from webhook: {self.dynamic_server_url}")

        if "apikey" in webhook_data and webhook_data["apikey"]:
            self.dynamic_api_key = webhook_data["apikey"]
            logger.info("Updated API key from webhook")

        if "instance" in webhook_data and webhook_data["instance"]:
            # Update the instance name in the config
            config.whatsapp.instance = webhook_data["instance"]
            logger.info(
                f"Updated instance name from webhook: {config.whatsapp.instance}"
            )

    def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming WhatsApp messages from RabbitMQ."""
        logger.debug(f"Received message: {message.get('event', 'unknown')}")

        # Update client configuration from the message
        self.update_from_webhook(message)

        # Process media if present
        message_type = self.detect_message_type(message)
        if message_type in ["image", "audio", "video", "sticker", "document"]:
            logger.info(f"Processing incoming {message_type} message")
            message = self.process_incoming_media(message)

        # Pass the message to the message handler for processing
        # Import here to avoid circular imports
        from src.channels.whatsapp.handlers import message_handler

        message_handler.handle_message(message)

    def _monitor_connection(self):
        """Monitor the RabbitMQ connection and reconnect if needed."""
        logger.info("Starting RabbitMQ connection monitor")

        while self._should_monitor:
            try:
                # Check if the connection is still open
                if not self.client.connection or not self.client.connection.is_open:
                    logger.warning(
                        "RabbitMQ connection lost. Attempting to reconnect..."
                    )
                    if self.client.reconnect():
                        # Re-subscribe to messages after reconnecting
                        self.client.subscribe(
                            EventType.MESSAGES_UPSERT, self._handle_message
                        )
                        logger.info(
                            "Successfully reconnected and resubscribed to WhatsApp messages"
                        )
                    else:
                        logger.error("Failed to reconnect to RabbitMQ")

                # Wait before checking again
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in connection monitor: {e}", exc_info=True)
                time.sleep(60)  # Wait longer after an error

    def start(self) -> bool:
        """Start the WhatsApp client."""
        # Import here to avoid circular imports
        from src.channels.whatsapp.handlers import message_handler

        # Set up the message handler callback
        message_handler.send_response_callback = self.send_text_message

        # Start the message handler
        message_handler.start()

        # Connect to RabbitMQ and start consuming messages
        if self.connect():
            # Start connection monitor
            self._should_monitor = True
            self._connection_monitor_thread = threading.Thread(
                target=self._monitor_connection
            )
            self._connection_monitor_thread.daemon = True
            self._connection_monitor_thread.start()

            try:
                logger.info("Starting to consume WhatsApp messages")
                # Start consuming in a separate thread to avoid blocking
                thread = threading.Thread(target=self.client.start_consuming)
                thread.daemon = True
                thread.start()

                return True
            except Exception as e:
                logger.error(f"Error while consuming messages: {e}")
                self.stop()
                return False
        else:
            return False

    # start_async is now an alias for start since both are non-blocking
    def start_async(self) -> bool:
        """Start the WhatsApp client in a separate thread (alias for start)."""
        return self.start()

    def _check_queue_status(self):
        """Check the status of RabbitMQ queues and log diagnostic information."""
        try:
            if not self.client.connection or not self.client.connection.is_open:
                logger.warning("Cannot check queue status: not connected to RabbitMQ")
                return

            # Get the list of queues that should exist for our instance
            expected_queues = []
            for event in self.evolution_config.events:
                expected_queues.append(f"{self.evolution_config.instance_name}.{event}")

            # Also add our application queue
            app_queue = f"evolution-api-{self.evolution_config.instance_name}"
            expected_queues.append(app_queue)

            # Log the expected queues
            logger.info(f"Expected queues: {', '.join(expected_queues)}")

            # Check if the queues exist
            for queue_name in expected_queues:
                try:
                    # Use passive=True to only check if queue exists, not create it
                    queue_info = self.client.channel.queue_declare(
                        queue=queue_name, passive=True
                    )
                    message_count = queue_info.method.message_count
                    consumer_count = queue_info.method.consumer_count

                    logger.info(
                        f"Queue '{queue_name}' exists with {message_count} messages and {consumer_count} consumers"
                    )
                except Exception as e:
                    logger.warning(
                        f"Queue '{queue_name}' does not exist or cannot be accessed: {e}"
                    )

        except Exception as e:
            logger.error(f"Error checking queue status: {e}", exc_info=True)

    def stop(self):
        """Stop the WhatsApp client."""
        # Stop connection monitoring
        self._should_monitor = False
        if (
            self._connection_monitor_thread
            and self._connection_monitor_thread.is_alive()
        ):
            self._connection_monitor_thread.join(timeout=5.0)

        # Import here to avoid circular imports
        from src.channels.whatsapp.handlers import message_handler

        # Stop the message handler
        message_handler.stop()

        # Stop the Evolution API client
        self.client.stop()
        logger.info("WhatsApp client stopped")

    def send_text_message(self, recipient: str, text: str):
        """Send a text message via Evolution API.

        Returns:
            Tuple[bool, Optional[Dict]]: Success flag and response data if successful
        """
        # Use dynamic server URL if available, otherwise fall back to configured URL
        server_url = self.dynamic_server_url or self.api_base_url

        # Use dynamic API key if available, otherwise fall back to configured key
        api_key = self.dynamic_api_key or self.api_key

        url = f"{server_url}/message/sendText/{config.rabbitmq.instance_name}"

        # Format the recipient number correctly for Evolution API
        # - Remove @s.whatsapp.net suffix if present (this is critical)
        formatted_recipient = recipient
        if "@" in formatted_recipient:
            formatted_recipient = formatted_recipient.split("@")[0]

        # Remove any + at the beginning
        if formatted_recipient.startswith("+"):
            formatted_recipient = formatted_recipient[1:]

        logger.info(f"Formatted recipient from {recipient} to {formatted_recipient}")

        headers = {"apikey": api_key, "Content-Type": "application/json"}

        payload = {
            "number": formatted_recipient,  # This must be just the number without @s.whatsapp.net
            "text": text,
        }

        try:
            # Log the request details (without sensitive data)
            logger.info(f"Sending message to {formatted_recipient} using URL: {url}")
            logger.info(
                f"Headers: {{'apikey': '*****', 'Content-Type': '{headers['Content-Type']}'}}"
            )
            logger.info(
                f"Payload: {{'number': '{formatted_recipient}', 'text': '{text[:30]}...' if len(text) > 30 else text}}"
            )

            # Make the API request
            response = requests.post(url, headers=headers, json=payload)

            # Log response status
            logger.info(f"Response status: {response.status_code}")

            # Log response content for debugging
            try:
                response_text = (
                    response.text[:200] + "..."
                    if len(response.text) > 200
                    else response.text
                )
                logger.info(f"Response content: {response_text}")
            except Exception as e:
                logger.info(f"Could not log response content: {str(e)}")

            # Raise for HTTP errors
            response.raise_for_status()

            logger.info(f"Message sent to {formatted_recipient}")

            # Parse response data
            response_data = {
                "direction": "outbound",
                "status": "sent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recipient": formatted_recipient,
                "text": text,
                "raw_response": response.json() if response.content else None,
            }

            return True, response_data
        except requests.exceptions.RequestException as e:
            # More detailed error logging
            error_msg = f"Failed to send message: {str(e)}"

            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                error_msg += f" | Status Code: {status_code}"

                # Try to get response content
                try:
                    content = e.response.text
                    error_msg += f" | Response: {content[:200]}..."
                except Exception:
                    pass

            logger.error(error_msg)
            return False, None

    def detect_message_type(self, message: Dict[str, Any]) -> str:
        """Detect the message type from the message data.

        Args:
            message: The message data

        Returns:
            str: The message type ('text', 'image', 'audio', 'video', 'sticker', etc.)
        """
        # Extract message content
        data = message.get("data", {})
        message_content = data.get("message", {})

        # First, check if the message has a specific messageType field
        if "messageType" in data:
            logger.info(f"Using messageType from data: {data.get('messageType')}")
            return data.get("messageType")

        # Check for specific message types in the message structure
        if (
            "conversation" in message_content
            or "extendedTextMessage" in message_content
        ):
            return "text"
        elif "imageMessage" in message_content:
            logger.info("Detected image message from message structure")
            return "image"
        elif "audioMessage" in message_content:
            return "audio"
        elif "videoMessage" in message_content:
            return "video"
        elif "stickerMessage" in message_content:
            return "sticker"
        elif "documentMessage" in message_content:
            return "document"

        # Check for media URL as a last resort
        if "mediaUrl" in data and data.get("mediaUrl"):
            # Try to guess type from media URL
            media_url = data.get("mediaUrl")
            if ".jpg" in media_url or ".jpeg" in media_url or ".png" in media_url:
                logger.info(f"Detected image from mediaUrl extension: {media_url}")
                return "image"
            elif ".mp3" in media_url or ".ogg" in media_url or ".opus" in media_url:
                return "audio"
            elif ".mp4" in media_url or ".webm" in media_url:
                return "video"
            elif ".pdf" in media_url or ".doc" in media_url:
                return "document"
            else:
                # If URL exists but can't determine type, default to image
                logger.info(
                    f"Unknown media type but URL exists, defaulting to image: {media_url}"
                )
                return "image"

        # Default to unknown
        logger.warning(f"Could not determine message type from data: {data}")
        return "unknown"

    def extract_media_url(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract media URL from a message.

        Args:
            message: Message data

        Returns:
            Optional[str]: Media URL if found, None otherwise
        """
        # Get the message content and determine message type
        data = message.get("data", {})
        message_content = data.get("message", {})

        # Skip URL extraction for sticker messages
        message_type = self.detect_message_type(message)
        if message_type == "sticker":
            logger.info("Skipping URL extraction for sticker message")
            return None

        # Check mediaUrl in the data
        if "mediaUrl" in data:
            url = data.get("mediaUrl")
            if url and url != "https://web.whatsapp.net":
                logger.info(f"Found URL in data: {url}")
                return url

        # Check message content for URLs
        if (
            "imageMessage" in message_content
            and "url" in message_content["imageMessage"]
        ):
            return message_content["imageMessage"]["url"]
        elif (
            "audioMessage" in message_content
            and "url" in message_content["audioMessage"]
        ):
            return message_content["audioMessage"]["url"]
        elif (
            "videoMessage" in message_content
            and "url" in message_content["videoMessage"]
        ):
            return message_content["videoMessage"]["url"]
        elif (
            "documentMessage" in message_content
            and "url" in message_content["documentMessage"]
        ):
            return message_content["documentMessage"]["url"]

        return None

    def send_media(
        self,
        recipient: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
    ):
        """Send a media message via Evolution API.

        Args:
            recipient: WhatsApp ID of the recipient
            media_url: URL of the media file
            caption: Optional caption for the media
            media_type: Type of media ('image', 'audio', 'video', 'document', 'sticker')

        Returns:
            Tuple[bool, Optional[Dict]]: Success flag and response data if successful
        """
        # Determine the appropriate endpoint based on media type
        if media_type == "audio":
            endpoint = "sendAudio"
        elif media_type == "video":
            endpoint = "sendVideo"
        elif media_type == "document":
            endpoint = "sendDocument"
        elif media_type == "sticker":
            endpoint = "sendSticker"
        else:
            # Default to sendMedia for images and other types
            endpoint = "sendMedia"

        url = f"{self.api_base_url}/message/{endpoint}/{config.rabbitmq.instance_name}"

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {"number": recipient, "mediaUrl": media_url}

        if caption and media_type != "audio" and media_type != "sticker":
            payload["caption"] = caption

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"{media_type.capitalize()} sent to {recipient}")

            # Parse response data
            response_data = {
                "direction": "outbound",
                "status": "sent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recipient": recipient,
                "media_url": media_url,
                "media_type": media_type,
                "caption": caption,
                "raw_response": response.json() if response.content else None,
            }

            return True, response_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send {media_type}: {e}")
            return False, None

    def download_and_save_media(
        self, message: Dict[str, Any], base64_encode: bool = False
    ) -> Optional[str]:
        """Download and save media (stickers, images, etc.) from WhatsApp messages.

        Args:
            message: Message data
            base64_encode: Whether to return a base64-encoded string instead of URL

        Returns:
            Optional[str]: Media URL if successful, None otherwise
        """
        # Extract the media URL from the message
        media_url = self.extract_media_url(message)
        if not media_url:
            logger.warning("Could not extract media URL from message")
            return None

        # If we just need the media URL, return it directly
        if not base64_encode:
            return media_url

        # For base64 encoding, download the media and encode it
        try:
            response = requests.get(media_url, stream=True, timeout=30)
            response.raise_for_status()

            # Read the content and encode it to base64
            content = response.content
            encoded_content = base64.b64encode(content).decode("utf-8")
            return encoded_content

        except Exception as e:
            logger.error(f"Failed to download and encode media: {str(e)}")
            return None

    def process_incoming_media(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming media message to extract and format URLs and other data.

        This will extract the most appropriate media URL and return a cleaned version
        of the message with consistent media fields.

        Args:
            message: Raw message data

        Returns:
            Dict[str, Any]: Processed message with consistent media fields
        """
        # Extract and detect the message type
        message_type = self.detect_message_type(message)
        data = message.get("data", {})

        if message_type not in ["image", "video", "audio", "document", "sticker"]:
            # Not a media message, return unchanged
            return message

        # Extract media URL
        media_url = self.extract_media_url(message)

        # If we found a media URL, add it to the message data
        if media_url:
            # Add or update the mediaUrl field in the data dictionary
            data["mediaUrl"] = media_url

            # Also update the top-level message with updated data
            message["data"] = data
            logger.info(f"Updated {message_type} message with URL: {media_url}")

        return message

    def _get_media_as_base64(self, media_url: str) -> Optional[str]:
        """Download media from URL and convert to base64 string.

        Args:
            media_url: URL of the media

        Returns:
            Optional[str]: Base64-encoded string or None if failed
        """
        if not media_url:
            logger.error("No media URL provided")
            return None

        try:
            # For WhatsApp URLs, use requests to download the content
            if media_url.startswith("https://mmg.whatsapp.net") or media_url.startswith(
                "https://web.whatsapp.net"
            ):
                response = requests.get(media_url, stream=True, timeout=30)
                response.raise_for_status()

                # Read the content and encode it to base64
                content = response.content
                encoded_content = base64.b64encode(content).decode("utf-8")
                return encoded_content

            # For other URLs, just download normally
            response = requests.get(media_url, stream=True, timeout=30)
            response.raise_for_status()

            # Read the content and encode it to base64
            content = response.content
            encoded_content = base64.b64encode(content).decode("utf-8")
            return encoded_content

        except Exception as e:
            logger.error(f"Failed to download and encode media: {str(e)}")
            return None

    def get_media_as_base64(
        self, message_or_url: Union[Dict[str, Any], str]
    ) -> Optional[str]:
        """Retrieve base64 encoded media from a message or media URL.

        Args:
            message_or_url: The message or direct media URL

        Returns:
            Optional[str]: Base64 encoded media or None if failed
        """
        # Check if we already have base64 encoded data in the message
        if (
            isinstance(message_or_url, dict)
            and "data" in message_or_url
            and "media_base64" in message_or_url["data"]
        ):
            return message_or_url["data"]["media_base64"]

        # Get the media URL
        media_url = message_or_url
        if isinstance(message_or_url, dict):
            media_url = self.extract_media_url(message_or_url)

        if media_url:
            # Use the helper method to get the base64 data
            return self._get_media_as_base64(media_url)

        return None

    def _get_extension_from_mime_type(self, mime_type: str) -> str:
        """Get file extension from MIME type with explicit mappings for common types.

        Args:
            mime_type: The MIME type string

        Returns:
            str: The appropriate file extension including the dot
        """
        # Common image MIME types mapping
        mime_map = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/svg+xml": ".svg",
            "image/heic": ".heic",
            "image/heif": ".heif",
            # Audio types
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
            "audio/webm": ".webm",
            "audio/aac": ".aac",
            "audio/opus": ".opus",
            # Video types
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/ogg": ".ogv",
            "video/quicktime": ".mov",
            "video/x-matroska": ".mkv",
            "video/x-msvideo": ".avi",
            # Document types
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.ms-excel": ".xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        }

        # Return the extension directly if it's in our map
        if mime_type in mime_map:
            return mime_map[mime_type]

        # Fall back to the system's mime types
        extension = mimetypes.guess_extension(mime_type)
        if extension:
            return extension

        # Log the unknown mime type
        logger.warning(f"Unknown MIME type encountered: {mime_type}")

        # Return default extensions based on general MIME type categories
        if mime_type.startswith("image/"):
            return ".jpg"
        elif mime_type.startswith("audio/"):
            return ".mp3"
        elif mime_type.startswith("video/"):
            return ".mp4"
        elif mime_type.startswith("text/"):
            return ".txt"
        else:
            return ".bin"

    def _detect_mime_type_from_file(self, file_path: str) -> str:
        """Detect the MIME type by examining the file content.

        Args:
            file_path: Path to the file

        Returns:
            str: Detected MIME type or empty string if detection fails
        """
        try:
            # First try to use the magic library if available
            try:
                import magic

                return magic.from_file(file_path, mime=True)
            except ImportError:
                # If magic is not available, use a simpler approach based on file signatures
                with open(file_path, "rb") as f:
                    header = f.read(12)  # Read first 12 bytes for file signature

                # Check file signatures
                if header.startswith(b"\xff\xd8\xff"):  # JPEG starts with these bytes
                    return "image/jpeg"
                elif header.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG signature
                    return "image/png"
                elif header.startswith(b"GIF87a") or header.startswith(
                    b"GIF89a"
                ):  # GIF signature
                    return "image/gif"
                elif (
                    header.startswith(b"RIFF") and header[8:12] == b"WEBP"
                ):  # WEBP signature
                    return "image/webp"
                elif header.startswith(b"\x42\x4d"):  # BMP signature
                    return "image/bmp"

                # If signature detection fails, fall back to extension-based detection
                ext = os.path.splitext(file_path)[1].lower()
                mime_map = {
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".png": "image/png",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                    ".bmp": "image/bmp",
                    ".mp3": "audio/mpeg",
                    ".mp4": "video/mp4",
                    ".pdf": "application/pdf",
                }
                return mime_map.get(ext, "")
        except Exception as e:
            logger.error(f"Error detecting MIME type: {e}")
            return ""

    def send_presence(
        self,
        recipient: str,
        presence_type: str = "composing",
        refresh_seconds: int = 25,
    ) -> bool:
        """Send a presence update (typing indicator) to a WhatsApp user.

        Args:
            recipient: WhatsApp ID of the recipient
            presence_type: Type of presence ('composing', 'recording', 'available', etc.)
            refresh_seconds: How long the presence should last in seconds

        Returns:
            bool: Success status
        """
        # Use dynamic server URL if available, otherwise fall back to configured URL
        server_url = self.dynamic_server_url or self.api_base_url

        # Use dynamic API key if available, otherwise fall back to configured key
        api_key = self.dynamic_api_key or self.api_key

        # Use the instance name from config.whatsapp.instance instead of rabbitmq.instance_name
        instance_name = config.whatsapp.instance
        url = f"{server_url}/chat/sendPresence/{instance_name}"

        # Use the dynamic API key from the webhook data if available
        if hasattr(self, "dynamic_api_key") and self.dynamic_api_key:
            api_key = self.dynamic_api_key

        # Format the recipient number correctly for Evolution API
        # - Remove @s.whatsapp.net suffix if present
        formatted_recipient = recipient
        if "@" in formatted_recipient:
            formatted_recipient = formatted_recipient.split("@")[0]

        # Remove any + at the beginning
        if formatted_recipient.startswith("+"):
            formatted_recipient = formatted_recipient[1:]

        headers = {"apikey": api_key, "Content-Type": "application/json"}

        # Update the payload structure to match the API's expected format
        # The API expects presence and delay directly in the payload, not nested under options
        payload = {
            "number": formatted_recipient,
            "presence": presence_type,
            "delay": refresh_seconds * 1000,  # Convert to milliseconds
        }

        try:
            # Log the request details (without sensitive data)
            logger.info(f"Sending presence '{presence_type}' to {formatted_recipient}")

            # Make the API request
            response = requests.post(url, headers=headers, json=payload)

            # Log response status
            success = response.status_code in [200, 201, 202]
            if success:
                logger.info(f"Presence update sent to {formatted_recipient}")
            else:
                logger.warning(
                    f"Failed to send presence update: {response.status_code} {response.text}"
                )

            return success
        except Exception as e:
            logger.error(f"Error sending presence update: {e}")
            return False


class PresenceUpdater:
    """Manages continuous presence updates for WhatsApp conversations."""

    def __init__(self, client, recipient: str, presence_type: str = "composing"):
        """Initialize the presence updater.

        Args:
            client: WhatsApp client instance
            recipient: WhatsApp ID to send presence to
            presence_type: Type of presence status
        """
        self.client = client
        self.recipient = recipient
        self.presence_type = presence_type
        self.should_update = False
        self.update_thread = None
        self.message_sent = False  # New flag to indicate if message was sent

    def start(self):
        """Start sending continuous presence updates."""
        if self.update_thread and self.update_thread.is_alive():
            # Already running
            return

        self.should_update = True
        self.message_sent = False
        self.update_thread = threading.Thread(target=self._presence_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        logger.info(f"Started presence updates for {self.recipient}")

    def stop(self):
        """Stop sending presence updates."""
        self.should_update = False
        self.message_sent = True

        # Send one more presence update with "paused" to clear the typing indicator
        try:
            self.client.send_presence(self.recipient, "paused", 1)
        except Exception as e:
            logger.debug(f"Error clearing presence: {e}")

        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)

        logger.info(f"Stopped presence updates for {self.recipient}")

    def mark_message_sent(self):
        """Mark that the message has been sent, but keep typing indicator for a short time."""
        self.message_sent = True
        # We'll let the _presence_loop handle stopping after a short delay

    def _presence_loop(self):
        """Thread method to continuously update presence."""
        # Initial delay before starting presence updates
        time.sleep(0.5)

        time.time()
        post_send_cooldown = 1.0  # Short cooldown after message sent (in seconds)
        message_sent_time = None

        while self.should_update:
            try:
                # Send presence update with a 15-second refresh
                self.client.send_presence(self.recipient, self.presence_type, 15)

                # If message was sent, start the post-send cooldown
                if self.message_sent and message_sent_time is None:
                    message_sent_time = time.time()

                # Check if we've reached the post-send cooldown time
                if message_sent_time and (
                    time.time() - message_sent_time > post_send_cooldown
                ):
                    logger.info(
                        "Typing indicator cooldown completed after message sent"
                    )
                    self.should_update = False
                    break

                # Normal refresh cycle (shorter now for responsiveness)
                for _ in range(5):  # 5 second refresh cycle
                    if not self.should_update:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error updating presence: {e}")
                # Wait a bit before retrying
                time.sleep(2)


# Global instance (DISABLED - using HTTP webhooks only)
# whatsapp_client = WhatsAppClient()
