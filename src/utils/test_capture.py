"""
Test Capture Utility
Captures real WhatsApp media messages for testing agent API integration.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("src.utils.test_capture")


class TestCapture:
    """Utility to capture real WhatsApp media messages for testing."""

    def __init__(self, save_directory: str = "test_captures"):
        """Initialize the test capture utility.

        Args:
            save_directory: Directory to save captured test data
        """
        self.save_directory = save_directory
        self.capture_enabled = True  # Toggle this to enable/disable
        self._ensure_directory_exists()

    def _ensure_directory_exists(self):
        """Ensure the save directory exists."""
        try:
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory, exist_ok=True)
                logger.info(f"Created test captures directory: {self.save_directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {self.save_directory}: {e}")

    def enable_capture(self):
        """Enable test capture."""
        self.capture_enabled = True
        logger.info(
            "🎯 Test capture ENABLED - send a WhatsApp image to capture real data"
        )

    def disable_capture(self):
        """Disable test capture."""
        self.capture_enabled = False
        logger.info("⏹️ Test capture DISABLED")

    def capture_media_message(
        self, webhook_data: Dict[str, Any], instance_config=None
    ) -> Optional[str]:
        """Capture a real media message from WhatsApp for testing.

        Args:
            webhook_data: Raw webhook data from Evolution API
            instance_config: Instance configuration (optional)

        Returns:
            str: Path to saved file, or None if not captured
        """
        if not self.capture_enabled:
            return None

        try:
            # Extract message data
            data = webhook_data.get("data", {})
            message_obj = data.get("message", {})
            push_name = data.get("pushName", "Unknown User")

            # Debug logging for capture detection
            logger.info(f"🔍 Test capture checking message from {push_name}")
            logger.info(f"   Has 'base64' in data: {'base64' in data}")
            logger.info(f"   Message object keys: {list(message_obj.keys())}")
            logger.info(f"   Data keys: {list(data.keys())}")

            # Check if it's a media message with base64
            has_base64 = "base64" in data
            is_media = any(
                key in message_obj
                for key in [
                    "imageMessage",
                    "videoMessage",
                    "audioMessage",
                    "documentMessage",
                ]
            )

            logger.info(f"   is_media: {is_media}, has_base64: {has_base64}")

            if not (is_media and has_base64):
                logger.info("Skipping capture - not a media message with base64")
                return None

            # Generate capture filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            message_id = data.get("key", {}).get("id", "unknown")
            message_type = self._extract_message_type(data)

            # Create comprehensive capture data
            capture_data = {
                "capture_info": {
                    "timestamp": datetime.now().isoformat(),
                    "message_type": message_type,
                    "user_name": push_name,
                    "message_id": message_id,
                    "instance": instance_config.name if instance_config else "unknown",
                },
                "raw_webhook": webhook_data,
                "agent_api_payload": self._build_agent_payload(webhook_data, push_name),
                "curl_command": self._build_curl_command(webhook_data, push_name),
            }

            # Save capture file
            filename = f"capture_{message_type}_{timestamp}_{message_id[:8]}.json"
            file_path = os.path.join(self.save_directory, filename)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(capture_data, f, indent=2, ensure_ascii=False)

            logger.info(f"📸 CAPTURED real {message_type} message: {file_path}")
            logger.info(f"   User: {push_name}")
            logger.info(f"   Base64 size: {len(data.get('base64', ''))} chars")
            logger.info("   Use this file to test agent API with real WhatsApp media!")

            # Also create a standalone curl script
            curl_file = file_path.replace(".json", "_curl.sh")
            self._save_curl_script(capture_data["curl_command"], curl_file)

            # Auto-disable after first capture to avoid spam
            self.disable_capture()

            return file_path

        except Exception as e:
            logger.error(f"Failed to capture media message: {e}", exc_info=True)
            return None

    def _extract_message_type(self, data: Dict[str, Any]) -> str:
        """Extract message type from webhook data."""
        if "messageType" in data:
            msg_type = data["messageType"]
            # Normalize message types
            type_mapping = {
                "imageMessage": "image",
                "videoMessage": "video",
                "audioMessage": "audio",
                "documentMessage": "document",
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
            return "unknown"

    def _build_agent_payload(
        self, webhook_data: Dict[str, Any], push_name: str
    ) -> Dict[str, Any]:
        """Build agent API payload from webhook data."""
        data = webhook_data.get("data", {})
        message_obj = data.get("message", {})
        message_type = self._extract_message_type(data)

        # Extract message content (caption)
        content = self._extract_message_content(data, message_obj, push_name)

        # Build base payload
        payload = {
            "message_content": content,
            "message_type": message_type,
            "session_name": f"test_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "user": {
                "phone_number": "+5511999999999",  # Test phone
                "email": "",
                "user_data": {
                    "name": push_name,
                    "whatsapp_id": data.get("key", {}).get(
                        "remoteJid", "test@s.whatsapp.net"
                    ),
                    "source": "whatsapp_test_capture",
                },
            },
        }

        # Add media contents
        media_contents = self._build_media_contents(data, message_obj)
        if media_contents:
            payload["media_contents"] = media_contents

        return payload

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
        elif "audioMessage" in message_obj:
            content = ""  # Audio typically doesn't have captions

        # Add user name prefix
        if content:
            return f"[{push_name}]: {content}"
        else:
            return f"[{push_name}]: "

    def _build_media_contents(
        self, data: Dict[str, Any], message_obj: Dict[str, Any]
    ) -> Optional[list]:
        """Build media contents array for agent API."""
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

                # Build media item with base64 data
                media_item = {
                    "mime_type": media_info.get(
                        "mimetype", f"{media_type.replace('Message', '')}/"
                    ),
                    "alt_text": media_info.get(
                        "caption",
                        f"Real {media_type.replace('Message', '')} from WhatsApp",
                    ),
                }

                # Add base64 data if available
                if "base64" in data:
                    base64_data = data["base64"]
                    mime_type = media_info.get("mimetype", "image/jpeg")
                    media_item["data"] = f"data:{mime_type};base64,{base64_data}"

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
                break

        return media_contents if media_contents else None

    def _build_curl_command(self, webhook_data: Dict[str, Any], push_name: str) -> str:
        """Build curl command string."""
        payload = self._build_agent_payload(webhook_data, push_name)
        payload_json = json.dumps(payload, indent=2)

        return f"""curl -X POST "http://localhost:8000/api/v1/agent/simple/run" \\
    -H "Content-Type: application/json" \\
    -H "X-API-Key: your-api-key" \\
    -d '{payload_json}' """

    def _save_curl_script(self, curl_command: str, curl_file_path: str):
        """Save curl command as executable script."""
        try:
            script_content = f"""#!/bin/bash
# Real WhatsApp media test captured on {datetime.now().isoformat()}
# Usage: chmod +x {os.path.basename(curl_file_path)} && ./{os.path.basename(curl_file_path)}

{curl_command}
"""

            with open(curl_file_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            # Make executable
            os.chmod(curl_file_path, 0o755)

            logger.info(f"📜 Created curl script: {curl_file_path}")

        except Exception as e:
            logger.error(f"Failed to save curl script: {e}")


# Global instance
test_capture = TestCapture()
