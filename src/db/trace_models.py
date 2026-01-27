"""
SQLAlchemy models for message tracing system.
Tracks the complete lifecycle of messages through the Omni-Hub system.
"""

import uuid
import json
import zlib
import base64
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import relationship
from typing import Dict, Any, Optional
from .database import Base
from src.utils.datetime_utils import datetime_utcnow


class MessageTrace(Base):
    """
    Main message trace model that tracks the complete lifecycle of a message
    from webhook reception to final response delivery.
    """

    __tablename__ = "omni_message_traces"

    # Unique trace ID for the entire message lifecycle
    trace_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))

    # Instance and message identification
    instance_name = Column(String, ForeignKey("omni_instance_configs.name"), index=True)
    whatsapp_message_id = Column(String, index=True)  # Evolution message ID

    # Sender information
    sender_phone = Column(String, index=True)
    sender_name = Column(String)
    sender_jid = Column(String)  # Full WhatsApp JID

    # Message metadata
    message_type = Column(String)  # text, image, audio, video, document
    has_media = Column(Boolean, default=False)
    has_quoted_message = Column(Boolean, default=False)
    message_length = Column(Integer)

    # Session tracking
    session_name = Column(String, index=True)
    agent_session_id = Column(String)  # Agent's session UUID from response

    # Timestamps for each major stage
    received_at = Column(DateTime, default=datetime_utcnow, index=True)
    processing_started_at = Column(DateTime)
    agent_request_at = Column(DateTime)
    agent_response_at = Column(DateTime)
    evolution_send_at = Column(DateTime)  # Alias: whatsapp_web_send_at
    completed_at = Column(DateTime)

    # Status tracking
    status = Column(
        String, default="received", index=True
    )  # received, processing, agent_called, completed, failed, access_denied
    error_message = Column(Text)
    error_stage = Column(String)  # Stage where error occurred

    # Access rule tracking
    blocked_by_access_rule = Column(Boolean, default=False, index=True)
    access_rule_id = Column(Integer, ForeignKey("omni_access_rules.id"), nullable=True)
    blocking_reason = Column(String)

    # Performance metrics
    agent_processing_time_ms = Column(Integer)
    total_processing_time_ms = Column(Integer)
    agent_request_tokens = Column(Integer)
    agent_response_tokens = Column(Integer)

    # Agent response metadata
    agent_response_success = Column(Boolean)
    agent_response_length = Column(Integer)
    agent_tools_used = Column(Integer, default=0)

    # WhatsApp Web API response (via Evolution API)
    # Use whatsapp_web_* property aliases for new code
    evolution_response_code = Column(Integer)  # Alias: whatsapp_web_response_code
    evolution_success = Column(Boolean)  # Alias: whatsapp_web_success

    # Relationships
    payloads = relationship("TracePayload", back_populates="trace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MessageTrace(trace_id='{self.trace_id}', status='{self.status}', sender='{self.sender_phone}')>"

    # WhatsApp Web API aliases (clean naming for evolution_* columns)
    @property
    def whatsapp_web_send_at(self) -> Optional[Any]:
        """Alias for evolution_send_at - WhatsApp Web API send timestamp."""
        return self.evolution_send_at

    @whatsapp_web_send_at.setter
    def whatsapp_web_send_at(self, value: Any) -> None:
        self.evolution_send_at = value

    @property
    def whatsapp_web_response_code(self) -> Optional[int]:
        """Alias for evolution_response_code - WhatsApp Web API response code."""
        return self.evolution_response_code

    @whatsapp_web_response_code.setter
    def whatsapp_web_response_code(self, value: Optional[int]) -> None:
        self.evolution_response_code = value

    @property
    def whatsapp_web_success(self) -> Optional[bool]:
        """Alias for evolution_success - WhatsApp Web API success status."""
        return self.evolution_success

    @whatsapp_web_success.setter
    def whatsapp_web_success(self, value: Optional[bool]) -> None:
        self.evolution_success = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for API responses."""
        return {
            "trace_id": self.trace_id,
            "instance_name": self.instance_name,
            "whatsapp_message_id": self.whatsapp_message_id,
            "sender_phone": self.sender_phone,
            "sender_name": self.sender_name,
            "message_type": self.message_type,
            "has_media": self.has_media,
            "has_quoted_message": self.has_quoted_message,
            "session_name": self.session_name,
            "agent_session_id": self.agent_session_id,
            "status": self.status,
            "error_message": self.error_message,
            "error_stage": self.error_stage,
            "blocked_by_access_rule": self.blocked_by_access_rule,
            "access_rule_id": self.access_rule_id,
            "blocking_reason": self.blocking_reason,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "agent_processing_time_ms": self.agent_processing_time_ms,
            "total_processing_time_ms": self.total_processing_time_ms,
            "agent_response_success": self.agent_response_success,
            "evolution_success": self.evolution_success,
        }


class TracePayload(Base):
    """
    Stores actual request/response payloads for each stage of message processing.
    Payloads are compressed to save space.
    """

    __tablename__ = "omni_trace_payloads"

    id = Column(Integer, primary_key=True)
    trace_id = Column(String, ForeignKey("omni_message_traces.trace_id"), index=True)

    # Stage and payload identification
    stage = Column(String, index=True)  # webhook_received, agent_request, agent_response, evolution_send
    payload_type = Column(String)  # request, response, webhook

    # Compressed payload data
    payload_compressed = Column(Text)  # Base64 encoded compressed JSON
    payload_size_original = Column(Integer)
    payload_size_compressed = Column(Integer)

    # Payload metadata
    timestamp = Column(DateTime, default=datetime_utcnow, index=True)
    status_code = Column(Integer)  # HTTP status codes
    error_details = Column(Text)

    # Content classification
    contains_media = Column(Boolean, default=False)
    contains_base64 = Column(Boolean, default=False)

    # Relationships
    trace = relationship("MessageTrace", back_populates="payloads")

    def set_payload(self, payload: Dict[str, Any]) -> None:
        """
        Store payload with compression.

        Args:
            payload: Dictionary to store
        """
        try:
            # Convert to JSON string
            json_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            self.payload_size_original = len(json_str)

            # Compress using zlib
            compressed_data = zlib.compress(json_str.encode("utf-8"))
            self.payload_size_compressed = len(compressed_data)

            # Encode as base64 for storage
            self.payload_compressed = base64.b64encode(compressed_data).decode("ascii")

            # Check content flags
            json_lower = json_str.lower()
            self.contains_base64 = "base64" in json_lower
            self.contains_media = any(media in json_lower for media in ["image", "video", "audio", "document", "media"])

        except Exception as e:
            # If compression fails, store error
            self.error_details = f"Payload compression failed: {str(e)}"
            self.payload_compressed = None

    def get_payload(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decompress payload.

        Returns:
            Original payload dictionary or None if decompression fails
        """
        if not self.payload_compressed:
            return None

        try:
            # Decode from base64
            compressed_data = base64.b64decode(self.payload_compressed.encode("ascii"))

            # Decompress
            json_str = zlib.decompress(compressed_data).decode("utf-8")

            # Parse JSON
            return json.loads(json_str)

        except Exception as e:
            # Log error but don't raise - this is for debugging
            return {"error": f"Payload decompression failed: {str(e)}"}

    def __repr__(self):
        return f"<TracePayload(trace_id='{self.trace_id}', stage='{self.stage}', type='{self.payload_type}')>"

    def to_dict(self, include_payload: bool = False) -> Dict[str, Any]:
        """Convert trace payload to dictionary for API responses."""
        result = {
            "id": self.id,
            "trace_id": self.trace_id,
            "stage": self.stage,
            "payload_type": self.payload_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status_code": self.status_code,
            "error_details": self.error_details,
            "payload_size_original": self.payload_size_original,
            "payload_size_compressed": self.payload_size_compressed,
            "compression_ratio": (
                round(self.payload_size_compressed / self.payload_size_original, 2)
                if self.payload_size_original
                else None
            ),
            "contains_media": self.contains_media,
            "contains_base64": self.contains_base64,
        }

        if include_payload:
            result["payload"] = self.get_payload()

        return result


class MediaContent(Base):
    """
    Processed media content extracted from messages.
    Stores transcriptions, image descriptions, and document content.
    Channel-agnostic - works for WhatsApp, Discord, and future channels.
    """

    __tablename__ = "omni_media_content"

    id = Column(Integer, primary_key=True)

    # Link to original message
    instance_name = Column(String(255), ForeignKey("omni_instance_configs.name"), index=True, nullable=False)
    channel_type = Column(String(20), nullable=False)  # 'whatsapp' or 'discord'
    original_message_id = Column(String(255), nullable=False, index=True)  # WhatsApp key.id or Discord message.id
    sender_id = Column(String(255), index=True)  # remoteJid for WhatsApp, user_id for Discord

    # Content type
    content_type = Column(
        String(50), nullable=False, index=True
    )  # 'audio_transcript', 'image_description', 'document_content'
    source_media_type = Column(String(50), nullable=False)  # 'audio', 'image', 'video', 'document'

    # Processed content
    content = Column(Text, nullable=False)  # The extracted/generated text
    content_format = Column(String(20), default="text")  # 'text', 'markdown', 'json'

    # Processing metadata
    processor_name = Column(String(100))  # 'groq_whisper', 'gemini_vision', 'docling', etc.
    processor_model = Column(String(100))  # 'whisper-large-v3-turbo', 'gemini-2.5-flash', etc.
    processing_time_ms = Column(Integer)
    confidence_score = Column(Integer)  # 0-100 confidence/quality score (stored as int for DB compat)

    # Token/usage tracking
    input_tokens = Column(Integer)  # Number of input tokens (for LLM-based processing)
    output_tokens = Column(Integer)  # Number of output tokens (for LLM responses)
    total_tokens = Column(Integer)  # Total tokens used

    # Cost tracking (in USD, using Numeric for precision)
    cost_input_usd = Column(Numeric(precision=10, scale=8))  # Cost for input processing
    cost_output_usd = Column(Numeric(precision=10, scale=8))  # Cost for output generation
    cost_total_usd = Column(Numeric(precision=10, scale=8))  # Total cost

    # Pricing metadata (for audit/debugging)
    pricing_model = Column(String(100))  # e.g., 'groq_whisper-large-v3-turbo'
    pricing_rate_input = Column(Numeric(precision=10, scale=8))  # Rate used for input
    pricing_rate_output = Column(Numeric(precision=10, scale=8))  # Rate used for output

    # Source media info (for re-download capability)
    media_url = Column(Text)
    media_mime_type = Column(String(100))
    media_size_bytes = Column(Integer)
    media_duration_seconds = Column(Integer)  # For audio/video
    media_key = Column(Text)  # WhatsApp media key for encrypted media (base64)

    # Status tracking
    status = Column(String(20), default="pending", index=True)  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow, index=True)
    processed_at = Column(DateTime)

    def __repr__(self):
        return f"<MediaContent(id={self.id}, type='{self.content_type}', msg='{self.original_message_id}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "instance_name": self.instance_name,
            "channel_type": self.channel_type,
            "original_message_id": self.original_message_id,
            "content_type": self.content_type,
            "source_media_type": self.source_media_type,
            "content": self.content,
            "content_format": self.content_format,
            "processor_name": self.processor_name,
            "processor_model": self.processor_model,
            "processing_time_ms": self.processing_time_ms,
            "confidence_score": self.confidence_score,
            # Token/usage tracking
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            # Cost tracking
            "cost_input_usd": float(self.cost_input_usd) if self.cost_input_usd else None,
            "cost_output_usd": float(self.cost_output_usd) if self.cost_output_usd else None,
            "cost_total_usd": float(self.cost_total_usd) if self.cost_total_usd else None,
            "pricing_model": self.pricing_model,
            # Media info
            "media_url": self.media_url,
            "media_mime_type": self.media_mime_type,
            "media_size_bytes": self.media_size_bytes,
            "media_duration_seconds": self.media_duration_seconds,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class BatchJob(Base):
    """
    Tracks batch processing jobs for async operations.
    Allows UI to poll for progress instead of waiting for completion.
    """

    __tablename__ = "omni_batch_jobs"

    # Job identification
    job_id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String(50), nullable=False, index=True)  # 'media_reprocess', 'sync_messages', etc.

    # Request context
    instance_name = Column(String(255), index=True)
    request_params = Column(Text)  # JSON of original request parameters

    # Progress tracking
    status = Column(String(20), default="pending", index=True)  # pending, processing, completed, failed, cancelled
    total_found = Column(Integer, default=0)  # Total items found matching criteria (before filtering)
    total_items = Column(Integer, default=0)  # Items to process (after filtering already-processed)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    skipped_items = Column(Integer, default=0)  # Already had MediaContent (not needing reprocess)

    # Current item being processed (for real-time progress)
    current_item = Column(String(255))  # e.g., trace_id or message_id being processed

    # Results summary
    results_summary = Column(Text)  # JSON summary of results
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime_utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Cost tracking (aggregate)
    total_cost_usd = Column(Numeric(precision=10, scale=8))
    total_tokens = Column(Integer)

    def __repr__(self):
        return f"<BatchJob(job_id='{self.job_id}', type='{self.job_type}', status='{self.status}', progress={self.processed_items}/{self.total_items})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        # Parse request_params JSON if available
        params = {}
        if self.request_params:
            try:
                params = json.loads(self.request_params)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "instance_name": self.instance_name,
            "request_params": params,  # Parsed JSON for UI display
            "status": self.status,
            "total_found": self.total_found or 0,  # Items found before filtering
            "total_items": self.total_items or 0,  # Items to process
            "processed_items": self.processed_items or 0,
            "failed_items": self.failed_items or 0,
            "skipped_items": self.skipped_items or 0,
            "current_item": self.current_item,
            "progress_percent": round((self.processed_items / self.total_items) * 100, 1)
            if self.total_items and self.total_items > 0
            else 0,
            "total_cost_usd": float(self.total_cost_usd) if self.total_cost_usd else None,
            "total_tokens": self.total_tokens,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class OmniMessageRecord(Base):
    """
    Unified message store that consolidates ALL messages from both webhooks and synced history.

    This is the central message table that enables:
    - Media processing on ALL messages (not just webhook-received)
    - Reduced dependency on Evolution API for message queries
    - Local message serving without Evolution API calls
    - Full reprocessing capability via stored content_raw

    Deduplication: Unique constraint on (instance_name, platform_message_id)
    """

    __tablename__ = "omni_messages"

    # Primary key: composite format {instance}:{platform_message_id}
    id = Column(String(512), primary_key=True)

    # Instance and chat linkage
    instance_name = Column(String(255), ForeignKey("omni_instance_configs.name"), nullable=False, index=True)
    channel_type = Column(String(20), nullable=False)  # 'whatsapp', 'discord'
    chat_id = Column(String(255), nullable=False)  # remoteJid for WhatsApp, channel_id for Discord
    canonical_chat_id = Column(String(255), nullable=True, index=True)  # Normalized chat ID for unified queries

    # Platform-specific identification
    platform_message_id = Column(String(255), nullable=False)  # WhatsApp key.id, Discord message.id
    platform_key = Column(Text)  # JSONB as Text: Full WhatsApp key object {id, remoteJid, fromMe, participant}

    # Direction and sender
    direction = Column(String(10), nullable=False)  # 'inbound', 'outbound'
    sender_id = Column(String(255), nullable=True)  # JID or user ID
    sender_name = Column(String(255), nullable=True)
    is_from_me = Column(Boolean, default=False, nullable=False)

    # Message content
    message_type = Column(String(50), nullable=False)  # 'text', 'audio', 'image', 'video', 'document', etc.
    content_text = Column(Text, nullable=True)  # Text content or caption
    content_raw = Column(Text)  # JSONB as Text: Raw platform-specific message object (for reprocessing)

    # Media information
    has_media = Column(Boolean, default=False, nullable=False)
    media_url = Column(Text, nullable=True)  # Original URL (may expire)
    media_local_path = Column(Text, nullable=True)  # Local file path after download
    media_mime_type = Column(String(100), nullable=True)
    media_size_bytes = Column(Integer, nullable=True)
    media_duration_seconds = Column(Integer, nullable=True)
    media_key = Column(Text, nullable=True)  # WhatsApp encryption key (base64)
    media_sha256 = Column(String(64), nullable=True)  # For deduplication
    media_status = Column(
        String(20), default="pending", nullable=False
    )  # pending, downloaded, processed, failed, expired

    # Context/threading
    quoted_message_id = Column(String(255), nullable=True)
    context_info = Column(Text)  # JSONB as Text

    # Delivery status (WhatsApp)
    delivery_status = Column(String(20), nullable=True)  # pending, sent, delivered, read, failed
    status_updated_at = Column(DateTime, nullable=True)

    # Source tracking (CRITICAL for this feature)
    source = Column(String(20), nullable=False)  # 'webhook', 'sync', 'api'
    sync_batch_id = Column(String(255), nullable=True)  # For tracking sync operations
    trace_id = Column(String(255), nullable=True, index=True)  # Link to omni_message_traces if from webhook

    # Timestamps
    message_timestamp = Column(DateTime, nullable=False)  # Original message time
    created_at = Column(DateTime, default=datetime_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow, nullable=False)
    synced_at = Column(DateTime, nullable=True)  # When imported from Evolution

    def __repr__(self):
        return f"<OmniMessageRecord(id='{self.id}', type='{self.message_type}', source='{self.source}')>"

    def get_platform_key(self) -> Optional[Dict[str, Any]]:
        """Parse platform_key - handles both JSONB (dict) and Text (string)."""
        if not self.platform_key:
            return None
        # If already a dict (from JSONB column), return directly
        if isinstance(self.platform_key, dict):
            return self.platform_key
        # If string, parse as JSON
        try:
            return json.loads(self.platform_key)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_platform_key(self, key: Dict[str, Any]) -> None:
        """Set platform_key as JSON string."""
        self.platform_key = json.dumps(key, ensure_ascii=False) if key else None

    def get_content_raw(self) -> Optional[Dict[str, Any]]:
        """Parse content_raw - handles both JSONB (dict) and Text (string)."""
        if not self.content_raw:
            return None
        if isinstance(self.content_raw, dict):
            return self.content_raw
        try:
            return json.loads(self.content_raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_content_raw(self, content: Dict[str, Any]) -> None:
        """Set content_raw as JSON string."""
        self.content_raw = json.dumps(content, ensure_ascii=False) if content else None

    def get_context_info(self) -> Optional[Dict[str, Any]]:
        """Parse context_info - handles both JSONB (dict) and Text (string)."""
        if not self.context_info:
            return None
        if isinstance(self.context_info, dict):
            return self.context_info
        try:
            return json.loads(self.context_info)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_context_info(self, info: Dict[str, Any]) -> None:
        """Set context_info as JSON string."""
        self.context_info = json.dumps(info, ensure_ascii=False) if info else None

    def to_dict(self, include_raw: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": self.id,
            "instance_name": self.instance_name,
            "channel_type": self.channel_type,
            "chat_id": self.chat_id,
            "canonical_chat_id": self.canonical_chat_id,
            "platform_message_id": self.platform_message_id,
            "platform_key": self.get_platform_key(),
            "direction": self.direction,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "is_from_me": self.is_from_me,
            "message_type": self.message_type,
            "content_text": self.content_text,
            "has_media": self.has_media,
            "media_url": self.media_url,
            "media_local_path": self.media_local_path,
            "media_mime_type": self.media_mime_type,
            "media_size_bytes": self.media_size_bytes,
            "media_duration_seconds": self.media_duration_seconds,
            "media_status": self.media_status,
            "quoted_message_id": self.quoted_message_id,
            "context_info": self.get_context_info(),
            "delivery_status": self.delivery_status,
            "status_updated_at": self.status_updated_at.isoformat() if self.status_updated_at else None,
            "source": self.source,
            "sync_batch_id": self.sync_batch_id,
            "trace_id": self.trace_id,
            "message_timestamp": self.message_timestamp.isoformat() if self.message_timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }

        if include_raw:
            result["content_raw"] = self.get_content_raw()

        return result

    @classmethod
    def generate_id(cls, instance_name: str, platform_message_id: str) -> str:
        """Generate composite primary key."""
        return f"{instance_name}:{platform_message_id}"


class ChatIdMapping(Base):
    """
    Maps alternate chat IDs to canonical chat IDs.

    WhatsApp uses different chat ID formats:
    - @s.whatsapp.net: Phone number format (e.g., 553488722041@s.whatsapp.net)
    - @lid: Linked device ID format (e.g., 179538357133535@lid)
    - @g.us: Group format

    The same contact can have multiple chat IDs depending on how messages are sent.
    This table stores known mappings to enable unified conversation queries.
    """

    __tablename__ = "omni_chat_id_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_name = Column(String(255), ForeignKey("omni_instance_configs.name"), nullable=False)

    # The canonical ID (usually @s.whatsapp.net format with phone number)
    canonical_chat_id = Column(String(255), nullable=False, index=True)

    # The alternative ID (@lid format)
    alternate_chat_id = Column(String(255), nullable=False, index=True)

    # Contact name for reference
    contact_name = Column(String(255), nullable=True)

    # Phone number extracted (if available)
    phone_number = Column(String(50), nullable=True)

    # How this mapping was discovered
    discovery_method = Column(String(50), nullable=True)  # 'sender_name', 'manual', 'api'

    created_at = Column(DateTime, default=datetime_utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime_utcnow, onupdate=datetime_utcnow, nullable=False)

    def __repr__(self):
        return f"<ChatIdMapping(canonical='{self.canonical_chat_id}', alternate='{self.alternate_chat_id}')>"
