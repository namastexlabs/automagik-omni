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
            events=[EventType.MESSAGES_UPSERT],
            # Add explicit connection settings
            heartbeat=30,
            connection_attempts=3,
            retry_delay=5
        )
        
        self.client = EvolutionAPIClient(self.evolution_config)
        self.api_base_url = self._get_api_base_url()
        self.api_key = self._get_api_key()
        
        # Set up message handler to use our send_text_message method
        message_handler.set_send_response_callback(self.send_text_message)
        
        # Connection monitoring
        self._connection_monitor_thread = None
        self._should_monitor = False
    
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
        logger.debug(f"Received message: {message.get('event', 'unknown')}")
        
        # Process media if present
        message_type = self.detect_message_type(message)
        if message_type in ['image', 'audio', 'video', 'sticker', 'document']:
            logger.info(f"Processing incoming {message_type} message")
            message = self.process_incoming_media(message)
        
        # Pass the message to the message handler for processing
        message_handler.handle_message(message)
    
    def _monitor_connection(self):
        """Monitor the RabbitMQ connection and reconnect if needed."""
        logger.info("Starting RabbitMQ connection monitor")
        
        while self._should_monitor:
            try:
                # Check if the connection is still open
                if not self.client.connection or not self.client.connection.is_open:
                    logger.warning("RabbitMQ connection lost. Attempting to reconnect...")
                    if self.client.reconnect():
                        # Re-subscribe to messages after reconnecting
                        self.client.subscribe(EventType.MESSAGES_UPSERT, self._handle_message)
                        logger.info("Successfully reconnected and resubscribed to WhatsApp messages")
                    else:
                        logger.error("Failed to reconnect to RabbitMQ")
                        
                # Wait before checking again
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}", exc_info=True)
                time.sleep(60)  # Wait longer after an error
    
    def start(self) -> bool:
        """Start the WhatsApp client."""
        # Start the message handler
        message_handler.start()
        
        # Connect to RabbitMQ and start consuming messages
        if self.connect():
            # Start connection monitor
            self._should_monitor = True
            self._connection_monitor_thread = threading.Thread(target=self._monitor_connection)
            self._connection_monitor_thread.daemon = True
            self._connection_monitor_thread.start()
            
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
            
            # Start connection monitor
            self._should_monitor = True
            self._connection_monitor_thread = threading.Thread(target=self._monitor_connection)
            self._connection_monitor_thread.daemon = True
            self._connection_monitor_thread.start()
            
            # Start consuming in a separate thread
            thread = threading.Thread(target=self.client.start_consuming)
            thread.daemon = True
            thread.start()
            
            return True
        else:
            return False
    
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
                    queue_info = self.client.channel.queue_declare(queue=queue_name, passive=True)
                    message_count = queue_info.method.message_count
                    consumer_count = queue_info.method.consumer_count
                    
                    logger.info(f"Queue '{queue_name}' exists with {message_count} messages and {consumer_count} consumers")
                except Exception as e:
                    logger.warning(f"Queue '{queue_name}' does not exist or cannot be accessed: {e}")
        
        except Exception as e:
            logger.error(f"Error checking queue status: {e}", exc_info=True)
    
    def stop(self):
        """Stop the WhatsApp client."""
        # Stop connection monitoring
        self._should_monitor = False
        if self._connection_monitor_thread and self._connection_monitor_thread.is_alive():
            self._connection_monitor_thread.join(timeout=5.0)
        
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
            
        # If the URL is a S3/MinIO URL, try to create a presigned URL
        if "minio:9000" in url or config.minio.endpoint in url:
            try:
                # Extract bucket and key from the MinIO URL
                # Format: http://minio:9000/evolution/evolution-api/{instance}/{remotejid}/{type}/{id}.{ext}
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.split('/', 2)
                
                if len(path_parts) >= 3:
                    bucket = path_parts[1]  # evolution
                    key = path_parts[2]  # rest of the path
                    
                    # Create a new S3 client with the configured credentials
                    s3_client = boto3.client(
                        's3',
                        endpoint_url=f"{'https' if config.minio.use_https else 'http'}://{config.minio.endpoint}:{config.minio.port}",
                        aws_access_key_id=config.minio.access_key,
                        aws_secret_access_key=config.minio.secret_key,
                        config=Config(signature_version='s3v4'),
                        region_name=config.minio.region
                    )
                    
                    # Create a presigned URL that expires in 7 days
                    presigned_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=604800  # 7 days in seconds
                    )
                    
                    logger.info(f"Created presigned URL for MinIO object: {presigned_url}")
                    return presigned_url
            except Exception as e:
                logger.error(f"Failed to create presigned URL for MinIO object: {e}")
                
                # Fallback to the direct public URL approach
                server_url = config.public_media_url
                
                # Extract path - handle both "minio:9000" and actual endpoint formats
                if "minio:9000" in url:
                    path_parts = url.split('minio:9000', 1)[1]
                else:
                    # Handle when actual endpoint is in URL
                    endpoint_with_port = f"{config.minio.endpoint}:{config.minio.port}"
                    path_parts = url.split(endpoint_with_port, 1)[1] if endpoint_with_port in url else url
                
                public_url = f"{server_url}/media{path_parts}"
                if '?' in public_url:
                    public_url = public_url.split('?')[0]
                logger.info(f"Using direct public URL: {public_url}")
                return public_url
                
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

    def download_and_save_media(self, message: Dict[str, Any]) -> Optional[str]:
        """Download and save media (stickers, images, etc.) from WhatsApp messages to MinIO.
        
        Args:
            message: The WhatsApp message data
            
        Returns:
            Optional[str]: The public URL of the saved media or None if failed
        """
        # First determine the message type and extract the media URL
        message_type = self.detect_message_type(message)
        media_url = self.extract_media_url(message)
        
        if not media_url:
            logger.warning(f"No media URL found in {message_type} message")
            return None
            
        # Check for specific case of stickers with non-working URL
        if message_type == 'sticker' and (media_url == 'https://web.whatsapp.net' or not media_url.startswith('http')):
            # Try to construct a working URL for stickers
            try:
                data = message.get('data', {})
                message_content = data.get('message', {})
                sticker_message = message_content.get('stickerMessage', {})
                
                # Extract direct path which contains the actual file path
                direct_path = sticker_message.get('directPath')
                
                if direct_path:
                    # Construct a proper WhatsApp download URL
                    media_url = f"https://mmg.whatsapp.net{direct_path}"
                    logger.info(f"Constructed sticker download URL: {media_url}")
                else:
                    logger.warning("Could not extract directPath from sticker message")
                    return None
            except Exception as e:
                logger.error(f"Error constructing sticker URL: {e}")
                return None
        
        # Check if this is a WhatsApp URL or already a Minio URL
        if media_url.startswith("https://mmg.whatsapp.net") or media_url.startswith("https://web.whatsapp.net") or "minio:9000" in media_url:
            try:
                # Extract necessary information
                data = message.get('data', {})
                key = data.get('key', {})
                
                # Get remote JID (sender/recipient)
                remote_jid = key.get('remoteJid', 'unknown')
                if '@' in remote_jid:
                    remote_jid = remote_jid.split('@')[0]  # Remove the @s.whatsapp.net part
                
                # Get message ID
                message_id = key.get('id', f"manual_{int(time.time())}")
                
                # Create a temporary file to store the media
                temp_dir = os.path.join(os.getcwd(), 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                
                # Determine file extension from mime type or URL
                message_content = data.get('message', {})
                mime_type = None
                
                # Try to get mime type from the message content based on media type
                if message_type == 'image':
                    mime_type = message_content.get('imageMessage', {}).get('mimetype')
                elif message_type == 'audio':
                    mime_type = message_content.get('audioMessage', {}).get('mimetype')
                elif message_type == 'video':
                    mime_type = message_content.get('videoMessage', {}).get('mimetype')
                elif message_type == 'sticker':
                    mime_type = message_content.get('stickerMessage', {}).get('mimetype', 'image/webp')
                elif message_type == 'document':
                    mime_type = message_content.get('documentMessage', {}).get('mimetype')
                
                # Default to webp for stickers if no mime type
                if not mime_type and message_type == 'sticker':
                    mime_type = 'image/webp'
                
                # Get extension from mime type
                extension = mimetypes.guess_extension(mime_type) if mime_type else ''
                if not extension:
                    # Try to get extension from URL
                    parsed_url = urlparse(media_url)
                    path = parsed_url.path
                    extension = os.path.splitext(path)[1]
                    
                # If still no extension, use default based on type
                if not extension:
                    if message_type == 'image':
                        extension = '.jpg'
                    elif message_type == 'audio':
                        extension = '.mp3'
                    elif message_type == 'video':
                        extension = '.mp4'
                    elif message_type == 'sticker':
                        extension = '.webp'
                    else:
                        extension = '.bin'
                
                # Create a temporary file path
                temp_file_path = os.path.join(temp_dir, f"{message_id}{extension}")
                
                # Download the file
                if "minio:9000" in media_url or config.minio.endpoint in media_url:
                    # This is an internal URL, we need to use the S3 client
                    s3_client = boto3.client('s3',
                        endpoint_url=f"{'https' if config.minio.use_https else 'http'}://{config.minio.endpoint}:{config.minio.port}",
                        aws_access_key_id=config.minio.access_key,
                        aws_secret_access_key=config.minio.secret_key,
                        config=Config(signature_version='s3v4'),
                        region_name=config.minio.region
                    )
                    
                    # Parse the URL to get bucket and key
                    parsed_url = urlparse(media_url)
                    path_parts = parsed_url.path.split('/', 2)
                    if len(path_parts) >= 3:
                        bucket = path_parts[1]  # evolution
                        key = path_parts[2]  # rest of the path
                        
                        # Download the file from S3
                        logger.info(f"Downloading from S3: bucket={bucket}, key={key}")
                        s3_client.download_file(bucket, key, temp_file_path)
                    else:
                        logger.error(f"Invalid MinIO URL format: {media_url}")
                        return None
                else:
                    # Special handling for stickers
                    if message_type == 'sticker':
                        headers = {}
                        # For stickers, we might need special headers
                        if 'mmg.whatsapp.net' in media_url:
                            headers = {
                                'User-Agent': 'WhatsApp/2.23.24.82 A',
                                'Accept': '*/*'
                            }
                        
                        # Log the download attempt for stickers
                        logger.info(f"Attempting to download sticker from: {media_url}")
                        
                        # Direct download with special headers for stickers
                        response = requests.get(media_url, headers=headers, stream=True)
                    else:
                        # Regular download for other media types
                        response = requests.get(media_url, stream=True)
                    
                    # Check status
                    if response.status_code != 200:
                        logger.error(f"Failed to download media, status code: {response.status_code}")
                        logger.error(f"Response: {response.text[:200]}")
                        return None
                    
                    # Save to file
                    response.raise_for_status()
                    with open(temp_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                
                logger.info(f"Media downloaded to {temp_file_path}")
                
                # Upload to MinIO
                s3_client = boto3.client('s3',
                    endpoint_url=f"{'https' if config.minio.use_https else 'http'}://{config.minio.endpoint}:{config.minio.port}",
                    aws_access_key_id=config.minio.access_key,
                    aws_secret_access_key=config.minio.secret_key,
                    config=Config(signature_version='s3v4'),
                    region_name=config.minio.region
                )
                
                # Define the S3 key (path in the bucket)
                s3_key = f"evolution-api/{config.rabbitmq.instance_name}/{remote_jid}/{message_type}/{message_id}{extension}"
                bucket = config.minio.bucket
                
                # Log upload details for troubleshooting
                logger.info(f"Uploading media to S3: endpoint={config.minio.endpoint}:{config.minio.port}, bucket={bucket}, key={s3_key}")
                logger.info(f"Using access key: {config.minio.access_key[:4]}...")
                
                # Upload the file
                s3_client.upload_file(
                    temp_file_path, 
                    bucket,
                    s3_key,
                    ExtraArgs={
                        'ContentType': mime_type,
                        'ACL': 'public-read'  # Set ACL to public-read to make it publicly accessible
                    } if mime_type else {'ACL': 'public-read'}
                )
                
                logger.info(f"Media uploaded to S3: bucket={bucket}, key={s3_key}")
                
                # Create a presigned URL that expires in 7 days
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': s3_key},
                    ExpiresIn=604800  # 7 days in seconds
                )
                
                logger.info(f"Created presigned URL for media: {presigned_url}")
                
                # Clean up the temporary file
                os.remove(temp_file_path)
                
                return presigned_url
                
            except Exception as e:
                logger.error(f"Error downloading and saving media: {e}", exc_info=True)
                return None
        return media_url

    def process_incoming_media(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming media messages to ensure they are saved to MinIO.
        
        Args:
            message: The WhatsApp message
            
        Returns:
            Dict[str, Any]: The updated message with saved media URL
        """
        # Only process if it's a media message
        message_type = self.detect_message_type(message)
        if message_type in ['image', 'audio', 'video', 'sticker', 'document']:
            # Check if we need to save the media
            media_url = self.extract_media_url(message)
            
            if media_url:
                # Special handling for stickers (always save them)
                if message_type == 'sticker' or not media_url.startswith("http://minio:9000"):
                    # Download and save to MinIO
                    saved_url = self.download_and_save_media(message)
                    
                    if saved_url:
                        # Update the message with the new URL
                        data = message.get('data', {})
                        
                        # Add mediaUrl to the data
                        data['mediaUrl'] = saved_url
                        
                        # Update the message content based on the type
                        message_content = data.get('message', {})
                        if message_type == 'image' and 'imageMessage' in message_content:
                            message_content['imageMessage']['url'] = saved_url
                        elif message_type == 'audio' and 'audioMessage' in message_content:
                            message_content['audioMessage']['url'] = saved_url
                        elif message_type == 'video' and 'videoMessage' in message_content:
                            message_content['videoMessage']['url'] = saved_url
                        elif message_type == 'sticker' and 'stickerMessage' in message_content:
                            message_content['stickerMessage']['url'] = saved_url
                        elif message_type == 'document' and 'documentMessage' in message_content:
                            message_content['documentMessage']['url'] = saved_url
                        
                        # Update the message data
                        data['message'] = message_content
                        message['data'] = data
                        
                        logger.info(f"Updated {message_type} message with saved media URL: {saved_url}")
        
        return message

# Singleton instance
whatsapp_client = WhatsAppClient() 