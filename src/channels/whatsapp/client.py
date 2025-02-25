"""
WhatsApp client using Evolution API and RabbitMQ.
"""

import logging
import json
import requests
from typing import Dict, Any, Optional, List
import threading
from datetime import datetime

from evolution_api_client import EvolutionAPIClient, RabbitMQConfig, EventType
from src.config import config
from src.channels.whatsapp.handlers import message_handler

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.client")

class WhatsAppClient:
    """WhatsApp client for interacting with Evolution API."""
    
    def __init__(self):
        """Initialize the WhatsApp client."""
        self.evolution_config = RabbitMQConfig(
            uri=config.rabbitmq.uri,
            exchange_name=config.rabbitmq.exchange_name,
            instance_name=config.rabbitmq.instance_name,
            global_mode=config.rabbitmq.global_mode,
            events=[EventType.MESSAGES_UPSERT]
        )
        
        self.client = EvolutionAPIClient(self.evolution_config)
        self.api_base_url = self._get_api_base_url()
        self.api_key = self._get_api_key()
        
        # Set up message handler to use our send_text_message method
        message_handler.set_send_response_callback(self.send_text_message)
    
    def _get_api_base_url(self) -> str:
        """Extract the API base URL from the RabbitMQ URI."""
        # Format: amqp://user:password@host:port/vhost
        # We need the host part to construct the API URL
        try:
            uri = str(config.rabbitmq.uri)
            if '@' in uri:
                host = uri.split('@')[1].split(':')[0]
                return f"http://{host}:8080"
            else:
                logger.warning("RabbitMQ URI is not in expected format")
                return "http://localhost:8080"
        except (IndexError, ValueError):
            logger.warning("Failed to extract host from RabbitMQ URI, using default")
            return "http://localhost:8080"
    
    def _get_api_key(self) -> str:
        """Get the API key from environment variables or use default."""
        # TODO: Add API key to config and environment variables
        return "namastex888"  # Default key, should be from env
    
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
    
    def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming WhatsApp messages from RabbitMQ."""
        logger.debug(f"Received message: {message.get('event', 'unknown')}")
        
        # Pass the message to the message handler for processing
        message_handler.handle_message(message)
    
    def start(self) -> bool:
        """Start the WhatsApp client."""
        # Start the message handler
        message_handler.start()
        
        # Connect to RabbitMQ and start consuming messages
        if self.connect():
            try:
                logger.info("Starting to consume WhatsApp messages")
                self.client.start_consuming()
                return True
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                self.stop()
                return False
            except Exception as e:
                logger.error(f"Error while consuming messages: {e}")
                self.stop()
                return False
        else:
            return False
    
    def start_async(self) -> bool:
        """Start the WhatsApp client in a separate thread."""
        # Start the message handler
        message_handler.start()
        
        # Connect to RabbitMQ
        if self.connect():
            logger.info("Starting to consume WhatsApp messages asynchronously")
            thread = threading.Thread(target=self.client.start_consuming)
            thread.daemon = True
            thread.start()
            return True
        else:
            return False
    
    def stop(self):
        """Stop the WhatsApp client."""
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
        url = f"{self.api_base_url}/message/sendText/{config.rabbitmq.instance_name}"
        
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": recipient,
            "text": text
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Message sent to {recipient}")
            
            # Parse response data
            response_data = {
                "direction": "outbound",
                "status": "sent",
                "timestamp": datetime.now().isoformat(),
                "recipient": recipient,
                "text": text,
                "raw_response": response.json() if response.content else None
            }
            
            return True, response_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message: {e}")
            return False, None
    
    def send_media(self, recipient: str, media_url: str, caption: Optional[str] = None):
        """Send a media message via Evolution API.
        
        Returns:
            Tuple[bool, Optional[Dict]]: Success flag and response data if successful
        """
        url = f"{self.api_base_url}/message/sendMedia/{config.rabbitmq.instance_name}"
        
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": recipient,
            "mediaUrl": media_url
        }
        
        if caption:
            payload["caption"] = caption
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Media sent to {recipient}")
            
            # Parse response data
            response_data = {
                "direction": "outbound",
                "status": "sent",
                "timestamp": datetime.now().isoformat(),
                "recipient": recipient,
                "media_url": media_url,
                "caption": caption,
                "raw_response": response.json() if response.content else None
            }
            
            return True, response_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send media: {e}")
            return False, None

# Singleton instance
whatsapp_client = WhatsAppClient() 