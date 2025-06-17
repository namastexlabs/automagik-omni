"""
Evolution API message sender for WhatsApp.
Handles sending messages back to Evolution API using webhook payload information.
"""

import logging
import requests
from typing import Dict, Any, Optional
import time
import threading

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.evolution_api_sender")

class EvolutionApiSender:
    """Client for sending messages to Evolution API."""
    
    def __init__(self):
        """Initialize the sender."""
        self.server_url = None
        self.api_key = None
        self.instance_name = None
    
    def update_from_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """
        Update the sender configuration from incoming webhook data.
        
        Args:
            webhook_data: Webhook payload containing server_url, apikey, and instance
        """
        self.server_url = webhook_data.get('server_url')
        self.api_key = webhook_data.get('apikey')
        self.instance_name = webhook_data.get('instance')
        
        if all([self.server_url, self.api_key, self.instance_name]):
            logger.info(f"Updated Evolution API sender: server={self.server_url}, instance={self.instance_name}")
        else:
            logger.warning(f"Missing required webhook data: server_url={self.server_url}, api_key={'*' if self.api_key else None}, instance={self.instance_name}")
    
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
    
    def send_text_message(self, recipient: str, text: str) -> bool:
        """
        Send a text message via Evolution API.
        
        Args:
            recipient: WhatsApp ID of the recipient
            text: Message text
            
        Returns:
            bool: Success status
        """
        if not all([self.server_url, self.api_key, self.instance_name]):
            logger.error("Cannot send message: missing server URL, API key, or instance name")
            return False
        
        url = f"{self.server_url}/message/sendText/{self.instance_name}"
        formatted_recipient = self._prepare_recipient(recipient)
        
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": formatted_recipient,
            "text": text
        }
        
        try:
            # Log the request details (without sensitive data)
            logger.info(f"Sending message to {formatted_recipient} using URL: {url}")
            
            # Make the API request
            response = requests.post(url, headers=headers, json=payload)
            
            # Log response status
            logger.info(f"Response status: {response.status_code}")
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            logger.info(f"Message sent to {formatted_recipient}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False
    
    def send_presence(self, recipient: str, presence_type: str = "composing", refresh_seconds: int = 25) -> bool:
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
            logger.error("Cannot send presence: missing server URL, API key, or instance name")
            return False
        
        url = f"{self.server_url}/chat/sendPresence/{self.instance_name}"
        formatted_recipient = self._prepare_recipient(recipient)
        
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": formatted_recipient,
            "presence": presence_type,
            "delay": refresh_seconds * 1000  # Convert to milliseconds
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
                logger.warning(f"Failed to send presence update: {response.status_code} {response.text}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending presence update: {e}")
            return False

    def get_presence_updater(self, recipient: str, presence_type: str = "composing") -> 'PresenceUpdater':
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
        
        start_time = time.time()
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
                if message_sent_time and (time.time() - message_sent_time > post_send_cooldown):
                    logger.info(f"Typing indicator cooldown completed after message sent")
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