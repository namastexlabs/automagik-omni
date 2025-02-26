"""
WhatsApp client using Evolution API and RabbitMQ.
"""

import logging
import json
import requests
from typing import Dict, Any, Optional, List
import threading
from datetime import datetime
import time
import os
import mimetypes
from urllib.parse import urlparse
import boto3
from botocore.client import Config
import aiohttp
import pika

from src.evolution_api_client import EvolutionAPIClient, RabbitMQConfig, EventType
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
                # Determine protocol based on config
                protocol = "https" if os.getenv("API_USE_HTTPS", "").lower() == "true" else "http"
                return f"{protocol}://{host}:8080"
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
        try:
            logger.info(f"📱 Received WhatsApp message: {message.get('event', 'unknown')}")
            
            # Verify that the message has the expected structure
            if not message:
                logger.warning("Received empty message")
                return
                
            # For debugging, log more information about the message structure
            if 'event' in message:
                logger.info(f"📱 Message event type: {message['event']}")
            
            if 'data' in message:
                data = message['data']
                # Log key information for debugging
                if 'key' in data:
                    key = data['key']
                    logger.info(f"📱 Message ID: {key.get('id', 'unknown')} from JID: {key.get('remoteJid', 'unknown')}")
                
                # Check if the actual message content exists
                if 'message' in data:
                    logger.info(f"📱 Message content type: {self.detect_message_type(message)}")
                else:
                    logger.warning("📱 Message doesn't contain 'message' field")
            else:
                logger.warning("📱 Message doesn't contain 'data' field")
                logger.info(f"📱 Message structure: {list(message.keys())}")
            
            # Process media if present
            message_type = self.detect_message_type(message)
            if message_type in ['image', 'audio', 'video', 'sticker', 'document']:
                logger.info(f"📱 Processing incoming {message_type} message")
            
            # Pass the message to the message handler for processing
            logger.info("📱 Passing message to handler for processing")
            message_handler.handle_message(message)
            
        except Exception as e:
            logger.error(f"Error handling WhatsApp message: {e}", exc_info=True)
    
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
            
            # Print diagnostics about the queue
            self._check_queue_status()
            
            # Start periodic queue check thread
            self._start_queue_monitor()
            
            # Start the consumer thread with reconnection capability
            self._start_consumer_with_reconnect()
            return True
        else:
            return False
            
    def _check_queue_status(self):
        """Check and log the status of the RabbitMQ queue for diagnostic purposes."""
        try:
            if self.client.channel and self.client.connection and self.client.connection.is_open:
                # Get queue info
                queue_info = self.client.channel.queue_declare(queue=self.client.queue_name, passive=True)
                message_count = queue_info.method.message_count
                consumer_count = queue_info.method.consumer_count
                
                logger.info(f"🔍 Queue '{self.client.queue_name}' status:")
                logger.info(f"🔍   - Message count: {message_count}")
                logger.info(f"🔍   - Consumer count: {consumer_count}")
                logger.info(f"🔍   - Exchange: {self.client.config.exchange_name}")
                
                # List bindings
                bindings = []
                
                # Instance-specific bindings
                for event in self.client.config.events:
                    bindings.append(f"{self.client.config.instance_name}.{event}")
                
                # Catch-all binding
                bindings.append(f"{self.client.config.instance_name}.*")
                
                logger.info(f"🔍   - Queue bindings: {bindings}")
                
                # Check if rabbitmq connection is using SSL
                is_ssl = "amqps://" in config.rabbitmq.uri
                logger.info(f"🔍   - Connection using SSL: {is_ssl}")
                
                # Check connection state
                logger.info(f"🔍   - Connection is open: {self.client.connection.is_open}")
                logger.info(f"🔍   - Channel is open: {self.client.channel.is_open}")
                
                # Send a test message only occasionally (every 5 minutes) to reduce connection stress
                # We'll use the current timestamp to determine this
                current_time = int(time.time())
                should_send_test = (current_time % 300) < 30  # Only in the first 30 seconds of every 5 minutes
                
                # Send a test message to ourselves if no messages in queue and it's time to do so
                if message_count == 0 and consumer_count > 0 and should_send_test:
                    logger.info("🔍 No messages in queue, sending test message to check routing...")
                    try:
                        self._publish_test_message()
                    except Exception as e:
                        logger.error(f"Failed to publish test message: {e}", exc_info=True)
            else:
                logger.warning("🔍 Cannot check queue status - no active connection to RabbitMQ")
                # Try to reconnect
                self.connect()
        except Exception as e:
            logger.error(f"🔍 Failed to check queue status: {e}", exc_info=True)
            
    def _publish_test_message(self):
        """Publish a test message to the exchange to verify routing."""
        try:
            if not self.client.channel or not self.client.connection or not self.client.connection.is_open:
                logger.warning("Cannot publish test message - no active connection")
                return
                
            # Verify channel is still open
            if not self.client.channel.is_open:
                logger.warning("Channel is closed, cannot send test message")
                return
                
            # Create a test message
            test_message = {
                "event": "messages.upsert",
                "instance": self.client.config.instance_name,
                "data": {
                    "key": {
                        "id": f"test-{int(time.time())}",
                        "remoteJid": "test@s.whatsapp.net"
                    },
                    "message": {
                        "conversation": "This is a test message from the system"
                    }
                },
                "is_test": True
            }
            
            # Convert to JSON
            message_body = json.dumps(test_message).encode('utf-8')
            
            # Publish to the exchange with the correct routing key
            routing_key = f"{self.client.config.instance_name}.messages.upsert"
            
            # Use a try-except block specifically for the publish operation
            try:
                self.client.channel.basic_publish(
                    exchange=self.client.config.exchange_name,
                    routing_key=routing_key,
                    body=message_body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # make message persistent
                        content_type='application/json'
                    )
                )
                logger.info(f"🔍 Published test message to exchange {self.client.config.exchange_name} with routing key {routing_key}")
            except pika.exceptions.ChannelClosed as e:
                logger.warning(f"Channel closed while trying to publish test message: {e}")
            except pika.exceptions.ConnectionClosed as e:
                logger.warning(f"Connection closed while trying to publish test message: {e}")
            except pika.exceptions.AMQPError as e:
                logger.warning(f"AMQP error while trying to publish test message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in _publish_test_message: {e}", exc_info=True)
            # Don't re-raise the exception to prevent thread crashes
    
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
    
    def detect_message_type(self, message: Dict[str, Any]) -> str:
        """Detect the message type from the message data.
        
        Args:
            message: The message data
            
        Returns:
            str: The message type ('text', 'image', 'audio', 'video', 'sticker', etc.)
        """
        # Extract message content
        data = message.get('data', {})
        message_content = data.get('message', {})
        
        # Check for specific message types
        if 'conversation' in message_content or 'extendedTextMessage' in message_content:
            return 'text'
        elif 'imageMessage' in message_content:
            return 'image'
        elif 'audioMessage' in message_content:
            return 'audio'
        elif 'videoMessage' in message_content:
            return 'video'
        elif 'stickerMessage' in message_content:
            return 'sticker'
        elif 'documentMessage' in message_content:
            return 'document'
        
        # Try to get from messageType field
        if 'messageType' in data:
            return data.get('messageType')
        
        # Default to unknown
        return 'unknown'
    
    def extract_media_url(self, message: Dict[str, Any]) -> Optional[str]:
        """Extract media URL from a message.
        
        Args:
            message: The message data
            
        Returns:
            Optional[str]: The media URL or None if not found
        """
        # Extract message content
        data = message.get('data', {})
        message_content = data.get('message', {})
        
        # Check for direct mediaUrl in data
        if 'mediaUrl' in data:
            url = data.get('mediaUrl')
            # If it's a generic WhatsApp URL, we'll handle it differently
            if url != "https://web.whatsapp.net":
                return self._convert_minio_to_public_url(url)
        
        # Check for specific message types
        if 'imageMessage' in message_content and 'url' in message_content['imageMessage']:
            return message_content['imageMessage']['url']
        elif 'audioMessage' in message_content and 'url' in message_content['audioMessage']:
            return message_content['audioMessage']['url']
        elif 'videoMessage' in message_content and 'url' in message_content['videoMessage']:
            return message_content['videoMessage']['url']
        elif 'stickerMessage' in message_content:
            # For stickers, first try to get the URL
            if 'url' in message_content['stickerMessage']:
                return message_content['stickerMessage']['url']
            # Otherwise, we'll just return a placeholder and let download_and_save_media construct the real URL
            return "https://web.whatsapp.net"
        elif 'documentMessage' in message_content and 'url' in message_content['documentMessage']:
            return message_content['documentMessage']['url']
        
        return None
    
    def _convert_minio_to_public_url(self, url: str) -> str:
        """Convert Minio internal URL to public-facing URL.
        
        Args:
            url: The internal Minio URL
            
        Returns:
            str: The public-facing URL
        """
        if not url:
            return url
            
        # If the URL is already a public URL, return as is
        if url.startswith("https://mmg.whatsapp.net") or url.startswith("https://web.whatsapp.net"):
            return url
            
        # Check if this is a MinIO URL (either internal or IP-based)
        is_minio_url = "minio:9000" in url or config.minio.endpoint in url
        
        if is_minio_url:
            # Extract the path from the URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            
            # Get the path component
            path = parsed_url.path
            
            # Format: /bucket_name/path/to/object
            # We need to extract the path after bucket name
            parts = path.split('/', 2)  # Split into ['', 'bucket_name', 'rest/of/path']
            
            if len(parts) >= 3:
                # Bucket name is parts[1], rest of path is parts[2]
                bucket_name = parts[1]
                object_path = parts[2]
                
                # Construct the public URL using the configured public URL
                public_url = f"{config.public_media_url}/media/{object_path}"
                
                # Remove query parameters if they exist
                if '?' in public_url:
                    public_url = public_url.split('?')[0]
                
                logger.info(f"Converted MinIO URL to public URL: {public_url}")
                return public_url
            else:
                logger.warning(f"Could not extract path components from MinIO URL: {url}")
        
        # If we couldn't convert it, return the original URL
        return url
    
    def send_media(self, recipient: str, media_url: str, caption: Optional[str] = None, media_type: str = 'image'):
        """Send a media message via Evolution API.
        
        Args:
            recipient: WhatsApp ID of the recipient
            media_url: URL of the media file
            caption: Optional caption for the media
            media_type: Type of media ('image', 'audio', 'video', 'document', 'sticker')
            
        Returns:
            Tuple[bool, Optional[Dict]]: Success flag and response data if successful
        """
        # Convert Minio URLs to public URLs if needed
        media_url = self._convert_minio_to_public_url(media_url)
        
        # Determine the appropriate endpoint based on media type
        if media_type == 'audio':
            endpoint = 'sendAudio'
        elif media_type == 'video':
            endpoint = 'sendVideo'
        elif media_type == 'document':
            endpoint = 'sendDocument'
        elif media_type == 'sticker':
            endpoint = 'sendSticker'
        else:
            # Default to sendMedia for images and other types
            endpoint = 'sendMedia'
        
        url = f"{self.api_base_url}/message/{endpoint}/{config.rabbitmq.instance_name}"
        
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "number": recipient,
            "mediaUrl": media_url
        }
        
        if caption and media_type != 'audio' and media_type != 'sticker':
            payload["caption"] = caption
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"{media_type.capitalize()} sent to {recipient}")
            
            # Parse response data
            response_data = {
                "direction": "outbound",
                "status": "sent",
                "timestamp": datetime.now().isoformat(),
                "recipient": recipient,
                "media_url": media_url,
                "media_type": media_type,
                "caption": caption,
                "raw_response": response.json() if response.content else None
            }
            
            return True, response_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send {media_type}: {e}")
            return False, None

    async def download_and_save_media(self, message: dict) -> str:
        """Download and save media to S3
        
        Args:
            message: The WhatsApp message containing media
            
        Returns:
            str: The URL to the media
        """
        message_id = message.get("id", "")
        remote_jid = message.get("key", {}).get("remoteJid", "")
        message_type = message.get("message", {}).get("messageStubType", "")
        
        # Determine the media URL - it could be in various places depending on message type
        media_url = None
        extension = ".enc"  # Default for WhatsApp encrypted media
        content_type = "application/octet-stream"  # Default content type
        
        # Extract media details based on message type
        if "imageMessage" in message.get("message", {}):
            logger.info("Message contains image")
            media_url = message.get("message", {}).get("imageMessage", {}).get("url", "")
            if not media_url:
                media_url = message.get("message", {}).get("imageMessage", {}).get("directPath", "")
            extension = ".jpg"
            content_type = "image/jpeg"
            message_type = "image"
            
        elif "videoMessage" in message.get("message", {}):
            logger.info("Message contains video")
            media_url = message.get("message", {}).get("videoMessage", {}).get("url", "")
            if not media_url:
                media_url = message.get("message", {}).get("videoMessage", {}).get("directPath", "")
            extension = ".mp4"
            content_type = "video/mp4"
            message_type = "video"
            
        elif "audioMessage" in message.get("message", {}):
            logger.info("Message contains audio")
            media_url = message.get("message", {}).get("audioMessage", {}).get("url", "")
            if not media_url:
                media_url = message.get("message", {}).get("audioMessage", {}).get("directPath", "")
            extension = ".ogg"
            content_type = "audio/ogg"
            message_type = "audio"
            
        elif "documentMessage" in message.get("message", {}):
            logger.info("Message contains document")
            media_url = message.get("message", {}).get("documentMessage", {}).get("url", "")
            if not media_url:
                media_url = message.get("message", {}).get("documentMessage", {}).get("directPath", "")
            # Try to get mime type and extension from document message
            mime = message.get("message", {}).get("documentMessage", {}).get("mimetype", "")
            if mime:
                content_type = mime
                # Extract extension from mimetype
                if "/" in mime:
                    potential_ext = mime.split("/")[-1]
                    if potential_ext:
                        extension = f".{potential_ext}"
            message_type = "document"
            
        elif "stickerMessage" in message.get("message", {}):
            logger.info("Message contains sticker")
            media_url = message.get("message", {}).get("stickerMessage", {}).get("url", "")
            if not media_url:
                media_url = message.get("message", {}).get("stickerMessage", {}).get("directPath", "")
            extension = ".webp"
            content_type = "image/webp"
            message_type = "sticker"
        
        logger.info(f"Media URL: {media_url}")
        
        if not media_url:
            logger.warning("No media URL found in the message")
            return ""
        
        # Check if we're dealing with a MinIO URL vs a WhatsApp URL
        if "minio:9000" in media_url or config.minio.endpoint in media_url:
            logger.info("Media URL is a MinIO URL, attempting to download from S3")
            try:
                # Extract the path after minio:9000 or the endpoint
                from urllib.parse import urlparse
                parsed_url = urlparse(media_url)
                path_parts = parsed_url.path.split('/', 2)
                
                if len(path_parts) < 3:
                    raise ValueError(f"Invalid MinIO URL format: {media_url}")
                    
                bucket = path_parts[1]
                key = path_parts[2]
                
                # Set up S3 client
                s3_client = boto3.client(
                    's3',
                    endpoint_url=f"{'https' if config.minio.use_https else 'http'}://{config.minio.endpoint}:{config.minio.port}",
                    aws_access_key_id=config.minio.access_key,
                    aws_secret_access_key=config.minio.secret_key,
                    region_name='us-east-1'
                )
                
                # Create a temporary file to download to
                temp_file_path = f"/tmp/{message_id}{extension}"
                
                # Download the file from S3
                s3_client.download_file(bucket, key, temp_file_path)
                
                # Check if file was actually downloaded and has content
                if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
                    logger.error(f"Failed to download file from S3 or file is empty: {temp_file_path}")
                    return ""
                
                logger.info(f"Successfully downloaded file from S3: {temp_file_path}")
                
                # Return the public URL to the media
                return self._convert_minio_to_public_url(media_url)
                
            except Exception as e:
                logger.error(f"Error downloading from S3: {e}")
                return ""
        
        # This is a WhatsApp URL, so we need to download and upload to S3
        try:
            # Get the download URL and auth token
            api_url = await self._get_api_base_url()
            download_url = f"{api_url}/download"
            headers = {
                "Origin": api_url,
                "X-API-Key": config.api_key,  # API key if needed
            }
            
            # Prepare the payload
            payload = {
                "url": media_url,
                "remoteJid": remote_jid,
                "directPath": message.get("directPath", ""),
                "type": "url"
            }
            
            # Download the media
            temp_file_path = f"/tmp/{message_id}{extension}"
            
            logger.info(f"Downloading media from: {download_url} with payload {payload}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(download_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to download media: {response.status} - {error_text}")
                        return ""
                    
                    # Save the file
                    with open(temp_file_path, "wb") as f:
                        f.write(await response.read())
            
            # Verify file downloaded successfully
            if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
                logger.error(f"Failed to download file or file is empty: {temp_file_path}")
                return ""
                
            logger.info(f"Downloaded media to: {temp_file_path} ({os.path.getsize(temp_file_path)} bytes)")
            
            # Upload to S3
            s3_key = f"evolution-api/{config.rabbitmq.instance_name}/{remote_jid}/{message_type}/{message_id}{extension}"
            bucket = config.minio.bucket
            
            logger.info(f"Uploading media to S3: endpoint={config.minio.endpoint}:{config.minio.port}, bucket={bucket}, key={s3_key}")
            logger.info(f"Using access key: {config.minio.access_key[:4]}... with content type: {content_type}")
            
            s3_client = boto3.client(
                's3',
                endpoint_url=f"{'https' if config.minio.use_https else 'http'}://{config.minio.endpoint}:{config.minio.port}",
                aws_access_key_id=config.minio.access_key,
                aws_secret_access_key=config.minio.secret_key,
                region_name='us-east-1'
            )
            
            # Upload the file with the appropriate content type
            s3_client.upload_file(
                temp_file_path, 
                bucket, 
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'
                }
            )
            
            # Clean up the temp file
            os.remove(temp_file_path)
            
            # Return URL to the uploaded media
            s3_url = f"http://{config.minio.endpoint}:{config.minio.port}/{bucket}/{s3_key}"
            public_url = self._convert_minio_to_public_url(s3_url)
            
            logger.info(f"Uploaded media to S3: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error downloading and saving media: {e}")
            # Clean up temp file if it exists
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return ""

    async def process_incoming_media(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process media in incoming messages.
        
        This function checks for media content and downloads it to S3 if needed.
        
        Args:
            message: The message to process
            
        Returns:
            The message with media URLs updated
        """
        if not message or 'data' not in message:
            return message
            
        data = message.get('data', {})
        message_type = self.detect_message_type(data)
        
        if message_type in ['image', 'video', 'audio', 'document', 'sticker']:
            logger.info(f"Processing {message_type} media in message")
            
            # Download and save media to S3
            media_url = await self.download_and_save_media(data)
            
            if media_url:
                logger.info(f"Media saved to: {media_url}")
                # Update the media URL in the message
                if message_type == 'image' and 'imageMessage' in data.get('message', {}):
                    data['message']['imageMessage']['url'] = media_url
                elif message_type == 'video' and 'videoMessage' in data.get('message', {}):
                    data['message']['videoMessage']['url'] = media_url
                elif message_type == 'audio' and 'audioMessage' in data.get('message', {}):
                    data['message']['audioMessage']['url'] = media_url
                elif message_type == 'document' and 'documentMessage' in data.get('message', {}):
                    data['message']['documentMessage']['url'] = media_url
                elif message_type == 'sticker' and 'stickerMessage' in data.get('message', {}):
                    data['message']['stickerMessage']['url'] = media_url
            else:
                logger.warning(f"Failed to download and save {message_type} media")
                
        # Return the potentially modified message
        return message

    def should_process_message(self, message: Dict[str, Any]) -> bool:
        """Check if we should process this message type."""
        # Skip empty messages or messages without data
        if not message or 'data' not in message:
            return False
            
        # Skip status messages
        if message.get('event') == 'status.update':
            return False
            
        # Get message data
        data = message.get('data', {})
        
        # Skip messages without a key (usually status updates)
        if 'key' not in data:
            return False
            
        # Skip messages without actual message content
        if 'message' not in data:
            return False
            
        return True
        
    def extract_message_content(self, message: Dict[str, Any]) -> str:
        """Extract the text content from a message."""
        data = message.get('data', {})
        message_content = data.get('message', {})
        
        # Check for different types of text content
        if 'conversation' in message_content:
            return message_content.get('conversation', '')
        elif 'extendedTextMessage' in message_content:
            return message_content.get('extendedTextMessage', {}).get('text', '')
        elif 'imageMessage' in message_content:
            return message_content.get('imageMessage', {}).get('caption', '')
        elif 'videoMessage' in message_content:
            return message_content.get('videoMessage', {}).get('caption', '')
        elif 'documentMessage' in message_content:
            return message_content.get('documentMessage', {}).get('fileName', '')
            
        # If no text content found
        return ""
        
    async def update_state(self, message_data: Dict[str, Any]) -> None:
        """Update the internal state with message data.
        
        This method is a placeholder that would be used to update
        any internal state like conversation context, etc.
        
        Args:
            message_data: Processed message data
        """
        # For now, just log the message data
        logger.debug(f"Updating state with message: {message_data['id']}")
        # In a real implementation, this would update conversation context
        # or trigger further processing

    def _start_queue_monitor(self):
        """Start a thread to periodically check the queue status."""
        def monitor_queue():
            """Periodically check queue status."""
            while True:
                try:
                    time.sleep(30)  # Check every 30 seconds
                    
                    # Check if connection is still alive
                    if not self.client.connection or not self.client.connection.is_open:
                        logger.warning("RabbitMQ connection is closed in monitor thread")
                        # Try to reconnect
                        self._handle_reconnection()
                    else:
                        # Check queue status
                        self._check_queue_status()
                        
                except Exception as e:
                    logger.error(f"Error in queue monitor: {e}", exc_info=True)
                    # Don't try to reconnect here since _check_queue_status will handle it
        
        # Start the monitoring thread
        monitor_thread = threading.Thread(target=monitor_queue)
        monitor_thread.daemon = True
        monitor_thread.start()
        logger.info("Started queue monitoring thread")

    def _start_consumer_with_reconnect(self):
        """Start the consumer thread with automatic reconnection."""
        def consume_with_reconnect():
            """Consumer function with reconnection logic."""
            while True:
                try:
                    logger.info("Starting to consume messages from RabbitMQ")
                    self.client.start_consuming()
                except pika.exceptions.StreamLostError as e:
                    logger.error(f"Connection to RabbitMQ lost: {e}", exc_info=True)
                    self._handle_reconnection()
                except pika.exceptions.ConnectionClosed as e:
                    logger.error(f"Connection to RabbitMQ closed: {e}", exc_info=True)
                    self._handle_reconnection()
                except pika.exceptions.AMQPConnectionError as e:
                    logger.error(f"AMQP Connection error: {e}", exc_info=True)
                    self._handle_reconnection()
                except Exception as e:
                    logger.error(f"Unexpected error in consumer thread: {e}", exc_info=True)
                    self._handle_reconnection()
        
        # Start the consumer thread
        thread = threading.Thread(target=consume_with_reconnect)
        thread.daemon = True
        thread.start()
        logger.info("Started consumer thread with automatic reconnection")
        
    def _handle_reconnection(self):
        """Handle reconnection to RabbitMQ after connection loss."""
        # Wait before attempting to reconnect
        reconnect_delay = 5  # seconds
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            logger.info(f"Waiting {reconnect_delay} seconds before attempting to reconnect (attempt {retry_count + 1}/{max_retries})")
            time.sleep(reconnect_delay)
            
            try:
                # Close the old connection if it exists
                if self.client.connection and self.client.connection.is_open:
                    try:
                        self.client.connection.close()
                    except Exception:
                        pass
                
                # Reset the client
                self.client.connection = None
                self.client.channel = None
                
                # Try to reconnect
                logger.info("Attempting to reconnect to RabbitMQ")
                if self.connect():
                    logger.info("Successfully reconnected to RabbitMQ")
                    return True
            except Exception as e:
                logger.error(f"Error during reconnection attempt: {e}", exc_info=True)
            
            # Increment retry count and increase delay (exponential backoff)
            retry_count += 1
            reconnect_delay = min(reconnect_delay * 1.5, 60)  # Cap at 60 seconds
        
        logger.error(f"Failed to reconnect after {max_retries} attempts")
        return False

# Singleton instance
whatsapp_client = WhatsAppClient() 