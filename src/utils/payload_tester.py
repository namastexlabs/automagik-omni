"""
Payload Tester Utility
Saves incoming WhatsApp webhook payloads in agent API format for testing.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("src.utils.payload_tester")


class PayloadTester:
    """Utility to save webhook payloads in agent API format for testing."""

    def __init__(self, save_directory: str = "test_payloads"):
        """Initialize the payload tester.

        Args:
            save_directory: Directory to save test payloads
        """
        self.save_directory = save_directory
        self._ensure_directory_exists()

    def _ensure_directory_exists(self):
        """Ensure the save directory exists."""
        try:
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory, exist_ok=True)
                logger.info(f"Created test payloads directory: {self.save_directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {self.save_directory}: {e}")

    def save_webhook_as_agent_payload(
        self, webhook_data: Dict[str, Any], instance_config=None
    ) -> Optional[str]:
        """Save webhook data in agent API format for testing.

        Args:
            webhook_data: Raw webhook data from Evolution API
            instance_config: Instance configuration (optional)

        Returns:
            str: Path to saved file, or None if failed
        """
        try:
            # Extract message data
            data = webhook_data.get("data", {})
            message_obj = data.get("message", {})
            push_name = data.get("pushName", "Unknown User")

            # Determine message type and content
            message_type = self._extract_message_type(data)
            message_content = self._extract_message_content(
                data, message_obj, push_name
            )

            # Build agent API payload
            agent_payload = {
                "message_content": message_content,
                "message_type": message_type,
                "session_name": f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "user": {
                    "phone_number": "+5511999999999",  # Test phone number
                    "email": "",
                    "user_data": {
                        "name": push_name,
                        "whatsapp_id": data.get("key", {}).get(
                            "remoteJid", "test@s.whatsapp.net"
                        ),
                        "source": "whatsapp_test",
                    },
                },
            }

            # Add media contents if it's a media message
            media_contents = self._extract_media_contents(data, message_obj)
            if media_contents:
                agent_payload["media_contents"] = media_contents

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[
                :-3
            ]  # Include milliseconds
            message_id = data.get("key", {}).get("id", "unknown")
            filename = f"agent_payload_{message_type}_{timestamp}_{message_id[:8]}.json"

            # Save to file
            file_path = os.path.join(self.save_directory, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(agent_payload, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Saved agent API test payload: {file_path}")

            # Also save a curl command file
            self._save_curl_command(
                agent_payload, file_path.replace(".json", "_curl.sh")
            )

            return file_path

        except Exception as e:
            logger.error(f"Failed to save webhook as agent payload: {e}")
            return None

    def _extract_message_type(self, data: Dict[str, Any]) -> str:
        """Extract message type from webhook data."""
        if "messageType" in data:
            msg_type = data["messageType"]
            # Normalize message types for agent API
            type_mapping = {
                "imageMessage": "image",
                "videoMessage": "video",
                "audioMessage": "audio",
                "documentMessage": "document",
                "conversation": "text",
                "extendedTextMessage": "text",
            }
            return type_mapping.get(msg_type, msg_type)

        # Fallback: check message structure
        message_obj = data.get("message", {})
        if "imageMessage" in message_obj:
            return "image"
        elif "videoMessage" in message_obj:
            return "video"
        elif "audioMessage" in message_obj:
            return "audio"
        elif "documentMessage" in message_obj:
            return "document"
        else:
            return "text"

    def _extract_message_content(
        self, data: Dict[str, Any], message_obj: Dict[str, Any], push_name: str
    ) -> str:
        """Extract message content with user name prefix."""
        content = ""

        # Try to get caption or text content
        if "imageMessage" in message_obj:
            content = message_obj["imageMessage"].get("caption", "")
        elif "videoMessage" in message_obj:
            content = message_obj["videoMessage"].get("caption", "")
        elif "documentMessage" in message_obj:
            content = message_obj["documentMessage"].get("caption", "")
        elif "conversation" in message_obj:
            content = message_obj["conversation"]
        elif "extendedTextMessage" in message_obj:
            content = message_obj["extendedTextMessage"].get("text", "")

        # Add user name prefix
        if content:
            return f"[{push_name}]: {content}"
        else:
            return f"[{push_name}]: "

    def _extract_media_contents(
        self, data: Dict[str, Any], message_obj: Dict[str, Any]
    ) -> Optional[list]:
        """Extract media contents in agent API format."""
        media_contents = []

        # Check for different media types
        media_types = [
            "imageMessage",
            "videoMessage",
            "audioMessage",
            "documentMessage",
        ]

        for media_type in media_types:
            if media_type in message_obj:
                media_info = message_obj[media_type]

                # Build media item
                media_item = {
                    "mime_type": media_info.get(
                        "mimetype", f"{media_type.replace('Message', '')}/"
                    ),
                    "alt_text": media_info.get(
                        "caption", f"{media_type.replace('Message', '')} content"
                    ),
                }

                # Add URL if available
                if "mediaUrl" in data:
                    media_item["media_url"] = data["mediaUrl"]
                elif "url" in media_info:
                    media_item["media_url"] = media_info["url"]

                # Add base64 data if available (prioritize this for testing)
                if "base64" in data:
                    base64_data = data["base64"]
                    mime_type = media_info.get("mimetype", "image/jpeg")
                    media_item["data"] = f"data:{mime_type};base64,{base64_data}"
                    # Remove media_url when we have base64 data
                    media_item.pop("media_url", None)

                # Add dimensions for images/videos
                if media_type in ["imageMessage", "videoMessage"]:
                    if "width" in media_info:
                        media_item["width"] = media_info["width"]
                    if "height" in media_info:
                        media_item["height"] = media_info["height"]

                # Add file info for documents
                elif media_type == "documentMessage":
                    if "fileName" in media_info:
                        media_item["name"] = media_info["fileName"]
                    if "fileLength" in media_info:
                        media_item["size_bytes"] = int(media_info["fileLength"])

                media_contents.append(media_item)
                break  # Only process the first media type found

        return media_contents if media_contents else None

    def _save_curl_command(self, agent_payload: Dict[str, Any], curl_file_path: str):
        """Save a curl command file for easy testing."""
        try:
            # Build curl command
            payload_json = json.dumps(agent_payload, indent=2)

            curl_command = f"""#!/bin/bash
# Generated curl command for testing agent API
# Usage: chmod +x {os.path.basename(curl_file_path)} && ./{os.path.basename(curl_file_path)}

curl -X POST "http://localhost:8000/api/v1/agent/simple/run" \\
    -H "Content-Type: application/json" \\
    -H "X-API-Key: your-api-key" \\
    -d '{payload_json}'
"""

            with open(curl_file_path, "w", encoding="utf-8") as f:
                f.write(curl_command)

            # Make curl file executable
            os.chmod(curl_file_path, 0o755)

            logger.info(f"💾 Saved curl command: {curl_file_path}")

        except Exception as e:
            logger.error(f"Failed to save curl command: {e}")


# Global instance
payload_tester = PayloadTester()
