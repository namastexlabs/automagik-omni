"""
Evolution API message sender for WhatsApp.
Handles sending messages back to Evolution API using webhook payload information.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import quote
import time
import threading
import random

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.evolution_api_sender")


class EvolutionApiSender:
    """Client for sending messages to Evolution API."""

    def __init__(self, config_override=None):
        """
        Initialize the sender.

        Args:
            config_override: Optional InstanceConfig object for per-instance configuration
        """
        if config_override:
            # Use per-instance configuration
            self.server_url = config_override.evolution_url or None
            self.api_key = config_override.evolution_key or None
            self.instance_name = config_override.whatsapp_instance
            logger.info(
                f"Evolution API sender initialized for instance '{config_override.name}'"
            )
        else:
            # Initialize with empty values (will be set from webhook)
            self.server_url = None
            self.api_key = None
            self.instance_name = None

    def update_from_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """
        Update the sender configuration from incoming webhook data.

        Args:
            webhook_data: Webhook payload containing server_url, apikey, and instance
        """
        self.server_url = webhook_data.get("server_url")
        self.api_key = webhook_data.get("apikey")
        self.instance_name = webhook_data.get("instance")

        if all([self.server_url, self.api_key, self.instance_name]):
            logger.info(
                f"Updated Evolution API sender: server={self.server_url}, instance={self.instance_name}"
            )
        else:
            logger.warning(
                f"Missing required webhook data: server_url={self.server_url}, api_key={'*' if self.api_key else None}, instance={self.instance_name}"
            )

    def _prepare_recipient(self, recipient: str) -> str:
        """
        Format recipient number for Evolution API.

        Args:
            recipient: WhatsApp number or JID

        Returns:
            str: Properly formatted recipient
        """
        # Remove @s.whatsapp.net suffix if present
        formatted_recipient = recipient
        if "@" in formatted_recipient:
            formatted_recipient = formatted_recipient.split("@")[0]

        # Remove any + at the beginning
        if formatted_recipient.startswith("+"):
            formatted_recipient = formatted_recipient[1:]

        return formatted_recipient

    def send_text_message(
        self, recipient: str, text: str, quoted_message: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a text message via Evolution API with optional message quoting and auto-splitting.

        Args:
            recipient: WhatsApp ID of the recipient
            text: Message text
            quoted_message: Optional message to quote/reply to

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot send message: missing server URL, API key, or instance name"
            )
            return False

        # Check if message should be split (contains \n\n and is replying to a text message)
        should_split = self._should_split_message(text, quoted_message)

        if should_split:
            return self._send_split_messages(recipient, text, quoted_message)
        else:
            return self._send_single_message(recipient, text, quoted_message)

    def _should_split_message(
        self, text: str, quoted_message: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Determine if a message should be split.

        Args:
            text: Message text
            quoted_message: Original message being replied to

        Returns:
            bool: True if message should be split
        """
        # Don't split if it's a reply to a media message
        if quoted_message and self._is_media_message(quoted_message):
            logger.info("Not splitting message - replying to media message")
            return False

        # Split if contains double newlines
        if "\n\n" in text:
            logger.info("Message contains \\n\\n - will split into multiple messages")
            return True

        return False

    def _is_media_message(self, quoted_message: Dict[str, Any]) -> bool:
        """Check if the quoted message is a media message."""
        if not quoted_message:
            return False

        message_obj = quoted_message.get("message", {})
        media_types = [
            "imageMessage",
            "videoMessage",
            "audioMessage",
            "documentMessage",
            "stickerMessage",
        ]

        return any(media_type in message_obj for media_type in media_types)

    def _send_split_messages(
        self, recipient: str, text: str, quoted_message: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Send text as multiple messages split by \\n\\n with random delays.

        Args:
            recipient: WhatsApp ID of the recipient
            text: Full message text
            quoted_message: Optional message to quote (only for first message)

        Returns:
            bool: Success status (True if all messages sent successfully)
        """
        # Split by double newlines and filter out empty strings
        parts = [part.strip() for part in text.split("\n\n") if part.strip()]

        if len(parts) <= 1:
            # No actual split needed
            return self._send_single_message(recipient, text, quoted_message)

        logger.info(f"Splitting message into {len(parts)} parts")

        success_count = 0
        for i, part in enumerate(parts):
            # Only quote the first message
            quote_for_this_part = quoted_message if i == 0 else None

            # Send the message part
            if self._send_single_message(recipient, part, quote_for_this_part):
                success_count += 1

            # Add random delay between messages (except for the last one)
            if i < len(parts) - 1:
                delay = random.uniform(0.3, 1.0)  # 300ms to 1000ms
                logger.info(f"Waiting {delay:.3f}s before sending next message part")
                time.sleep(delay)

        success = success_count == len(parts)
        logger.info(
            f"Split message result: {success_count}/{len(parts)} parts sent successfully"
        )
        return success

    def _send_single_message(
        self, recipient: str, text: str, quoted_message: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Send a single text message via Evolution API.

        Args:
            recipient: WhatsApp ID of the recipient
            text: Message text
            quoted_message: Optional message to quote/reply to

        Returns:
            bool: Success status
        """
        url = f"{self.server_url}/message/sendText/{quote(self.instance_name, safe='')}"
        formatted_recipient = self._prepare_recipient(recipient)

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {"number": formatted_recipient, "text": text}

        # Add quoted message if provided (disabled due to Evolution API 400 errors)
        # if quoted_message:
        #     payload["quoted"] = self._format_quoted_message(quoted_message)
        #     logger.info("Including quoted message in response")

        try:
            # Log the request details (without sensitive data)
            logger.info(f"Sending message to {formatted_recipient} using URL: {url}")

            # Make the API request
            response = requests.post(url, headers=headers, json=payload)

            # Log response status
            logger.info(f"Response status: {response.status_code}")

            # Handle Evolution API's known database schema issue with quoted messages
            # See: https://github.com/EvolutionAPI/evolution-api/issues/1247
            if response.status_code == 400:
                # Log the actual error response for debugging
                try:
                    error_response = response.json()
                    error_message = str(error_response.get("message", ""))
                    logger.error(f"Evolution API 400 error response: {error_response}")

                    if quoted_message and (
                        "typebotSessionId" in error_message
                        or "database" in error_message.lower()
                    ):
                        logger.warning(
                            f"Evolution API 400 error (known database schema issue): {error_message}"
                        )
                        logger.info(
                            "Message likely sent despite 400 error - continuing"
                        )
                        return True
                except Exception as e:
                    logger.error(f"Could not parse 400 error response: {e}")
                    logger.error(f"Raw response text: {response.text}")

                if quoted_message:
                    logger.warning(
                        "400 error with quoted message - this may be Evolution API database schema issue"
                    )
                    logger.info(
                        "Attempting to continue - message may have been sent despite error"
                    )
                    return True
                else:
                    logger.error(
                        "400 error without quoted message - this is a real error"
                    )
                    return False

            # Raise for other HTTP errors
            response.raise_for_status()

            logger.info(f"Message sent to {formatted_recipient}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    def _format_quoted_message(self, quoted_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a message for quoting according to Evolution API format.

        Args:
            quoted_message: Original message data from webhook

        Returns:
            Dict: Formatted quoted message for Evolution API
        """
        # Extract key information
        key_data = quoted_message.get("key", {})
        message_data = quoted_message.get("message", {})

        # Basic quoted structure
        quoted_payload = {"key": {"id": key_data.get("id", "")}, "message": {}}

        # Handle different message types for quoted content
        if "conversation" in message_data:
            quoted_payload["message"]["conversation"] = message_data["conversation"]
        elif "extendedTextMessage" in message_data:
            quoted_payload["message"]["conversation"] = message_data[
                "extendedTextMessage"
            ].get("text", "")
        elif "imageMessage" in message_data:
            # For media messages, use caption or indicate it's an image
            caption = message_data["imageMessage"].get("caption", "[Image]")
            quoted_payload["message"]["conversation"] = caption
        elif "videoMessage" in message_data:
            caption = message_data["videoMessage"].get("caption", "[Video]")
            quoted_payload["message"]["conversation"] = caption
        elif "audioMessage" in message_data:
            quoted_payload["message"]["conversation"] = "[Audio]"
        elif "documentMessage" in message_data:
            file_name = message_data["documentMessage"].get("fileName", "[Document]")
            quoted_payload["message"]["conversation"] = file_name
        else:
            # Fallback for unknown message types
            quoted_payload["message"]["conversation"] = "[Message]"

        return quoted_payload

    def send_media_message(
        self,
        recipient: str,
        media_type: str,
        media: str,
        mime_type: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> bool:
        """
        Send a media message (image, video, document) via Evolution API.

        Args:
            recipient: WhatsApp ID of the recipient
            media_type: Type of media (image, video, document)
            media: URL or base64 data
            mime_type: MIME type of the media
            caption: Optional caption text
            filename: Optional filename for documents

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot send media message: missing server URL, API key, or instance name"
            )
            return False

        url = (
            f"{self.server_url}/message/sendMedia/{quote(self.instance_name, safe='')}"
        )
        formatted_recipient = self._prepare_recipient(recipient)

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {
            "number": formatted_recipient,
            "mediatype": media_type,
            "media": media,
            "mimetype": mime_type,
        }

        if caption:
            payload["caption"] = caption
        if filename:
            payload["fileName"] = filename

        try:
            logger.info(f"Sending {media_type} message to {formatted_recipient}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            logger.info(f"Media message sent to {formatted_recipient}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send media message: {str(e)}")
            return False

    def send_audio_message(self, recipient: str, audio: str) -> bool:
        """
        Send a WhatsApp audio message via Evolution API.

        Args:
            recipient: WhatsApp ID of the recipient
            audio: URL or base64 data for the audio

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot send audio message: missing server URL, API key, or instance name"
            )
            return False

        url = f"{self.server_url}/message/sendWhatsAppAudio/{quote(self.instance_name, safe='')}"
        formatted_recipient = self._prepare_recipient(recipient)

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {"number": formatted_recipient, "audio": audio}

        try:
            logger.info(f"Sending audio message to {formatted_recipient}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            logger.info(f"Audio message sent to {formatted_recipient}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send audio message: {str(e)}")
            return False

    def send_sticker_message(self, recipient: str, sticker: str) -> bool:
        """
        Send a sticker via Evolution API.

        Args:
            recipient: WhatsApp ID of the recipient
            sticker: URL or base64 data for the sticker

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot send sticker: missing server URL, API key, or instance name"
            )
            return False

        url = f"{self.server_url}/message/sendSticker/{quote(self.instance_name, safe='')}"
        formatted_recipient = self._prepare_recipient(recipient)

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {"number": formatted_recipient, "sticker": sticker}

        try:
            logger.info(f"Sending sticker to {formatted_recipient}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            logger.info(f"Sticker sent to {formatted_recipient}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send sticker: {str(e)}")
            return False

    def send_contact_message(
        self, recipient: str, contacts: List[Dict[str, Any]]
    ) -> bool:
        """
        Send contact card(s) via Evolution API.

        Args:
            recipient: WhatsApp ID of the recipient
            contacts: List of contact dictionaries

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot send contact: missing server URL, API key, or instance name"
            )
            return False

        url = f"{self.server_url}/message/sendContact/{quote(self.instance_name, safe='')}"
        formatted_recipient = self._prepare_recipient(recipient)

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {"number": formatted_recipient, "contact": contacts}

        try:
            logger.info(f"Sending contact(s) to {formatted_recipient}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            logger.info(f"Contact(s) sent to {formatted_recipient}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send contact: {str(e)}")
            return False

    def send_reaction_message(
        self, recipient: str, message_id: str, reaction: str
    ) -> bool:
        """
        Send a reaction to a message via Evolution API.

        Args:
            recipient: WhatsApp ID of the recipient
            message_id: ID of the message to react to
            reaction: Reaction emoji

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot send reaction: missing server URL, API key, or instance name"
            )
            return False

        url = f"{self.server_url}/message/sendReaction/{quote(self.instance_name, safe='')}"

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {
            "key": {"remoteJid": recipient, "fromMe": False, "id": message_id},
            "reaction": reaction,
        }

        try:
            logger.info(f"Sending reaction '{reaction}' to message {message_id}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            logger.info(f"Reaction sent to {recipient}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send reaction: {str(e)}")
            return False

    def fetch_profile(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a user's WhatsApp profile via Evolution API.

        Args:
            phone_number: Phone number (will be formatted)

        Returns:
            Optional[Dict]: Profile data if successful, None otherwise
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot fetch profile: missing server URL, API key, or instance name"
            )
            return None

        url = (
            f"{self.server_url}/chat/fetchProfile/{quote(self.instance_name, safe='')}"
        )
        formatted_number = self._prepare_recipient(phone_number)

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {"number": formatted_number}

        try:
            logger.info(f"Fetching profile for {formatted_number}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            profile_data = response.json()
            logger.info(f"Profile fetched for {formatted_number}")
            return profile_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch profile: {str(e)}")
            return None

    def update_profile_picture(self, picture_url: str) -> bool:
        """
        Update the instance's profile picture via Evolution API.

        Args:
            picture_url: URL to the new profile picture

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot update profile picture: missing server URL, API key, or instance name"
            )
            return False

        url = f"{self.server_url}/chat/updateProfilePicture/{quote(self.instance_name, safe='')}"

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {"picture": picture_url}

        try:
            logger.info(f"Updating profile picture for instance {self.instance_name}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            logger.info(f"Profile picture updated for instance {self.instance_name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update profile picture: {str(e)}")
            return False

    def send_presence(
        self,
        recipient: str,
        presence_type: str = "composing",
        refresh_seconds: int = 25,
    ) -> bool:
        """
        Send a presence update (typing indicator) to a WhatsApp user.

        Args:
            recipient: WhatsApp ID of the recipient
            presence_type: Type of presence ('composing', 'recording', 'available', etc.)
            refresh_seconds: How long the presence should last in seconds

        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error(
                "Cannot send presence: missing server URL, API key, or instance name"
            )
            return False

        url = (
            f"{self.server_url}/chat/sendPresence/{quote(self.instance_name, safe='')}"
        )
        formatted_recipient = self._prepare_recipient(recipient)

        headers = {"apikey": self.api_key, "Content-Type": "application/json"}

        payload = {
            "number": formatted_recipient,
            "presence": presence_type,
            "delay": refresh_seconds * 1000,  # Convert to milliseconds
        }

        try:
            # Log the request details
            logger.info(f"Sending presence '{presence_type}' to {formatted_recipient}")

            # Make the API request
            response = requests.post(url, headers=headers, json=payload)

            # Log response status
            success = response.status_code in [200, 201, 202]
            if success:
                logger.info(f"Presence update sent to {formatted_recipient}")
            else:
                logger.warning(
                    f"Failed to send presence update: {response.status_code} (response: {len(response.text)} chars)"
                )

            return success

        except Exception as e:
            logger.error(f"Error sending presence update: {e}")
            return False

    def get_presence_updater(
        self, recipient: str, presence_type: str = "composing"
    ) -> "PresenceUpdater":
        """
        Get a PresenceUpdater instance for the given recipient.

        Args:
            recipient: WhatsApp ID of the recipient
            presence_type: Type of presence status

        Returns:
            PresenceUpdater: Instance for managing presence updates
        """
        return PresenceUpdater(self, recipient, presence_type)


class PresenceUpdater:
    """Manages continuous presence updates for WhatsApp conversations."""

    def __init__(self, sender, recipient: str, presence_type: str = "composing"):
        """
        Initialize the presence updater.

        Args:
            sender: EvolutionApiSender instance
            recipient: WhatsApp ID to send presence to
            presence_type: Type of presence status
        """
        self.sender = sender
        self.recipient = recipient
        self.presence_type = presence_type
        self.should_update = False
        self.update_thread = None
        self.message_sent = False

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
            self.sender.send_presence(self.recipient, "paused", 1)
        except Exception as e:
            logger.debug(f"Error clearing presence: {e}")

        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)

        logger.info(f"Stopped presence updates for {self.recipient}")

    def mark_message_sent(self):
        """Mark that the message has been sent, but keep typing indicator for a short time."""
        self.message_sent = True

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
                self.sender.send_presence(self.recipient, self.presence_type, 15)

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


# Create singleton instance
evolution_api_sender = EvolutionApiSender()
