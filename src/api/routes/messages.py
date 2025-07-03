"""
Message sending API endpoints.
Provides simplified sending endpoints that wrap Evolution API calls.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.api.deps import get_database, verify_api_key, get_instance_by_name
from src.channels.whatsapp.evolution_api_sender import EvolutionApiSender
from src.services.user_service import user_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Force reload to pick up user_id type changes
# Schema update trigger


# Test model for debugging
class TestRequest(BaseModel):
    """Test schema for debugging user_id types."""

    user_id: Union[str, None] = Field(None, description="User ID (UUID string)")
    test_field: str = Field(description="Test field")


# Pydantic models for message sending
class SendTextRequest(BaseModel):
    """Schema for sending text messages."""

    user_id: Union[str, None] = Field(
        None, description="User ID (UUID string, if known)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code (e.g., +5511999999999)"
    )
    text: str = Field(description="Message text to send")
    quoted_message_id: Optional[str] = Field(
        None, description="ID of message to quote/reply to"
    )


class SendMediaRequest(BaseModel):
    """Schema for sending media messages."""

    user_id: Union[str, None] = Field(
        None, description="User ID (UUID string, if known)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    media_type: str = Field(description="Media type: image, video, document")
    media_url: Optional[str] = Field(None, description="URL to media file")
    media_base64: Optional[str] = Field(None, description="Base64 encoded media data")
    mime_type: str = Field(description="MIME type (e.g., image/jpeg, video/mp4)")
    caption: Optional[str] = Field(None, description="Media caption")
    filename: Optional[str] = Field(None, description="File name for documents")


class SendAudioRequest(BaseModel):
    """Schema for sending WhatsApp audio messages."""

    user_id: Union[str, None] = Field(
        None, description="User ID (UUID string, if known)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio data")


class SendStickerRequest(BaseModel):
    """Schema for sending stickers."""

    user_id: Union[str, None] = Field(
        None, description="User ID (UUID string, if known)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    sticker_url: Optional[str] = Field(None, description="URL to sticker file")
    sticker_base64: Optional[str] = Field(
        None, description="Base64 encoded sticker data"
    )


class ContactInfo(BaseModel):
    """Contact information schema."""

    full_name: str = Field(description="Contact's full name")
    phone_number: Optional[str] = Field(None, description="Contact's phone number")
    email: Optional[str] = Field(None, description="Contact's email")
    organization: Optional[str] = Field(None, description="Contact's organization")
    url: Optional[str] = Field(None, description="Contact's website URL")


class SendContactRequest(BaseModel):
    """Schema for sending contact cards."""

    user_id: Union[str, None] = Field(
        None, description="User ID (UUID string, if known)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    contacts: List[ContactInfo] = Field(description="List of contacts to send")


class SendReactionRequest(BaseModel):
    """Schema for sending reactions."""

    user_id: Union[str, None] = Field(
        None, description="User ID (UUID string, if known)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    message_id: str = Field(description="ID of message to react to")
    reaction: str = Field(description="Reaction emoji (e.g., 🚀, ❤️)")


class FetchProfileRequest(BaseModel):
    """Schema for fetching user profiles."""

    user_id: Union[str, None] = Field(
        None, description="User ID (UUID string, if known)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )


class UpdateProfilePictureRequest(BaseModel):
    """Schema for updating profile picture."""

    picture_url: str = Field(description="URL to new profile picture")


class MessageResponse(BaseModel):
    """Schema for message sending response."""

    success: bool
    message_id: Optional[str] = None
    status: str
    evolution_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _resolve_recipient(
    user_id: Optional[str], phone_number: Optional[str], db: Session
) -> str:
    """
    Resolve user_id or phone_number to WhatsApp JID using the new user service.

    Resolution order:
    1. If user_id provided: lookup in our local user database
    2. If not found locally: try agent API (backward compatibility)
    3. If phone_number provided: use directly

    Returns:
        str: WhatsApp JID (remoteJid) for the recipient
    """
    if not user_id and not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or phone_number must be provided",
        )

    # First: try to resolve user_id through our local user database
    if user_id:
        # Look up user by our stable internal UUID first
        user = user_service.get_user_by_id(user_id, db)
        if user:
            logger.info(
                f"Resolved user_id {user_id} to phone {user.phone_number} via local database (internal UUID)"
            )
            return user_service.resolve_user_to_jid(user)

        # Also try to find by agent user_id (for backward compatibility)
        user = user_service.get_user_by_agent_id(user_id, db)
        if user:
            logger.info(
                f"Resolved user_id {user_id} to phone {user.phone_number} via local database (agent UUID)"
            )
            return user_service.resolve_user_to_jid(user)

        # Fallback: try agent API lookup for backward compatibility
        user_data = user_service.try_agent_api_lookup(user_id)
        if user_data:
            # Try to get WhatsApp ID from user_data
            whatsapp_id = user_data.get("user_data", {}).get("whatsapp_id")
            if whatsapp_id:
                logger.info(
                    f"Found WhatsApp ID for user_id {user_id} via agent API: {whatsapp_id}"
                )
                return whatsapp_id

            # Fallback to phone number from agent API
            user_phone = user_data.get("phone_number")
            if user_phone:
                logger.info(
                    f"Using phone number for user_id {user_id} via agent API: {user_phone}"
                )
                return _format_phone_to_jid(user_phone)

        # User not found anywhere
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found in local database or agent API",
        )

    # Direct phone number usage
    if phone_number:
        logger.info(f"Using provided phone number directly: {phone_number}")
        return _format_phone_to_jid(phone_number)


def _format_phone_to_jid(phone_number: str) -> str:
    """
    Format phone number to WhatsApp JID format.

    Args:
        phone_number: Phone number (with or without + and country code)

    Returns:
        str: WhatsApp JID format (e.g., 5511999999999@s.whatsapp.net)
    """
    # Remove any non-digit characters except +
    clean_phone = "".join(c for c in phone_number if c.isdigit() or c == "+")

    # Remove + if present
    if clean_phone.startswith("+"):
        clean_phone = clean_phone[1:]

    # Add @s.whatsapp.net if not present
    if "@" not in clean_phone:
        clean_phone = f"{clean_phone}@s.whatsapp.net"

    return clean_phone


@router.post("/{instance_name}/send-text", response_model=MessageResponse)
async def send_text_message(
    instance_name: str,
    request: SendTextRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Send a text message via WhatsApp."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Resolve recipient
        recipient = _resolve_recipient(request.user_id, request.phone_number, db)

        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Send the message
        success = sender.send_text_message(
            recipient=recipient,
            text=request.text,
            quoted_message=None,  # TODO: Implement quoted message lookup
        )

        return MessageResponse(
            success=success,
            status="sent" if success else "failed",
            message_id=None,  # Evolution API doesn't return message ID in current implementation
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send text message: {e}")
        return MessageResponse(success=False, status="error", error=str(e))


@router.post("/{instance_name}/send-media", response_model=MessageResponse)
async def send_media_message(
    instance_name: str,
    request: SendMediaRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Send a media message (image, video, document) via WhatsApp."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Resolve recipient
        recipient = _resolve_recipient(request.user_id, request.phone_number, db)

        # Validate media source
        if not request.media_url and not request.media_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either media_url or media_base64 must be provided",
            )

        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Use media_url or base64
        media_source = request.media_url if request.media_url else request.media_base64

        # Send the media message
        success = sender.send_media_message(
            recipient=recipient,
            media_type=request.media_type,
            media=media_source,
            mime_type=request.mime_type,
            caption=request.caption,
            filename=request.filename,
        )

        return MessageResponse(success=success, status="sent" if success else "failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send media message: {e}")
        return MessageResponse(success=False, status="error", error=str(e))


@router.post("/{instance_name}/send-audio", response_model=MessageResponse)
async def send_audio_message(
    instance_name: str,
    request: SendAudioRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Send a WhatsApp audio message."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Resolve recipient
        recipient = _resolve_recipient(request.user_id, request.phone_number, db)

        # Validate audio source
        if not request.audio_url and not request.audio_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either audio_url or audio_base64 must be provided",
            )

        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Use audio_url or base64
        audio_source = request.audio_url if request.audio_url else request.audio_base64

        # Send the audio message
        success = sender.send_audio_message(recipient=recipient, audio=audio_source)

        return MessageResponse(success=success, status="sent" if success else "failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send audio message: {e}")
        return MessageResponse(success=False, status="error", error=str(e))


@router.post("/{instance_name}/send-sticker", response_model=MessageResponse)
async def send_sticker_message(
    instance_name: str,
    request: SendStickerRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Send a sticker via WhatsApp."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Resolve recipient
        recipient = _resolve_recipient(request.user_id, request.phone_number, db)

        # Validate sticker source
        if not request.sticker_url and not request.sticker_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either sticker_url or sticker_base64 must be provided",
            )

        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Use sticker_url or base64
        sticker_source = (
            request.sticker_url if request.sticker_url else request.sticker_base64
        )

        # Send the sticker
        success = sender.send_sticker_message(
            recipient=recipient, sticker=sticker_source
        )

        return MessageResponse(success=success, status="sent" if success else "failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send sticker: {e}")
        return MessageResponse(success=False, status="error", error=str(e))


@router.post("/{instance_name}/send-contact", response_model=MessageResponse)
async def send_contact_message(
    instance_name: str,
    request: SendContactRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Send contact card(s) via WhatsApp."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Resolve recipient
        recipient = _resolve_recipient(request.user_id, request.phone_number, db)

        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Convert contacts to Evolution API format
        contacts_data = []
        for contact in request.contacts:
            contact_data = {
                "fullName": contact.full_name,
                "phoneNumber": contact.phone_number,
                "email": contact.email,
                "organization": contact.organization,
                "url": contact.url,
            }
            # Remove None values
            contact_data = {k: v for k, v in contact_data.items() if v is not None}
            contacts_data.append(contact_data)

        # Send the contact
        success = sender.send_contact_message(
            recipient=recipient, contacts=contacts_data
        )

        return MessageResponse(success=success, status="sent" if success else "failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send contact: {e}")
        return MessageResponse(success=False, status="error", error=str(e))


@router.post("/{instance_name}/send-reaction", response_model=MessageResponse)
async def send_reaction_message(
    instance_name: str,
    request: SendReactionRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Send a reaction to a message via WhatsApp."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Resolve recipient
        recipient = _resolve_recipient(request.user_id, request.phone_number, db)

        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Send the reaction
        success = sender.send_reaction_message(
            recipient=recipient,
            message_id=request.message_id,
            reaction=request.reaction,
        )

        return MessageResponse(success=success, status="sent" if success else "failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send reaction: {e}")
        return MessageResponse(success=False, status="error", error=str(e))


@router.post("/{instance_name}/fetch-profile")
async def fetch_user_profile(
    instance_name: str,
    request: FetchProfileRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Fetch a user's WhatsApp profile."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Resolve recipient
        recipient = _resolve_recipient(request.user_id, request.phone_number, db)

        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Fetch the profile
        profile_data = sender.fetch_profile(recipient)

        return {"success": True, "profile": profile_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch profile: {e}")
        return {"success": False, "error": str(e)}


@router.post("/{instance_name}/update-profile-picture", response_model=MessageResponse)
async def update_profile_picture(
    instance_name: str,
    request: UpdateProfilePictureRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Update the instance's profile picture."""

    instance_config = get_instance_by_name(instance_name, db)

    try:
        # Create Evolution API sender with instance config
        sender = EvolutionApiSender(config_override=instance_config)

        # Update profile picture
        success = sender.update_profile_picture(request.picture_url)

        return MessageResponse(
            success=success, status="updated" if success else "failed"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile picture: {e}")
        return MessageResponse(success=False, status="error", error=str(e))


@router.post("/{instance_name}/test-schema")
async def test_schema_endpoint(
    instance_name: str,
    request: TestRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Test endpoint for debugging schema generation."""
    return {
        "message": "Test endpoint",
        "user_id": request.user_id,
        "test_field": request.test_field,
    }
