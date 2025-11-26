"""HTTP client for OMNI API"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from .config import OmniConfig
from .models import (
    InstanceConfig,
    InstanceResponse,
    ConnectionStatus,
    QRCodeResponse,
    SendTextRequest,
    SendMediaRequest,
    SendAudioRequest,
    SendStickerRequest,
    SendContactRequest,
    SendReactionRequest,
    MessageResponse,
    TraceFilter,
    TraceResponse,
    TracePayloadResponse,
    TraceAnalytics,
    FetchProfileRequest,
    UpdateProfilePictureRequest,
    ChatResponse,
    ChatListResponse,
    ContactResponse,
    ContactListResponse,
    ChannelListResponse,
)

logger = logging.getLogger(__name__)


def normalize_jid(phone_or_jid: str) -> str:
    """
    Convert phone number to WhatsApp JID format automatically.

    Handles:
    - Individual numbers: "5511999999999" -> "5511999999999@s.whatsapp.net"
    - Group numbers: "120363421396472428" -> "120363421396472428@g.us"
    - Already formatted JIDs: returned unchanged

    Args:
        phone_or_jid: Phone number or JID

    Returns:
        Properly formatted WhatsApp JID
    """
    # Already a JID - return as-is
    if "@" in phone_or_jid:
        return phone_or_jid

    # Group numbers start with 120363
    if phone_or_jid.startswith("120363"):
        return f"{phone_or_jid}@g.us"

    # Individual phone number
    return f"{phone_or_jid}@s.whatsapp.net"


class OmniClient:
    """Async HTTP client for OMNI API"""

    def __init__(self, config: OmniConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.headers = {"x-api-key": config.api_key, "Content-Type": "application/json"}
        self.timeout = httpx.Timeout(config.timeout)

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=json,
                    params=params,
                )
                response.raise_for_status()

                # Handle empty responses
                if response.status_code == 204:
                    return {"success": True}

                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise Exception(
                    f"API error: {e.response.status_code} - {e.response.text}"
                )
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                raise

    # Instance Operations
    async def list_instances(
        self, skip: int = 0, limit: int = 100, include_status: bool = True
    ) -> List[InstanceResponse]:
        """List all instances"""
        params = {"skip": skip, "limit": limit, "include_status": include_status}
        data = await self._request("GET", "/api/v1/instances", params=params)
        return [InstanceResponse(**item) for item in data]

    async def get_instance(
        self, instance_name: str, include_status: bool = True
    ) -> InstanceResponse:
        """Get specific instance"""
        params = {"include_status": include_status}
        data = await self._request(
            "GET", f"/api/v1/instances/{instance_name}", params=params
        )
        return InstanceResponse(**data)

    async def create_instance(self, config: InstanceConfig) -> InstanceResponse:
        """Create new instance"""
        data = await self._request(
            "POST", "/api/v1/instances", json=config.model_dump(exclude_none=True)
        )
        return InstanceResponse(**data)

    async def update_instance(
        self, instance_name: str, config: Dict[str, Any]
    ) -> InstanceResponse:
        """Update instance"""
        data = await self._request(
            "PUT", f"/api/v1/instances/{instance_name}", json=config
        )
        return InstanceResponse(**data)

    async def delete_instance(self, instance_name: str) -> bool:
        """Delete instance"""
        await self._request("DELETE", f"/api/v1/instances/{instance_name}")
        return True

    async def set_default_instance(self, instance_name: str) -> InstanceResponse:
        """Set instance as default"""
        data = await self._request(
            "POST", f"/api/v1/instances/{instance_name}/set-default"
        )
        return InstanceResponse(**data)

    async def get_instance_status(self, instance_name: str) -> ConnectionStatus:
        """Get instance connection status"""
        data = await self._request("GET", f"/api/v1/instances/{instance_name}/status")
        return ConnectionStatus(**data)

    async def get_instance_qr(self, instance_name: str) -> QRCodeResponse:
        """Get instance QR code"""
        data = await self._request("GET", f"/api/v1/instances/{instance_name}/qr")
        return QRCodeResponse(**data)

    async def restart_instance(self, instance_name: str) -> Dict[str, Any]:
        """Restart instance"""
        return await self._request("POST", f"/api/v1/instances/{instance_name}/restart")

    async def logout_instance(self, instance_name: str) -> Dict[str, Any]:
        """Logout instance"""
        return await self._request("POST", f"/api/v1/instances/{instance_name}/logout")

    # Message Operations
    async def send_text(
        self, instance_name: str, request: SendTextRequest
    ) -> MessageResponse:
        """Send text message"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/send-text",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return MessageResponse(**data)

    async def send_media(
        self, instance_name: str, request: SendMediaRequest
    ) -> MessageResponse:
        """Send media message"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/send-media",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return MessageResponse(**data)

    async def send_audio(
        self, instance_name: str, request: SendAudioRequest
    ) -> MessageResponse:
        """Send audio message"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/send-audio",
            json=request.model_dump(exclude_none=True),
        )
        return MessageResponse(**data)

    async def send_sticker(
        self, instance_name: str, request: SendStickerRequest
    ) -> MessageResponse:
        """Send sticker message"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/send-sticker",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return MessageResponse(**data)

    async def send_contact(
        self, instance_name: str, request: SendContactRequest
    ) -> MessageResponse:
        """Send contact message"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/send-contact",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return MessageResponse(**data)

    async def send_reaction(
        self, instance_name: str, request: SendReactionRequest
    ) -> MessageResponse:
        """Send reaction"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/send-reaction",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return MessageResponse(**data)

    # Trace Operations
    async def list_traces(self, filters: TraceFilter) -> List[TraceResponse]:
        """List traces with filters"""
        params = {
            k: v
            for k, v in filters.model_dump(exclude_none=True).items()
            if v is not None
        }
        data = await self._request("GET", "/api/v1/traces", params=params)
        return [TraceResponse(**item) for item in data]

    async def get_trace(self, trace_id: str) -> TraceResponse:
        """Get specific trace"""
        data = await self._request("GET", f"/api/v1/traces/{trace_id}")
        return TraceResponse(**data)

    async def get_trace_payloads(
        self, trace_id: str, include_payload: bool = False
    ) -> List[TracePayloadResponse]:
        """Get trace payloads"""
        params = {"include_payload": include_payload}
        data = await self._request(
            "GET", f"/api/v1/traces/{trace_id}/payloads", params=params
        )
        return [TracePayloadResponse(**item) for item in data]

    async def get_trace_analytics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        instance_name: Optional[str] = None,
    ) -> TraceAnalytics:
        """Get trace analytics"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if instance_name:
            params["instance_name"] = instance_name

        data = await self._request(
            "GET", "/api/v1/traces/analytics/summary", params=params
        )
        return TraceAnalytics(**data)

    async def get_traces_by_phone(
        self, phone_number: str, limit: int = 50
    ) -> List[TraceResponse]:
        """Get traces for phone number"""
        params = {"limit": limit}
        data = await self._request(
            "GET", f"/api/v1/traces/phone/{phone_number}", params=params
        )
        return [TraceResponse(**item) for item in data]

    async def cleanup_traces(
        self, days_old: int = 30, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Cleanup old traces"""
        params = {"days_old": days_old, "dry_run": dry_run}
        return await self._request("DELETE", "/api/v1/traces/cleanup", params=params)

    # Profile Operations
    async def fetch_profile(
        self, instance_name: str, request: FetchProfileRequest
    ) -> Dict[str, Any]:
        """Fetch user profile"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/fetch-profile",
            json=request.model_dump(exclude_none=True),
        )
        return data

    async def update_profile_picture(
        self, instance_name: str, request: UpdateProfilePictureRequest
    ) -> MessageResponse:
        """Update profile picture"""
        data = await self._request(
            "POST",
            f"/api/v1/instance/{instance_name}/update-profile-picture",
            json=request.model_dump(exclude_none=True),
        )
        return MessageResponse(**data)

    # Chat Operations
    async def list_chats(
        self,
        instance_name: str,
        page: int = 1,
        page_size: int = 50,
        chat_type_filter: Optional[str] = None,
        archived: Optional[bool] = None,
        channel_type: Optional[str] = None,
    ) -> ChatListResponse:
        """List chats for an instance"""
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if chat_type_filter:
            params["chat_type_filter"] = chat_type_filter
        if archived is not None:
            params["archived"] = archived
        if channel_type:
            params["channel_type"] = channel_type

        data = await self._request(
            "GET", f"/api/v1/instances/{instance_name}/chats", params=params
        )
        return ChatListResponse(**data)

    async def get_chat(self, instance_name: str, chat_id: str) -> ChatResponse:
        """Get specific chat"""
        data = await self._request(
            "GET", f"/api/v1/instances/{instance_name}/chats/{chat_id}"
        )
        return ChatResponse(**data)

    # Contact Operations
    async def list_contacts(
        self,
        instance_name: str,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
        channel_type: Optional[str] = None,
    ) -> ContactListResponse:
        """List contacts for an instance"""
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if search_query:
            params["search_query"] = search_query
        if status_filter:
            params["status_filter"] = status_filter
        if channel_type:
            params["channel_type"] = channel_type

        data = await self._request(
            "GET", f"/api/v1/instances/{instance_name}/contacts", params=params
        )
        return ContactListResponse(**data)

    async def get_contact(self, instance_name: str, contact_id: str) -> ContactResponse:
        """Get specific contact"""
        data = await self._request(
            "GET", f"/api/v1/instances/{instance_name}/contacts/{contact_id}"
        )
        return ContactResponse(**data)

    # Channel Operations
    async def list_channels(
        self, channel_type: Optional[str] = None
    ) -> ChannelListResponse:
        """List all channels/instances in Omni format"""
        params = {}
        if channel_type:
            params["channel_type"] = channel_type

        data = await self._request("GET", "/api/v1/instances/", params=params)
        return ChannelListResponse(**data)

    # Evolution API Direct Access
    async def evolution_send_text(
        self, instance_name: str, remote_jid: str, text: str,
        quoted_msg_id: Optional[str] = None, from_me: bool = False,
        delay: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send text message via Evolution API directly (with optional quote)"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload: Dict[str, Any] = {
                    "number": remote_jid,
                    "text": text
                }

                if delay:
                    payload["delay"] = delay

                if quoted_msg_id:
                    payload["quoted"] = {
                        "key": {
                            "remoteJid": remote_jid,
                            "fromMe": from_me,
                            "id": quoted_msg_id
                        }
                    }

                response = await client.post(
                    f"{instance.evolution_url}/message/sendText/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_send_text_quoted(
        self, instance_name: str, remote_jid: str, text: str, quoted_msg_id: str, from_me: bool = False
    ) -> Dict[str, Any]:
        """Legacy method - use evolution_send_text instead"""
        remote_jid = normalize_jid(remote_jid)
        return await self.evolution_send_text(
            instance_name=instance_name,
            remote_jid=remote_jid,
            text=text,
            quoted_msg_id=quoted_msg_id,
            from_me=from_me
        )

    async def evolution_send_reaction(
        self, instance_name: str, remote_jid: str, message_id: str, emoji: str, from_me: bool = False
    ) -> Dict[str, Any]:
        """Send reaction via Evolution API directly"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/message/sendReaction/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "key": {
                            "remoteJid": remote_jid,
                            "fromMe": from_me,
                            "id": message_id
                        },
                        "reaction": emoji
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_find_messages(
        self, instance_name: str, remote_jid: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Call Evolution API findMessages directly for message history"""
        remote_jid = normalize_jid(remote_jid)

        # First get instance to get Evolution credentials
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        # Call Evolution API directly
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/chat/findMessages/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "where": {"key": {"remoteJid": remote_jid}},
                        "limit": limit,
                        "sort": {"messageTimestamp": -1}  # Newest first
                    }
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Evolution API response: {result}")
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_send_location(
        self, instance_name: str, remote_jid: str, latitude: float, longitude: float,
        name: Optional[str] = None, address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send location via Evolution API directly"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        payload = {
            "number": remote_jid,
            "latitude": latitude,
            "longitude": longitude
        }

        if name:
            payload["name"] = name
        if address:
            payload["address"] = address

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/message/sendLocation/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_delete_message(
        self, instance_name: str, remote_jid: str, message_id: str, from_me: bool = True
    ) -> Dict[str, Any]:
        """Delete message for everyone via Evolution API directly"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method="DELETE",
                    url=f"{instance.evolution_url}/chat/deleteMessageForEveryone/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "id": message_id,
                        "remoteJid": remote_jid,
                        "fromMe": from_me
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_send_presence(
        self, instance_name: str, remote_jid: str, presence: str, delay: int = 3000
    ) -> Dict[str, Any]:
        """Send presence status (typing, recording, etc) via Evolution API directly

        Available presence types:
        - composing: Typing... (default 3 seconds)
        - recording: Recording audio... (default 3 seconds)
        """
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/chat/sendPresence/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "number": remote_jid,
                        "options": {
                            "delay": delay,
                            "presence": presence,
                            "number": remote_jid
                        }
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_update_message(
        self, instance_name: str, remote_jid: str, message_id: str, new_text: str, from_me: bool = True
    ) -> Dict[str, Any]:
        """Update (edit) a message via Evolution API directly"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/chat/updateMessage/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "number": remote_jid,
                        "text": new_text,
                        "key": {
                            "remoteJid": remote_jid,
                            "fromMe": from_me,
                            "id": message_id
                        }
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_check_is_whatsapp(
        self, instance_name: str, phone_numbers: List[str]
    ) -> Dict[str, Any]:
        """Check if phone numbers are registered on WhatsApp via Evolution API directly"""
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/chat/whatsappNumbers/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "numbers": phone_numbers
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_send_poll(
        self, instance_name: str, remote_jid: str, name: str, options: List[str], selectable_count: int = 1
    ) -> Dict[str, Any]:
        """Send poll via Evolution API directly"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/message/sendPoll/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "number": remote_jid,
                        "name": name,
                        "selectableCount": selectable_count,
                        "values": options
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_send_sticker(
        self, instance_name: str, remote_jid: str, sticker_url: str,
        quoted_message_id: Optional[str] = None, delay: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send sticker via Evolution API directly"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload: Dict[str, Any] = {
                    "number": remote_jid,
                    "sticker": sticker_url
                }

                if delay:
                    payload["delay"] = delay
                if quoted_message_id:
                    payload["quoted"] = {"key": {"id": quoted_message_id}}

                response = await client.post(
                    f"{instance.evolution_url}/message/sendSticker/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_send_media(
        self, instance_name: str, remote_jid: str,
        media_url: Optional[str] = None, media_base64: Optional[str] = None,
        media_type: str = "image", caption: Optional[str] = None,
        filename: Optional[str] = None, mime_type: Optional[str] = None,
        quoted_message_id: Optional[str] = None, delay: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send media (image/video/document) via Evolution API directly

        Supports both URL and base64 media.
        """
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        if not media_url and not media_base64:
            raise Exception("Either media_url or media_base64 must be provided")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload: Dict[str, Any] = {
                    "number": remote_jid,
                    "mediatype": media_type  # Required: image, video, or document
                }

                # Add media (URL or base64)
                if media_base64:
                    payload["media"] = media_base64  # Evolution API uses "media" for both URL and base64
                    if filename:
                        payload["fileName"] = filename
                elif media_url:
                    payload["media"] = media_url

                # Add optional fields
                if caption:
                    payload["caption"] = caption
                if mime_type:
                    payload["mimetype"] = mime_type
                if delay:
                    payload["delay"] = delay
                if quoted_message_id:
                    payload["quoted"] = {"key": {"id": quoted_message_id}}

                # Determine endpoint based on media type
                endpoint_map = {
                    "image": "sendMedia",
                    "video": "sendMedia",
                    "document": "sendMedia"
                }
                endpoint = endpoint_map.get(media_type, "sendMedia")

                response = await client.post(
                    f"{instance.evolution_url}/message/{endpoint}/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_send_contact(
        self, instance_name: str, remote_jid: str, contacts: List[Dict[str, Any]],
        quoted_message_id: Optional[str] = None, delay: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send contact(s) via Evolution API directly"""
        remote_jid = normalize_jid(remote_jid)
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Convert contact fields from snake_case to camelCase for Evolution API
                evolution_contacts = []
                for contact in contacts:
                    evolution_contact = {}
                    if "full_name" in contact:
                        evolution_contact["fullName"] = contact["full_name"]
                    if "phone_number" in contact:
                        evolution_contact["phoneNumber"] = contact["phone_number"]
                    if "email" in contact:
                        evolution_contact["email"] = contact["email"]
                    if "organization" in contact:
                        evolution_contact["organization"] = contact["organization"]
                    if "url" in contact:
                        evolution_contact["url"] = contact["url"]
                    evolution_contacts.append(evolution_contact)

                payload: Dict[str, Any] = {
                    "number": remote_jid,
                    "contact": evolution_contacts
                }

                if delay:
                    payload["delay"] = delay
                if quoted_message_id:
                    payload["quoted"] = {"key": {"id": quoted_message_id}}

                response = await client.post(
                    f"{instance.evolution_url}/message/sendContact/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_find_chats(
        self, instance_name: str
    ) -> Dict[str, Any]:
        """Find all chats via Evolution API"""
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{instance.evolution_url}/chat/findChats/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json={}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_fetch_all_groups(
        self, instance_name: str, get_participants: bool = True
    ) -> Dict[str, Any]:
        """Fetch all groups via Evolution API"""
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{instance.evolution_url}/group/fetchAllGroups/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key
                    },
                    params={"getParticipants": str(get_participants).lower()}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_find_group_members(
        self, instance_name: str, group_jid: str
    ) -> Dict[str, Any]:
        """Find group members via Evolution API"""
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{instance.evolution_url}/group/participants/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key
                    },
                    params={"groupJid": group_jid}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise

    async def evolution_get_base64_media(
        self, instance_name: str, message_id: str, convert_to_mp4: bool = False
    ) -> Dict[str, Any]:
        """Get media from message as base64 via Evolution API directly

        This is an internal method used to abstract media downloading.
        Media is saved to tmp folder automatically, not exposed directly.
        """
        instance = await self.get_instance(instance_name, include_status=False)

        if not instance.evolution_url or not instance.evolution_key:
            raise Exception("Evolution API not configured for this instance")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload = {
                    "message": {
                        "key": {
                            "id": message_id
                        }
                    },
                    "convertToMp4": convert_to_mp4
                }

                response = await client.post(
                    f"{instance.evolution_url}/chat/getBase64FromMediaMessage/{instance_name}",
                    headers={
                        "apikey": instance.evolution_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Evolution API error {e.response.status_code}: {e.response.text}")
                raise Exception(f"Evolution API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Evolution API request failed: {str(e)}")
                raise
