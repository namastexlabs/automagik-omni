"""
Media Download Service

Downloads and stores media files from omni_messages for processing.
Handles WhatsApp encrypted media, direct URLs, and URL expiration re-fetch.

Features:
- Local file storage with organized directory structure
- SHA256 deduplication to avoid re-downloading same files
- WhatsApp encrypted media decryption
- URL expiration handling with Evolution API re-fetch
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import requests

from sqlalchemy.orm import Session as SQLAlchemySession

from src.db.trace_models import OmniMessageRecord
from src.channels.whatsapp.whatsapp_media_decrypt import whatsapp_media_decryptor, WhatsAppMediaDecryptor
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)

# Default media cache path - uses project-local storage
# Can be overridden via MEDIA_CACHE_PATH environment variable or constructor param
DEFAULT_MEDIA_CACHE_PATH = os.environ.get("MEDIA_CACHE_PATH", "/tmp/omni/media_cache")

# Media type mapping for decryption
MEDIA_TYPE_MAP = {
    "image": WhatsAppMediaDecryptor.MEDIA_TYPE_IMAGE,
    "sticker": WhatsAppMediaDecryptor.MEDIA_TYPE_IMAGE,  # Stickers use same encryption as images
    "video": WhatsAppMediaDecryptor.MEDIA_TYPE_VIDEO,
    "audio": WhatsAppMediaDecryptor.MEDIA_TYPE_AUDIO,
    "document": WhatsAppMediaDecryptor.MEDIA_TYPE_DOCUMENT,
}

# File extension mapping
MIME_TO_EXT = {
    # Audio
    "audio/ogg": ".ogg",
    "audio/ogg; codecs=opus": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    # Image
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    # Video
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/3gpp": ".3gp",
    # Document
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/plain": ".txt",
}


class MediaDownloadService:
    """
    Service for downloading and storing media files from omni_messages.

    Supports:
    - Direct URL downloads (Discord, Evolution processed media)
    - Encrypted WhatsApp media decryption
    - SHA256 deduplication
    - URL expiration handling
    """

    def __init__(self, db: SQLAlchemySession, media_cache_path: Optional[str] = None):
        """
        Initialize the media download service.

        Args:
            db: Database session
            media_cache_path: Path for storing downloaded media files
        """
        self.db = db
        self.media_cache_path = Path(media_cache_path or DEFAULT_MEDIA_CACHE_PATH)

        # Ensure base directory exists
        self.media_cache_path.mkdir(parents=True, exist_ok=True)

    def _resolve_media_url(self, message: OmniMessageRecord) -> Optional[str]:
        """
        Resolve the actual media URL for a message.

        WhatsApp sometimes stores placeholder URLs (like https://web.whatsapp.net)
        with the actual path in the raw content's directPath field.

        Returns:
            The resolved media URL or None if not resolvable
        """
        url = message.media_url

        # Check if URL is a placeholder that needs resolution
        if url and ("web.whatsapp.net" in url or url == "https://web.whatsapp.net"):
            # Try to get directPath from raw content
            content_raw = message.get_content_raw()
            if content_raw:
                # Look for directPath in various message type structures
                direct_path = None
                for key in [
                    "stickerMessage",
                    "imageMessage",
                    "audioMessage",
                    "videoMessage",
                    "documentMessage",
                    "message",
                ]:
                    msg_content = content_raw.get(key, {})
                    if isinstance(msg_content, dict):
                        direct_path = msg_content.get("directPath")
                        if direct_path:
                            break
                        # Also check nested message structure
                        for nested_key in ["stickerMessage", "imageMessage", "audioMessage"]:
                            nested = msg_content.get(nested_key, {})
                            if isinstance(nested, dict) and nested.get("directPath"):
                                direct_path = nested.get("directPath")
                                break

                if direct_path:
                    # Construct full URL from directPath
                    resolved_url = f"https://mmg.whatsapp.net{direct_path}"
                    logger.info(f"Resolved placeholder URL to: {resolved_url[:60]}...")
                    return resolved_url

            logger.warning(f"Could not resolve placeholder URL for message {message.platform_message_id}")
            return None

        return url

    def _get_storage_path(self, message: OmniMessageRecord) -> Path:
        """
        Generate storage path for a media file.

        Format: /data/media/{instance}/{year}/{month}/{message_id}.{ext}
        """
        # Get timestamp for directory structure
        msg_time = message.message_timestamp or datetime_utcnow()
        year = msg_time.strftime("%Y")
        month = msg_time.strftime("%m")

        # Get file extension from mime type
        ext = self._get_extension(message.media_mime_type)

        # Create path
        dir_path = self.media_cache_path / message.instance_name / year / month
        dir_path.mkdir(parents=True, exist_ok=True)

        file_name = f"{message.platform_message_id}{ext}"
        return dir_path / file_name

    def _get_extension(self, mime_type: Optional[str]) -> str:
        """Get file extension from MIME type."""
        if not mime_type:
            return ".bin"

        # Handle MIME types with parameters (e.g., "audio/ogg; codecs=opus")
        base_mime = mime_type.split(";")[0].strip()

        # First check the full mime type with params
        if mime_type in MIME_TO_EXT:
            return MIME_TO_EXT[mime_type]

        # Then check just the base type
        return MIME_TO_EXT.get(base_mime, ".bin")

    def _check_sha256_exists(self, sha256: str) -> Optional[str]:
        """
        Check if a file with the given SHA256 already exists.

        Returns the path if found, None otherwise.
        """
        if not sha256:
            return None

        # Query for existing message with same SHA256 and downloaded media
        existing = (
            self.db.query(OmniMessageRecord)
            .filter(OmniMessageRecord.media_sha256 == sha256)
            .filter(OmniMessageRecord.media_local_path.isnot(None))
            .filter(OmniMessageRecord.media_status == "downloaded")
            .first()
        )

        if existing and existing.media_local_path:
            # Verify file still exists
            if Path(existing.media_local_path).exists():
                return existing.media_local_path

        return None

    def _download_direct_url(self, url: str, output_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Download media from a direct URL.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            logger.info(f"Downloading media from: {url[:60]}...")

            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()

            # Write to file
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = output_path.stat().st_size
            logger.info(f"Downloaded media: {file_size} bytes -> {output_path}")

            return True, None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False, "URL expired or not found (404)"
            return False, f"HTTP error: {e}"
        except Exception as e:
            return False, f"Download error: {e}"

    def _download_encrypted_whatsapp(
        self, url: str, media_key: str, media_type: str, output_path: Path
    ) -> Tuple[bool, Optional[str]]:
        """
        Download and decrypt WhatsApp encrypted media.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get decryption media type
            decrypt_type = MEDIA_TYPE_MAP.get(media_type, WhatsAppMediaDecryptor.MEDIA_TYPE_DOCUMENT)

            logger.info(f"Decrypting WhatsApp {media_type} media...")

            # Use the existing decryptor
            decrypted_data = whatsapp_media_decryptor.decrypt_media(url, media_key, decrypt_type)

            if not decrypted_data:
                return False, "Decryption failed"

            # Write to file
            with open(output_path, "wb") as f:
                f.write(decrypted_data)

            file_size = output_path.stat().st_size
            logger.info(f"Decrypted WhatsApp media: {file_size} bytes -> {output_path}")

            return True, None

        except Exception as e:
            return False, f"Decryption error: {e}"

    def _refetch_via_evolution_api(self, message: OmniMessageRecord, output_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Re-fetch expired media via Evolution API's getBase64FromMediaMessage.

        This is a fallback for synced messages with expired URLs/keys.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            import base64

            logger.info(f"Re-fetching media via Evolution API for message {message.platform_message_id}")

            # Get instance config to get Evolution API credentials
            from src.db.models import InstanceConfig

            instance = self.db.query(InstanceConfig).filter(InstanceConfig.name == message.instance_name).first()

            if not instance:
                return False, f"Instance {message.instance_name} not found"

            if not instance.evolution_url or not instance.evolution_key:
                return False, "Evolution API URL or key not configured for instance"

            # Get the message key from platform_key
            platform_key = message.get_platform_key()
            if not platform_key:
                return False, "No platform key available for re-fetch"

            message_id = platform_key.get("id") or message.platform_message_id

            # Call Evolution API getBase64FromMediaMessage
            url = f"{instance.evolution_url}/chat/getBase64FromMediaMessage/{message.instance_name}"
            headers = {
                "apikey": instance.evolution_key,
                "Content-Type": "application/json",
            }
            payload = {
                "message": {"key": {"id": message_id}},
                "convertToMp4": False,
            }

            logger.debug(f"Calling Evolution API: {url}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            if response.status_code != 200:
                return False, f"Evolution API returned {response.status_code}: {response.text[:200]}"

            result = response.json()

            if not result or not result.get("base64"):
                return False, "Evolution API did not return base64 data"

            # Decode base64 and write to file
            media_data = base64.b64decode(result["base64"])

            with open(output_path, "wb") as f:
                f.write(media_data)

            file_size = output_path.stat().st_size
            logger.info(f"Re-fetched media via Evolution API: {file_size} bytes -> {output_path}")

            return True, None

        except Exception as e:
            logger.error(f"Error re-fetching via Evolution API: {e}")
            return False, f"Evolution API re-fetch failed: {e}"

    def _compute_file_sha256(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def download_media(self, message: OmniMessageRecord) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Download media for a message.

        Handles:
        - SHA256 deduplication (returns existing path if same file already downloaded)
        - Direct URL download (Discord, Evolution processed)
        - Encrypted WhatsApp media decryption

        Args:
            message: OmniMessageRecord with media to download

        Returns:
            Tuple of (success, local_path, error_message)
        """
        if not message.has_media:
            return False, None, "Message has no media"

        # Resolve the actual media URL (handles placeholder URLs)
        media_url = self._resolve_media_url(message)
        if not media_url:
            return False, None, "No media URL available (could not resolve)"

        # Check SHA256 deduplication first
        if message.media_sha256:
            existing_path = self._check_sha256_exists(message.media_sha256)
            if existing_path:
                logger.info(f"Using existing file for SHA256 {message.media_sha256[:16]}...: {existing_path}")
                return True, existing_path, None

        # Determine output path
        output_path = self._get_storage_path(message)

        # Check if file already exists at expected path
        if output_path.exists():
            logger.info(f"Media file already exists: {output_path}")
            return True, str(output_path), None

        # Determine download method
        # WhatsApp media with media_key is ALWAYS encrypted, regardless of URL extension
        is_encrypted = bool(message.media_key) and message.channel_type == "whatsapp"

        if is_encrypted:
            # WhatsApp encrypted media
            success, error = self._download_encrypted_whatsapp(
                url=media_url,
                media_key=message.media_key,
                media_type=message.message_type,
                output_path=output_path,
            )

            # If decryption failed (expired keys), try Evolution API fallback
            if not success and message.channel_type == "whatsapp":
                logger.info("Decryption failed, trying Evolution API fallback...")
                success, error = self._refetch_via_evolution_api(message, output_path)
        else:
            # Direct URL download
            success, error = self._download_direct_url(media_url, output_path)

        if not success:
            return False, None, error

        # Compute and store SHA256 if not already present
        if not message.media_sha256 and output_path.exists():
            message.media_sha256 = self._compute_file_sha256(output_path)

        return True, str(output_path), None

    def download_and_update(self, message_id: str) -> Dict[str, Any]:
        """
        Download media for a message and update its status in the database.

        Args:
            message_id: ID of the OmniMessageRecord

        Returns:
            Dict with download result
        """
        message = self.db.query(OmniMessageRecord).filter(OmniMessageRecord.id == message_id).first()

        if not message:
            return {"success": False, "error": f"Message {message_id} not found"}

        if not message.has_media:
            return {"success": False, "error": "Message has no media"}

        if message.media_status == "downloaded" and message.media_local_path:
            # Already downloaded, verify file exists
            if Path(message.media_local_path).exists():
                return {
                    "success": True,
                    "path": message.media_local_path,
                    "status": "already_downloaded",
                }
            else:
                # File was deleted, reset status to re-download
                message.media_status = "pending"
                message.media_local_path = None

        # Perform download
        success, local_path, error = self.download_media(message)

        # Update message record
        if success:
            message.media_local_path = local_path
            message.media_status = "downloaded"
            message.updated_at = datetime_utcnow()
            self.db.commit()

            return {
                "success": True,
                "path": local_path,
                "status": "downloaded",
                "sha256": message.media_sha256,
            }
        else:
            # Check if URL expired
            if error and ("404" in error or "expired" in error.lower()):
                message.media_status = "expired"
            else:
                message.media_status = "failed"
            message.updated_at = datetime_utcnow()
            self.db.commit()

            return {
                "success": False,
                "error": error,
                "status": message.media_status,
            }

    def batch_download(
        self,
        instance_name: Optional[str] = None,
        message_type: Optional[str] = None,
        limit: int = 100,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Batch download pending media for multiple messages.

        Args:
            instance_name: Filter by instance (optional)
            message_type: Filter by message type (e.g., 'audio', 'image')
            limit: Maximum number of messages to process
            progress_callback: Optional callback(processed, total)

        Returns:
            Dict with batch download statistics
        """
        # Query pending media
        query = (
            self.db.query(OmniMessageRecord)
            .filter(OmniMessageRecord.has_media == True)  # noqa: E712
            .filter(OmniMessageRecord.media_status == "pending")
            .filter(OmniMessageRecord.media_url.isnot(None))
        )

        if instance_name:
            query = query.filter(OmniMessageRecord.instance_name == instance_name)
        if message_type:
            query = query.filter(OmniMessageRecord.message_type == message_type)

        messages = query.limit(limit).all()

        stats = {
            "total": len(messages),
            "downloaded": 0,
            "failed": 0,
            "expired": 0,
            "skipped": 0,
            "results": [],
        }

        for i, message in enumerate(messages):
            result = self.download_and_update(message.id)

            if result["success"]:
                if result["status"] == "already_downloaded":
                    stats["skipped"] += 1
                else:
                    stats["downloaded"] += 1
            else:
                if result.get("status") == "expired":
                    stats["expired"] += 1
                else:
                    stats["failed"] += 1

            stats["results"].append(
                {
                    "message_id": message.id,
                    "type": message.message_type,
                    **result,
                }
            )

            if progress_callback:
                progress_callback(i + 1, len(messages))

        return stats


def download_media_for_message(message_id: str) -> Dict[str, Any]:
    """
    Utility function to download media for a single message.

    Args:
        message_id: ID of the OmniMessageRecord

    Returns:
        Download result dict
    """
    from src.db.database import get_db

    db = next(get_db())
    try:
        service = MediaDownloadService(db)
        return service.download_and_update(message_id)
    finally:
        db.close()
