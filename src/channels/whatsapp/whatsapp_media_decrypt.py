"""
WhatsApp Media Decryption Module
Based on WhatsApp's end-to-end encryption protocol for media files.

This module decrypts WhatsApp media files (.enc) using the mediaKey provided
in the webhook payload, following the same algorithm used by WhatsApp clients.
"""

import base64
import hashlib
import logging
from typing import Optional, Tuple
import sys

sys.path.append("/usr/lib/python3/dist-packages")

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad

    CRYPTO_AVAILABLE = True
except ImportError:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad

        CRYPTO_AVAILABLE = True
    except ImportError:
        AES = None
        unpad = None
        CRYPTO_AVAILABLE = False
import requests
import tempfile

logger = logging.getLogger(__name__)


class WhatsAppMediaDecryptor:
    """Handles decryption of WhatsApp encrypted media files."""

    # Media type constants for key derivation
    MEDIA_TYPE_IMAGE = 1
    MEDIA_TYPE_VIDEO = 2
    MEDIA_TYPE_AUDIO = 3
    MEDIA_TYPE_DOCUMENT = 4

    def __init__(self):
        """Initialize the media decryptor."""
        pass

    def decrypt_media(
        self, encrypted_url: str, media_key_b64: str, media_type: int = MEDIA_TYPE_AUDIO
    ) -> Optional[bytes]:
        """
        Decrypt WhatsApp encrypted media.

        Args:
            encrypted_url: URL to the encrypted .enc file
            media_key_b64: Base64 encoded media key from the webhook
            media_type: Type of media (1=image, 2=video, 3=audio, 4=document)

        Returns:
            Optional[bytes]: Decrypted media content or None if failed
        """
        try:
            # Download the encrypted file
            logger.info(f"Downloading encrypted media from: {encrypted_url[:50]}...")
            encrypted_data = self._download_encrypted_file(encrypted_url)
            if not encrypted_data:
                logger.error("Failed to download encrypted file")
                return None

            # Decode the media key
            try:
                media_key = base64.b64decode(media_key_b64)
                logger.info(f"Decoded media key (length: {len(media_key)} bytes)")
            except Exception as e:
                logger.error(f"Failed to decode media key: {e}")
                return None

            # Decrypt the media
            decrypted_data = self._decrypt_whatsapp_media(encrypted_data, media_key, media_type)
            if decrypted_data:
                logger.info(f"Successfully decrypted media (size: {len(decrypted_data)} bytes)")
                return decrypted_data
            else:
                logger.error("Failed to decrypt media")
                return None

        except Exception as e:
            logger.error(f"Error during media decryption: {e}", exc_info=True)
            return None

    def decrypt_and_save_temp(
        self, encrypted_url: str, media_key_b64: str, media_type: int = MEDIA_TYPE_AUDIO
    ) -> Optional[str]:
        """
        Decrypt media and save to a temporary file.

        Args:
            encrypted_url: URL to the encrypted .enc file
            media_key_b64: Base64 encoded media key
            media_type: Type of media

        Returns:
            Optional[str]: Path to temporary decrypted file or None if failed
        """
        decrypted_data = self.decrypt_media(encrypted_url, media_key_b64, media_type)
        if not decrypted_data:
            return None

        try:
            # Create temporary file
            suffix = self._get_file_suffix(media_type)
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(decrypted_data)
                temp_path = temp_file.name

            logger.info(f"Saved decrypted media to temporary file: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to save decrypted media to temp file: {e}")
            return None

    def _download_encrypted_file(self, url: str) -> Optional[bytes]:
        """Download the encrypted file from WhatsApp servers."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            file_size = len(response.content)

            logger.info(f"Downloaded encrypted file: {file_size} bytes, content-type: {content_type}")
            return response.content

        except Exception as e:
            logger.error(f"Failed to download encrypted file: {e}")
            return None

    def _decrypt_whatsapp_media(self, encrypted_data: bytes, media_key: bytes, media_type: int) -> Optional[bytes]:
        """
        Decrypt WhatsApp media using the standard WhatsApp decryption algorithm.

        Based on the WhatsApp encryption specification:
        1. Derive keys from media key using HKDF-SHA256
        2. Validate file integrity using HMAC over IV + ciphertext
        3. Decrypt using AES-256-CBC
        """
        try:
            # Extract the encrypted content (skip the last 10 bytes which contain the MAC)
            if len(encrypted_data) < 10:
                logger.error("Encrypted data too short")
                return None

            mac_from_file = encrypted_data[-10:]
            encrypted_content = encrypted_data[:-10]

            # Derive keys using HKDF-SHA256
            keys = self._expand_key(media_key, media_type)
            if not keys:
                logger.error("Failed to derive encryption keys")
                return None

            iv, cipher_key, mac_key = keys

            # Verify MAC (WhatsApp calculates MAC over IV + ciphertext)
            if not self._verify_mac(encrypted_content, mac_key, mac_from_file, iv):
                logger.error("MAC verification failed - file may be corrupted")
                return None

            # Decrypt using AES-256-CBC
            decrypted_data = self._aes_decrypt(encrypted_content, cipher_key, iv)
            if decrypted_data:
                logger.info("Successfully decrypted WhatsApp media")
                return decrypted_data
            else:
                logger.error("AES decryption failed")
                return None

        except Exception as e:
            logger.error(f"Error in WhatsApp media decryption: {e}", exc_info=True)
            return None

    def _expand_key(self, media_key: bytes, media_type: int) -> Optional[Tuple[bytes, bytes, bytes]]:
        """
        Expand the media key using HKDF to derive IV, cipher key, and MAC key.

        WhatsApp uses HKDF-SHA256 for key derivation based on the media type.
        """
        import hmac

        try:
            # Create the info parameter for HKDF based on media type
            if media_type == self.MEDIA_TYPE_IMAGE:
                info = b"WhatsApp Image Keys"
            elif media_type == self.MEDIA_TYPE_VIDEO:
                info = b"WhatsApp Video Keys"
            elif media_type == self.MEDIA_TYPE_AUDIO:
                info = b"WhatsApp Audio Keys"
            elif media_type == self.MEDIA_TYPE_DOCUMENT:
                info = b"WhatsApp Document Keys"
            else:
                logger.error(f"Unknown media type: {media_type}")
                return None

            # HKDF-SHA256 implementation
            # Step 1: Extract phase - use empty salt (WhatsApp standard)
            # PRK = HMAC-SHA256(salt, IKM) where salt is empty/zeros
            salt = b"\x00" * 32  # 32 zero bytes
            prk = hmac.new(salt, media_key, hashlib.sha256).digest()

            # Step 2: Expand phase using HMAC-SHA256
            # Output: 16 bytes IV + 32 bytes cipher key + 32 bytes MAC key = 80 bytes needed
            # We need 112 bytes total to match WhatsApp's implementation
            output_length = 112
            output = b""
            prev_block = b""
            counter = 1

            while len(output) < output_length:
                # T(n) = HMAC-SHA256(PRK, T(n-1) || info || counter)
                h = hmac.new(prk, prev_block + info + bytes([counter]), hashlib.sha256)
                prev_block = h.digest()
                output += prev_block
                counter += 1

            # Extract the keys
            iv = output[0:16]  # First 16 bytes for IV
            cipher_key = output[16:48]  # Next 32 bytes for cipher key
            mac_key = output[48:80]  # Next 32 bytes for MAC key

            logger.debug(
                f"Derived keys - IV: {len(iv)} bytes, Cipher: {len(cipher_key)} bytes, MAC: {len(mac_key)} bytes"
            )
            return iv, cipher_key, mac_key

        except Exception as e:
            logger.error(f"Key expansion failed: {e}")
            return None

    def _verify_mac(self, encrypted_content: bytes, mac_key: bytes, expected_mac: bytes, iv: bytes) -> bool:
        """Verify the HMAC of the IV + encrypted content."""
        try:
            import hmac

            # Calculate HMAC-SHA256 of IV + encrypted content (WhatsApp includes IV in MAC)
            calculated_mac = hmac.new(mac_key, iv + encrypted_content, hashlib.sha256).digest()

            # WhatsApp uses the first 10 bytes of the HMAC
            calculated_mac_truncated = calculated_mac[:10]

            # Compare with expected MAC
            is_valid = hmac.compare_digest(calculated_mac_truncated, expected_mac)

            if is_valid:
                logger.debug("MAC verification successful")
            else:
                logger.error(
                    f"MAC mismatch - calculated: {calculated_mac_truncated.hex()}, expected: {expected_mac.hex()}"
                )

            return is_valid

        except Exception as e:
            logger.error(f"MAC verification failed: {e}")
            return False

    def _aes_decrypt(self, encrypted_content: bytes, cipher_key: bytes, iv: bytes) -> Optional[bytes]:
        """Decrypt content using AES-256-CBC."""
        try:
            if not CRYPTO_AVAILABLE:
                logger.error("Crypto library not available - cannot decrypt WhatsApp media")
                return None

            # Create AES cipher in CBC mode
            cipher = AES.new(cipher_key, AES.MODE_CBC, iv)

            # Decrypt the content
            decrypted_padded = cipher.decrypt(encrypted_content)

            # Remove PKCS7 padding
            try:
                decrypted = unpad(decrypted_padded, AES.block_size)
                logger.debug(f"AES decryption successful, output size: {len(decrypted)} bytes")
                return decrypted
            except ValueError as e:
                logger.error(f"Padding removal failed: {e}")
                # Try without padding removal (some files might not be padded)
                return decrypted_padded

        except Exception as e:
            logger.error(f"AES decryption failed: {e}")
            return None

    def _get_file_suffix(self, media_type: int) -> str:
        """Get appropriate file suffix for media type."""
        if media_type == self.MEDIA_TYPE_AUDIO:
            return ".oga"  # WhatsApp uses OGG audio
        elif media_type == self.MEDIA_TYPE_IMAGE:
            return ".jpg"
        elif media_type == self.MEDIA_TYPE_VIDEO:
            return ".mp4"
        elif media_type == self.MEDIA_TYPE_DOCUMENT:
            return ".bin"
        else:
            return ".bin"


# Global instance for easy access
whatsapp_media_decryptor = WhatsAppMediaDecryptor()
