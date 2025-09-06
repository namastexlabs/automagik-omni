"""
Audio transcription service for WhatsApp audio messages.
Uses the Evolution Transcript API to transcribe audio content.
"""

import logging
import json
import requests
import base64
from typing import Optional
import tempfile
import os

from src.channels.whatsapp.whatsapp_media_decrypt import whatsapp_media_decryptor

# Configure logging
logger = logging.getLogger("src.channels.whatsapp.audio_transcriber")


class AudioTranscriptionService:
    """Service for transcribing audio messages from Evolution API."""

    def __init__(self):
        """Initialize the audio transcription service."""
        # Audio transcription is currently disabled
        # This service is kept for backward compatibility but not actively used
        self.api_url = ""
        self.api_key = ""

        logger.debug("Audio transcription service initialized (currently disabled)")

    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        # Always return False since transcription is disabled
        return False

    def transcribe_encrypted_audio(
        self, encrypted_url: str, media_key_b64: str
    ) -> Optional[str]:
        """
        Transcribe encrypted WhatsApp audio by first decrypting it.

        Args:
            encrypted_url: URL to the encrypted .enc audio file
            media_key_b64: Base64 encoded media key from WhatsApp

        Returns:
            Optional[str]: Transcribed text or None if failed
        """
        try:
            logger.info("🔓 Starting decryption and transcription of encrypted audio")

            # Decrypt the audio using the WhatsApp media decryptor
            decrypted_temp_path = whatsapp_media_decryptor.decrypt_and_save_temp(
                encrypted_url=encrypted_url,
                media_key_b64=media_key_b64,
                media_type=whatsapp_media_decryptor.MEDIA_TYPE_AUDIO,
            )

            if not decrypted_temp_path:
                logger.error("❌ Failed to decrypt WhatsApp audio file")
                return None

            try:
                logger.info(
                    f"✅ Successfully decrypted audio to: {decrypted_temp_path}"
                )

                # Now transcribe the decrypted audio file using multipart upload
                transcription = self._transcribe_multipart_upload(decrypted_temp_path)

                if transcription:
                    logger.info(
                        f"🎯 Successfully transcribed decrypted WhatsApp audio: {transcription}"
                    )
                    return transcription
                else:
                    logger.error("❌ Failed to transcribe decrypted audio")
                    return None

            finally:
                # Clean up the temporary decrypted file
                try:
                    if os.path.exists(decrypted_temp_path):
                        os.unlink(decrypted_temp_path)
                        logger.info(
                            f"🗑️ Cleaned up temporary decrypted file: {decrypted_temp_path}"
                        )
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Failed to clean up temp file: {cleanup_error}")

        except Exception as e:
            logger.error(
                f"❌ Error during encrypted audio transcription: {e}", exc_info=True
            )
            return None

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
                path_parts = path.split("/")
                if len(path_parts) > 4:
                    # Keep first 2 and last part
                    short_path = "/".join(path_parts[:2]) + "/.../" + path_parts[-1]
                else:
                    short_path = path[:15] + "..." + path[-15:]
            else:
                short_path = path

            # Format with just a hint of the query string
            query = parsed.query
            query_hint = "?" + query[:10] + "..." if query else ""

            return f"{parsed.scheme}://{host}{short_path}{query_hint}"

        except Exception:
            # If parsing fails, do a simple truncation
            return url[:30] + "..." + url[-30:]

    def _convert_minio_url(self, audio_url: str) -> str:
        """
        Convert internal Minio URL to external URL if configured.

        Args:
            audio_url: Original audio URL

        Returns:
            str: Converted URL or original if no conversion needed
        """
        if "minio:9000" in audio_url:
            # Replace the Docker container hostname with localhost or host IP
            # Since we're running on the VM but Minio is in Docker
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(audio_url)

            # Create a new netloc with localhost and the same port
            # This assumes the Minio port is mapped to the same port on the host
            new_netloc = "localhost:9000"

            # Reconstruct the URL with the new hostname but same path and query
            converted_url = urlunparse(
                (
                    parsed.scheme,
                    new_netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )

            logger.info(
                f"\033[96mConverted Docker container URL to host URL: {self._truncate_url_for_logging(converted_url)}\033[0m"
            )
            return converted_url

        return audio_url

    def transcribe_audio(
        self, audio_url: str, language: Optional[str] = None
    ) -> Optional[str]:
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
            # Use the configured API URL and key from environment variables
            url = f"{self.api_url.rstrip('/')}/transcribe"
            api_key = self.api_key

            logger.info(
                f"Using configured transcription API: {self._truncate_url_for_logging(url)}"
            )

            # Prepare headers with API key
            headers = {
                "apikey": api_key,
            }

            # Prepare payload as form data
            payload = {"url": audio_url}

            # Add optional language if provided
            if language:
                payload["language"] = language

            # Log the request (excluding sensitive data)
            request_info = {
                "url": url,
                "headers": {"apikey": "***hidden***"},
                "payload": {"url": self._truncate_url_for_logging(payload["url"])},
            }
            logger.info(
                f"\033[94mMaking transcription request: {json.dumps(request_info)}\033[0m"
            )

            # Make API request with form data payload
            response = requests.post(
                url,
                headers=headers,
                data=payload,  # Use data parameter for form-encoded data
                timeout=30,
            )

            logger.info(
                f"\033[94mTranscription response status code: {response.status_code}\033[0m"
            )

            # Try to log response content for debugging
            try:
                logger.info(f"Response content: {response.text[:500]}...")
            except Exception:
                logger.info("Could not log response content")

            # Check for successful response
            if response.status_code == 200:
                try:
                    result = response.json()
                    # Look for text in the response
                    if isinstance(result, dict):
                        text = (
                            result.get("text")
                            or result.get("transcription")
                            or result.get("result")
                        )
                        if text:
                            logger.info(
                                f"\033[92mTranscription successful: {text[:100]}{'...' if len(text) > 100 else ''}\033[0m"
                            )
                            return text
                        else:
                            logger.warning(
                                f"\033[93mTranscription response didn't contain expected text field. Response: {result}\033[0m"
                            )
                    else:
                        # If response is a string, use it directly
                        if isinstance(result, str) and result.strip():
                            logger.info(
                                f"\033[92mTranscription successful: {result[:100]}{'...' if len(result) > 100 else ''}\033[0m"
                            )
                            return result.strip()

                except json.JSONDecodeError:
                    # If it's not JSON, check if it's plain text
                    text = response.text.strip()
                    if text and not text.startswith('{"error"'):
                        logger.info(
                            f"\033[92mTranscription successful (plain text): {text[:100]}{'...' if len(text) > 100 else ''}\033[0m"
                        )
                        return text

            # If we get here, transcription failed
            try:
                error_response = response.json()
                error_msg = error_response.get("error", "Unknown error")
                logger.error(f"\033[91mTranscription failed: {error_msg}\033[0m")
            except json.JSONDecodeError:
                logger.error(
                    f"\033[91mTranscription failed with status {response.status_code}: {response.text[:200]}\033[0m"
                )

            # Raise the exception to trigger fallback
            response.raise_for_status()
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"\033[91mTranscription API request failed: {str(e)}\033[0m")
            return None
        except Exception as e:
            logger.error(f"\033[91mError during transcription: {str(e)}\033[0m")
            return None

    def download_and_encode_audio(self, audio_url: str) -> Optional[str]:
        """
        Download audio file and encode as base64.

        Args:
            audio_url: URL of the audio file to download

        Returns:
            Optional[str]: Base64-encoded audio data or None if failed
        """
        try:
            # Don't modify the audio_url - keep it as is for the transcription service

            # Try using the original URL directly
            logger.info(
                f"\033[94mAttempting to download audio from URL: {self._truncate_url_for_logging(audio_url)}\033[0m"
            )
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
            content_type = response.headers.get("Content-Type", "")
            logger.info(
                f"\033[94mDownloaded file with Content-Type: {content_type}\033[0m"
            )

            # Log file size for debugging
            file_size = len(response.content)
            logger.info(f"\033[94mDownloaded audio file size: {file_size} bytes\033[0m")

            if file_size == 0:
                logger.error("\033[91mDownloaded file is empty (0 bytes)\033[0m")
                return None

            # Get the content and encode it as base64
            audio_data = response.content
            base64_data = base64.b64encode(audio_data).decode("utf-8")

            logger.info(
                f"\033[92mSuccessfully downloaded and encoded audio file ({len(audio_data)} bytes)\033[0m"
            )
            return base64_data
        except Exception as e:
            logger.error(f"\033[91mError processing download response: {str(e)}\033[0m")
            return None

    def transcribe_with_fallback(
        self, audio_url: str, language: Optional[str] = None
    ) -> Optional[str]:
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
            logger.info(
                "\033[92mSuccessfully transcribed audio using URL method\033[0m"
            )
            return result

        # If URL approach fails, try downloading and sending base64
        logger.info("\033[93mURL method failed, trying with base64 approach\033[0m")
        audio_data = None
        try:
            audio_data_response = self.download_and_encode_audio(audio_url)
            if audio_data_response:
                base64_data = audio_data_response
                audio_data = base64.b64decode(
                    base64_data
                )  # Save the raw data for multipart fallback
            else:
                logger.error(
                    "\033[91mFailed to download audio file for base64 encoding\033[0m"
                )
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
            logger.info(
                "\033[94mBase64 approach failed, trying multipart file upload\033[0m"
            )
            result = self._try_multipart_transcription(audio_data, language)
            if result:
                return result

        # All approaches failed
        logger.error("\033[91mAll transcription approaches failed\033[0m")
        return None

    def _try_base64_transcription(
        self, base64_data: str, language: Optional[str] = None
    ) -> Optional[str]:
        """Try transcription using base64 approach"""
        try:
            logger.info(
                f"\033[94mAttempting transcription with base64 data (length: {len(base64_data)} chars)\033[0m"
            )

            # Use the configured API URL and key from environment variables
            url = f"{self.api_url.rstrip('/')}/transcribe"
            api_key = self.api_key

            logger.info(
                f"Using configured transcription API for base64: {self._truncate_url_for_logging(url)}"
            )

            # Create payload with "base64" parameter instead of "url"
            payload = {"base64": base64_data}
            if language:
                payload["language"] = language

            # Use the same headers structure as the main method
            headers = {
                "apikey": api_key,
            }

            logger.info(
                f"\033[94mSending base64 transcription request to: {self._truncate_url_for_logging(url)}\033[0m"
            )

            # Make API call with form data payload (same as main method)
            response = requests.post(
                url,
                headers=headers,
                data=payload,  # Use data parameter for form-encoded data
                timeout=60,
            )

            # Log response status
            logger.info(
                f"\033[94mBase64 transcription response status: {response.status_code}\033[0m"
            )

            # Try to log response content for debugging
            try:
                logger.info(f"Base64 response content: {response.text[:200]}...")
            except Exception:
                logger.info("Could not log base64 response content")

            # Check if successful
            if response.status_code == 200:
                try:
                    result = response.json()
                    # Look for text in various possible fields
                    text = (
                        result.get("text")
                        or result.get("transcription")
                        or result.get("result")
                    )
                    if text:
                        logger.info(
                            f"\033[92mBase64 transcription successful: {text[:50]}{'...' if len(text) > 50 else ''}\033[0m"
                        )
                        return text
                    else:
                        logger.warning(
                            f"\033[93mBase64 transcription response didn't contain text field: {result}\033[0m"
                        )
                except json.JSONDecodeError:
                    # Try plain text response
                    text = response.text.strip()
                    if text and not text.startswith('{"error"'):
                        logger.info(
                            f"\033[92mBase64 transcription successful (plain text): {text[:50]}{'...' if len(text) > 50 else ''}\033[0m"
                        )
                        return text
            else:
                # Log error details
                logger.error(
                    f"\033[91mBase64 transcription failed with status {response.status_code}\033[0m"
                )
                try:
                    error_content = response.json()
                    logger.error(f"\033[91mError response: {error_content}\033[0m")
                except Exception:
                    logger.error(
                        f"\033[91mError response content: {response.text[:200]}\033[0m"
                    )

            return None
        except Exception as e:
            logger.error(f"\033[91mError during base64 transcription: {str(e)}\033[0m")
            return None

    def _try_multipart_transcription(
        self, audio_data: bytes, language: Optional[str] = None
    ) -> Optional[str]:
        """Try transcription using multipart file upload approach"""
        try:
            logger.info(
                f"\033[94mAttempting transcription with multipart file upload (size: {len(audio_data)} bytes)\033[0m"
            )

            # Use the configured API URL and key from environment variables
            url = f"{self.api_url.rstrip('/')}/transcribe"
            api_key = self.api_key

            logger.info(
                f"Using configured transcription API for multipart: {self._truncate_url_for_logging(url)}"
            )

            # Create a temporary file to hold the audio data
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(audio_data)

            try:
                # Create multipart form data - use "file" parameter instead of "url"
                files = {"file": ("audio.ogg", open(temp_path, "rb"), "audio/ogg")}

                # Add language if provided
                data = {}
                if language:
                    data["language"] = language

                # Use the same headers structure as the main method
                headers = {
                    "apikey": api_key,
                }

                logger.info(
                    f"\033[94mSending multipart transcription request to: {self._truncate_url_for_logging(url)}\033[0m"
                )

                # Make API call
                response = requests.post(
                    url, files=files, data=data, headers=headers, timeout=60
                )

                # Log response status
                logger.info(
                    f"\033[94mMultipart transcription response status: {response.status_code}\033[0m"
                )

                # Try to log response content for debugging
                try:
                    logger.info(f"Multipart response content: {response.text[:200]}...")
                except Exception:
                    logger.info("Could not log multipart response content")

                # Check if successful
                if response.status_code == 200:
                    try:
                        result = response.json()
                        # Look for text in various possible fields
                        text = (
                            result.get("text")
                            or result.get("transcription")
                            or result.get("result")
                        )
                        if text:
                            logger.info(
                                f"\033[92mMultipart transcription successful: {text[:50]}{'...' if len(text) > 50 else ''}\033[0m"
                            )
                            return text
                        else:
                            logger.warning(
                                f"\033[93mMultipart transcription response didn't contain text field: {result}\033[0m"
                            )
                    except json.JSONDecodeError:
                        # Try plain text response
                        text = response.text.strip()
                        if text and not text.startswith('{"error"'):
                            logger.info(
                                f"\033[92mMultipart transcription successful (plain text): {text[:50]}{'...' if len(text) > 50 else ''}\033[0m"
                            )
                            return text
                else:
                    # Log error details
                    logger.error(
                        f"\033[91mMultipart transcription failed with status {response.status_code}\033[0m"
                    )
                    try:
                        error_content = response.json()
                        logger.error(f"\033[91mError response: {error_content}\033[0m")
                    except Exception:
                        logger.error(
                            f"\033[91mError response content: {response.text[:200]}\033[0m"
                        )

                return None
            finally:
                # Clean up the temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

                # Clean up the file handle
                try:
                    if "files" in locals() and files:
                        for file_obj in files.values():
                            if hasattr(file_obj, "close"):
                                file_obj.close()
                            elif isinstance(file_obj, tuple) and len(file_obj) >= 2:
                                # file_obj is (filename, file_handle, content_type)
                                file_handle = file_obj[1]
                                if hasattr(file_handle, "close"):
                                    file_handle.close()
                except Exception as e:
                    logger.debug(f"Error closing file handle: {e}")

        except Exception as e:
            logger.error(
                f"\033[91mError during multipart transcription: {str(e)}\033[0m"
            )
            return None
