"""
Audio transcription service for WhatsApp audio messages.
Uses the Evolution Transcript API to transcribe audio content.
"""

import logging
import json
import requests
import time
import uuid
import base64
from typing import Dict, Any, Optional
from datetime import datetime
import tempfile
import os

from src.config import config

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.audio_transcriber")

class AudioTranscriptionService:
    """Service for transcribing audio messages from Evolution API."""
    
    def __init__(self):
        """Initialize the audio transcription service."""
        self.api_url = config.evolution_transcript.api_url
        self.api_key = config.evolution_transcript.api_key
        
        # Get Minio URL from environment variable
        self.minio_url = os.getenv("EVOLUTION_MINIO_URL", "")
        if self.minio_url:
            logger.info(f"\033[96mUsing Minio URL from environment: {self.minio_url}\033[0m")
        
        # Validate required configuration is present
        if not self.api_url or not self.api_key:
            logger.warning("\033[93mAudio transcription service not fully configured. "
                         "EVOLUTION_TRANSCRIPT_API and EVOLUTION_TRANSCRIPT_API_KEY "
                         "must be set in environment variables.\033[0m")
    
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_url and self.api_key)
    
    def _truncate_url_for_logging(self, url: str, max_length: int = 60) -> str:
        """Truncate a URL for logging to reduce verbosity.
        
        Args:
            url: The URL to truncate
            max_length: Maximum length to display
            
        Returns:
            Truncated URL suitable for logging
        """
        if not url or len(url) <= max_length:
            return url
            
        # Parse the URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Get the host and path
            host = parsed.netloc
            path = parsed.path
            
            # Truncate the path if it's too long
            if len(path) > 30:
                path_parts = path.split('/')
                if len(path_parts) > 4:
                    # Keep first 2 and last part
                    short_path = '/'.join(path_parts[:2]) + '/.../' + path_parts[-1]
                else:
                    short_path = path[:15] + '...' + path[-15:]
            else:
                short_path = path
                
            # Format with just a hint of the query string
            query = parsed.query
            query_hint = '?' + query[:10] + '...' if query else ''
            
            return f"{parsed.scheme}://{host}{short_path}{query_hint}"
            
        except Exception:
            # If parsing fails, do a simple truncation
            return url[:30] + '...' + url[-30:]
    
    def _convert_minio_url(self, audio_url: str) -> str:
        """
        Convert internal minio URLs to use the configured external Minio URL.
        
        Args:
            audio_url: Original audio URL
            
        Returns:
            Converted URL using external Minio address if applicable
        """
        if not audio_url:
            return audio_url
            
        # If we have a configured minio URL and the audio URL contains minio:9000
        if self.minio_url and "minio:9000" in audio_url:
            # Extract the path and query string from the URL
            from urllib.parse import urlparse
            parsed = urlparse(audio_url)
            path_and_query = parsed.path
            if parsed.query:
                path_and_query += f"?{parsed.query}"
                
            # Create new URL with the external Minio address
            # Ensure we have a proper URL format with protocol
            if not self.minio_url.startswith(('http://', 'https://')):
                external_url = f"http://{self.minio_url.rstrip('/')}"
            else:
                external_url = self.minio_url.rstrip('/')
                
            converted_url = f"{external_url}{path_and_query}"
            logger.info(f"\033[96mConverted internal minio URL to external URL: {self._truncate_url_for_logging(converted_url)}\033[0m")
            return converted_url
            
        return audio_url
    
    def transcribe_audio(self, audio_url: str, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio from URL using Evolution Transcript API.
        
        Args:
            audio_url: URL of the audio file to transcribe
            language: Optional language code for transcription
            
        Returns:
            Optional[str]: Transcribed text or None if failed
        """
        if not self.is_configured():
            logger.error("\033[91mAudio transcription service not configured\033[0m")
            return None
            
        if not audio_url:
            logger.error("\033[91mNo audio URL provided for transcription\033[0m")
            return None
        
        try:
            # Convert internal minio URL to external URL if configured
            original_url = audio_url
            
            # Prepare API endpoint URL (don't modify this)
            api_url_str = str(self.api_url)
            url = f"{api_url_str.rstrip('/')}/transcribe"
            
            # Prepare headers with API key
            headers = {
                "apikey": self.api_key,
            }
            
            # Prepare payload as form data - don't modify the URL further, use it as is
            payload = {
                "url": audio_url
            }
            
            # Add optional language if provided
            if language:
                payload["language"] = language
            
            # Log the request (excluding sensitive data)
            request_info = {
                "url": self._truncate_url_for_logging(url),
                "headers": {
                    "apikey": "***hidden***"
                },
                "payload": {"url": self._truncate_url_for_logging(payload["url"])}
            }
            logger.info(f"\033[94mMaking transcription request: {json.dumps(request_info)}\033[0m")
            
            # Make API request with form data payload
            response = requests.post(
                url, 
                headers=headers,
                data=payload  # Use data parameter for form-encoded data
            )
            
            logger.info(f"\033[94mTranscription response status code: {response.status_code}\033[0m")
            
            # Try to log response content for debugging
            try:
                logger.info(f"Response content: {response.text[:200]}...")
            except Exception:
                logger.info("Could not log response content")
            
            # Check for successful response
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Extract transcription
            transcription = data.get("transcription", "")
            if not transcription:
                logger.warning("\033[93mNo transcription found in response\033[0m")
                return None
            
            logger.info("\033[92mSuccessfully extracted transcription\033[0m")
            return transcription
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Transcription API request failed: {str(e)}"
            logger.error(f"\033[91m{error_msg}\033[0m")
            return None
        except Exception as e:
            error_msg = f"Unexpected error during transcription: {str(e)}"
            logger.error(f"\033[91m{error_msg}\033[0m")
            return None
            
    def download_and_encode_audio(self, audio_url: str) -> Optional[str]:
        """
        Download audio file and encode as base64.
        
        Args:
            audio_url: URL of the audio file to download
            
        Returns:
            Optional[str]: Base64-encoded audio data or None if failed
        """
        original_url = audio_url
        try:
            # Don't modify the audio_url - keep it as is for the transcription service
            
            # Try using the original URL directly
            logger.info(f"\033[94mAttempting to download audio from URL: {self._truncate_url_for_logging(audio_url)}\033[0m")
            try:
                # Make request to download the file with a reasonable timeout
                response = requests.get(audio_url, timeout=30)
                response.raise_for_status()
                
                # Process the response
                return self._process_download_response(response)
            except Exception as e:
                logger.warning(f"\033[93mFailed to download from URL: {str(e)}\033[0m")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"\033[91mFailed to download audio file: {str(e)}\033[0m")
            return None
        except Exception as e:
            logger.error(f"\033[91mFailed to process audio file: {str(e)}\033[0m")
            return None
            
    def _process_download_response(self, response):
        """Helper method to process download response and create base64 encoding"""
        try:
            # Check content type to ensure it's audio
            content_type = response.headers.get('Content-Type', '')
            logger.info(f"\033[94mDownloaded file with Content-Type: {content_type}\033[0m")
            
            # Log file size for debugging
            file_size = len(response.content)
            logger.info(f"\033[94mDownloaded audio file size: {file_size} bytes\033[0m")
            
            if file_size == 0:
                logger.error("\033[91mDownloaded file is empty (0 bytes)\033[0m")
                return None
                
            # Get the content and encode it as base64
            audio_data = response.content
            base64_data = base64.b64encode(audio_data).decode('utf-8')
            
            logger.info(f"\033[92mSuccessfully downloaded and encoded audio file ({len(audio_data)} bytes)\033[0m")
            return base64_data
        except Exception as e:
            logger.error(f"\033[91mError processing download response: {str(e)}\033[0m")
            return None

    def transcribe_with_fallback(self, audio_url: str, language: Optional[str] = None) -> Optional[str]:
        """
        Try to transcribe using URL first, then fallback to downloading and base64 encoding if that fails.
        
        Args:
            audio_url: URL of the audio file to transcribe
            language: Optional language code for transcription
            
        Returns:
            Optional[str]: Transcribed text or None if all methods failed
        """
        # Don't modify the audio_url, pass it as-is to the transcription service
        
        # First try with URL approach
        logger.info("\033[94mAttempting to transcribe with URL method first\033[0m")
        result = self.transcribe_audio(audio_url, language)
        
        if result:
            logger.info("\033[92mSuccessfully transcribed audio using URL method\033[0m")
            return result
            
        # If URL approach fails, try downloading and sending base64
        logger.info("\033[93mURL method failed, trying with base64 approach\033[0m")
        audio_data = None
        try:
            audio_data_response = self.download_and_encode_audio(audio_url)
            if audio_data_response:
                base64_data = audio_data_response
                audio_data = base64.b64decode(base64_data)  # Save the raw data for multipart fallback
            else:
                logger.error("\033[91mFailed to download audio file for base64 encoding\033[0m")
                return None
        except Exception as e:
            logger.error(f"\033[91mError decoding base64 data: {str(e)}\033[0m")
            return None
        
        # Try base64 encoding approach
        logger.info("\033[94mAttempting base64 encoding approach\033[0m")
        result = self._try_base64_transcription(base64_data, language)
        if result:
            return result
        
        # If base64 approach fails, try multipart file upload
        if audio_data:
            logger.info("\033[94mBase64 approach failed, trying multipart file upload\033[0m")
            result = self._try_multipart_transcription(audio_data, language)
            if result:
                return result
        
        # All approaches failed
        logger.error("\033[91mAll transcription approaches failed\033[0m")
        return None

    def _try_base64_transcription(self, base64_data: str, language: Optional[str] = None) -> Optional[str]:
        """Try transcription using base64 approach"""
        try:
            logger.info(f"\033[94mAttempting transcription with base64 data (length: {len(base64_data)} chars)\033[0m")
            
            # Create payload with "base64" parameter
            payload = {"base64": base64_data}
            if language:
                payload["language"] = language
                
            # Prepare API endpoint URL
            api_url_str = str(self.api_url)
            api_endpoint = f"{api_url_str}/speech-to-text/transcribe"
            logger.info(f"\033[94mSending base64 transcription request to: {self._truncate_url_for_logging(api_endpoint)}\033[0m")
            
            # Make API call without Content-Type header (let requests determine it)
            response = requests.post(
                api_endpoint,
                data=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60
            )
            
            # Log response status
            logger.info(f"\033[94mBase64 transcription response status: {response.status_code}\033[0m")
            
            # Check if successful
            if response.status_code == 200:
                result = response.json()
                text = result.get("text")
                if text:
                    logger.info(f"\033[92mBase64 transcription successful: {text[:50]}{'...' if len(text) > 50 else ''}\033[0m")
                    return text
                else:
                    logger.warning("\033[93mBase64 transcription response didn't contain text field\033[0m")
            else:
                # Log error details
                logger.error(f"\033[91mBase64 transcription failed with status {response.status_code}\033[0m")
                try:
                    error_content = response.json()
                    logger.error(f"\033[91mError response: {error_content}\033[0m")
                except Exception:
                    logger.error(f"\033[91mError response content: {response.text[:200]}\033[0m")
                    
            return None
        except Exception as e:
            logger.error(f"\033[91mError during base64 transcription: {str(e)}\033[0m")
            return None
            
    def _try_multipart_transcription(self, audio_data: bytes, language: Optional[str] = None) -> Optional[str]:
        """Try transcription using multipart file upload approach"""
        try:
            logger.info(f"\033[94mAttempting transcription with multipart file upload (size: {len(audio_data)} bytes)\033[0m")
            
            # Create a temporary file to hold the audio data
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)
                
            try:
                # Create multipart form data
                files = {'file': ('audio.ogg', open(temp_path, 'rb'), 'audio/ogg')}
                
                # Add language if provided
                data = {}
                if language:
                    data["language"] = language
                
                # Prepare API endpoint URL
                api_url_str = str(self.api_url)
                api_endpoint = f"{api_url_str}/speech-to-text/transcribe"
                logger.info(f"\033[94mSending multipart transcription request to: {self._truncate_url_for_logging(api_endpoint)}\033[0m")
                
                # Make API call
                response = requests.post(
                    api_endpoint,
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60
                )
                
                # Log response status
                logger.info(f"\033[94mMultipart transcription response status: {response.status_code}\033[0m")
                
                # Check if successful
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text")
                    if text:
                        logger.info(f"\033[92mMultipart transcription successful: {text[:50]}{'...' if len(text) > 50 else ''}\033[0m")
                        return text
                    else:
                        logger.warning("\033[93mMultipart transcription response didn't contain text field\033[0m")
                else:
                    # Log error details
                    logger.error(f"\033[91mMultipart transcription failed with status {response.status_code}\033[0m")
                    try:
                        error_content = response.json()
                        logger.error(f"\033[91mError response: {error_content}\033[0m")
                    except Exception:
                        logger.error(f"\033[91mError response content: {response.text[:200]}\033[0m")
                        
                return None
            finally:
                # Clean up the temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            logger.error(f"\033[91mError during multipart transcription: {str(e)}\033[0m")
            return None 