"""
WhatsApp client using Evolution API and RabbitMQ.
"""

import logging
import json
import requests
from typing import Dict, Any, Optional, List, Union
import threading
from datetime import datetime
import time
import os
import mimetypes
from urllib.parse import urlparse
import boto3
from botocore.client import Config
import base64
import tempfile

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
        
        # Initialize the temp directory to ensure it exists
        self._ensure_temp_directory()
        
        # Log using the actual URI instead of constructing it from parts
        logger.info(f"Connecting to Evolution API RabbitMQ at {config.rabbitmq.uri}")
        logger.info(f"Using WhatsApp instance: {self.evolution_config.instance_name}")
    
    def _ensure_temp_directory(self):
        """Ensure the temporary directory exists and has proper permissions."""
        temp_dir = os.path.join(os.getcwd(), 'temp')
        try:
            # Create the directory if it doesn't exist
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
                logger.info(f"Created temporary directory at {temp_dir}")
            
            # Check if the directory is writable
            test_file_path = os.path.join(temp_dir, '_test_write.tmp')
            with open(test_file_path, 'w') as f:
                f.write('test')
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
        message_type = self.detect_message_type(message)
        
        # Skip sticker messages as requested
        if message_type == 'sticker':
            logger.info("Skipping URL extraction for sticker message")
            return None
        
        # Check for direct mediaUrl in data - prioritize this as it may be already processed
        if 'mediaUrl' in data:
            url = data.get('mediaUrl')
            # If it's a generic WhatsApp URL, we'll handle it differently
            if url and url != "https://web.whatsapp.net":
                # Don't convert internal URLs here - that's handled in process_incoming_media
                return url
        
        # Check for specific message types
        if 'imageMessage' in message_content and 'url' in message_content['imageMessage']:
            return message_content['imageMessage']['url']
        elif 'audioMessage' in message_content and 'url' in message_content['audioMessage']:
            return message_content['audioMessage']['url']
        elif 'videoMessage' in message_content and 'url' in message_content['videoMessage']:
            return message_content['videoMessage']['url']
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
                    
                    # Create a presigned URL that expires in 1 hour
                    presigned_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=3600  # 1 hour in seconds
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

    def download_and_save_media(self, message: Dict[str, Any], base64_encode: bool = False) -> Optional[str]:
        """Download and save media (stickers, images, etc.) from WhatsApp messages to MinIO.
        
        Args:
            message: The WhatsApp message data
            base64_encode: Whether to also provide the media as base64 (added to the message)
            
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
                
                # Ensure we have a proper temp directory
                temp_dir = self._ensure_temp_directory()
                
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
                extension = self._get_extension_from_mime_type(mime_type) if mime_type else ''
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
                
                # If base64 encoding is requested, encode the file and add to message
                if base64_encode:
                    try:
                        # Read the file and convert to base64
                        with open(temp_file_path, 'rb') as f:
                            file_content = f.read()
                            base64_data = base64.b64encode(file_content).decode('utf-8')
                        
                        # Add base64 data to the message
                        if 'data' in message:
                            message['data']['media_base64'] = base64_data
                            logger.info("Added base64 encoded media to message")
                    except Exception as e:
                        logger.error(f"Error encoding media as base64: {e}")
                
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
                
                # If mime_type is empty or None, try to detect it from the file
                if not mime_type:
                    detected_mime = self._detect_mime_type_from_file(temp_file_path)
                    if detected_mime:
                        mime_type = detected_mime
                        logger.info(f"Detected MIME type from file content: {mime_type}")
                    else:
                        # Fall back to guessing from extension
                        mime_type = mimetypes.guess_type(temp_file_path)[0]
                        logger.info(f"Guessed MIME type from extension: {mime_type}")
                
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
                
                # Create a presigned URL that expires in 1 hour instead of 7 days
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': s3_key},
                    ExpiresIn=3600  # 1 hour in seconds
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
        """Process incoming media messages to ensure they have valid URLs.
        
        Args:
            message: The WhatsApp message
            
        Returns:
            Dict[str, Any]: The updated message
        """
        # Only process if it's a media message
        message_type = self.detect_message_type(message)
        
        # Skip sticker messages as requested
        if message_type == 'sticker':
            logger.info(f"Skipping sticker message as requested")
            return message
            
        if message_type in ['image', 'audio', 'video', 'document']:
            logger.info(f"Processing incoming {message_type} message")
            
            # Extract media URL directly from the message
            media_url = self.extract_media_url(message)
            
            if media_url:
                # Use the direct URL from Evolution API
                # Only convert internal MinIO URLs to public URLs if needed
                if "minio:9000" in media_url:
                    public_url = self._convert_minio_to_public_url(media_url)
                    
                    if public_url:
                        # Update the message with the new URL
                        data = message.get('data', {})
                        
                        # Add mediaUrl to the data
                        data['mediaUrl'] = public_url
                        
                        # Update the message
                        message['data'] = data
                        
                        logger.info(f"Updated {message_type} message with public URL: {public_url}")
        
        return message

    def _get_media_as_base64(self, media_url: str) -> Optional[str]:
        """Download media from URL and convert to base64 encoding.
        
        Args:
            media_url: URL of the media to download
            
        Returns:
            Optional[str]: Base64 encoded media string or None if failed
        """
        try:
            # Create a temporary file in a reliable temp directory
            temp_dir = self._ensure_temp_directory()
            temp_path = os.path.join(temp_dir, f"base64_tmp_{int(time.time())}.bin")
            
            # Check if this is a MinIO URL
            if "minio:9000" in media_url or config.minio.endpoint in media_url:
                # Parse the URL to get bucket and key
                parsed_url = urlparse(media_url)
                path_parts = parsed_url.path.split('/', 2)
                
                if len(path_parts) >= 3:
                    bucket = path_parts[1]
                    key = path_parts[2]
                    
                    # Create S3 client
                    s3_client = boto3.client('s3',
                        endpoint_url=f"{'https' if config.minio.use_https else 'http'}://{config.minio.endpoint}:{config.minio.port}",
                        aws_access_key_id=config.minio.access_key,
                        aws_secret_access_key=config.minio.secret_key,
                        config=Config(signature_version='s3v4'),
                        region_name=config.minio.region
                    )
                    
                    # Download file
                    s3_client.download_file(bucket, key, temp_path)
                else:
                    logger.error(f"Invalid MinIO URL format: {media_url}")
                    return None
            else:
                # Regular HTTP download
                response = requests.get(media_url, stream=True)
                response.raise_for_status()
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            # Read the file and convert to base64
            with open(temp_path, 'rb') as f:
                file_content = f.read()
                base64_data = base64.b64encode(file_content).decode('utf-8')
            
            # Clean up
            os.remove(temp_path)
            
            return base64_data
            
        except Exception as e:
            logger.error(f"Error converting media to base64: {e}", exc_info=True)
            # Attempt to clean up if possible
            try:
                if 'temp_path' in locals():
                    os.remove(temp_path)
            except:
                pass
            return None

    def get_media_as_base64(self, message_or_url: Union[Dict[str, Any], str]) -> Optional[str]:
        """Retrieve base64 encoded media from a message or media URL.
        
        Args:
            message_or_url: The message or direct media URL
            
        Returns:
            Optional[str]: Base64 encoded media or None if failed
        """
        # Check if we already have base64 encoded data in the message
        if isinstance(message_or_url, dict) and 'data' in message_or_url and 'media_base64' in message_or_url['data']:
            return message_or_url['data']['media_base64']
        
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
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'image/svg+xml': '.svg',
            'image/heic': '.heic',
            'image/heif': '.heif',
            # Audio types
            'audio/mpeg': '.mp3',
            'audio/mp4': '.m4a',
            'audio/ogg': '.ogg',
            'audio/wav': '.wav',
            'audio/webm': '.webm',
            'audio/aac': '.aac',
            'audio/opus': '.opus',
            # Video types
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'video/ogg': '.ogv',
            'video/quicktime': '.mov',
            'video/x-matroska': '.mkv',
            'video/x-msvideo': '.avi',
            # Document types
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx'
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
        if mime_type.startswith('image/'):
            return '.jpg'
        elif mime_type.startswith('audio/'):
            return '.mp3'
        elif mime_type.startswith('video/'):
            return '.mp4'
        elif mime_type.startswith('text/'):
            return '.txt'
        else:
            return '.bin'

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
                with open(file_path, 'rb') as f:
                    header = f.read(12)  # Read first 12 bytes for file signature
                
                # Check file signatures
                if header.startswith(b'\xFF\xD8\xFF'):  # JPEG starts with these bytes
                    return 'image/jpeg'
                elif header.startswith(b'\x89PNG\r\n\x1A\n'):  # PNG signature
                    return 'image/png'
                elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):  # GIF signature
                    return 'image/gif'
                elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':  # WEBP signature
                    return 'image/webp'
                elif header.startswith(b'\x42\x4D'):  # BMP signature
                    return 'image/bmp'
                
                # If signature detection fails, fall back to extension-based detection
                ext = os.path.splitext(file_path)[1].lower()
                mime_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp',
                    '.bmp': 'image/bmp',
                    '.mp3': 'audio/mpeg',
                    '.mp4': 'video/mp4',
                    '.pdf': 'application/pdf',
                }
                return mime_map.get(ext, '')
        except Exception as e:
            logger.error(f"Error detecting MIME type: {e}")
            return ''

# Singleton instance
whatsapp_client = WhatsAppClient() 