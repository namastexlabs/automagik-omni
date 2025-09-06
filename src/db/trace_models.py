"""
SQLAlchemy models for message tracing system.
Tracks the complete lifecycle of messages through the Omni-Hub system.
"""

import uuid
import json
import zlib
import base64
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from typing import Dict, Any, Optional
from .database import Base
from src.utils.datetime_utils import datetime_utcnow


class MessageTrace(Base):
    """
    Main message trace model that tracks the complete lifecycle of a message
    from webhook reception to final response delivery.
    """

    __tablename__ = "message_traces"

    # Unique trace ID for the entire message lifecycle
    trace_id = Column(
        String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())
    )

    # Instance and message identification
    instance_name = Column(String, ForeignKey("instance_configs.name"), index=True)
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
    evolution_send_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Status tracking
    status = Column(
        String, default="received", index=True
    )  # received, processing, agent_called, completed, failed
    error_message = Column(Text)
    error_stage = Column(String)  # Stage where error occurred

    # Performance metrics
    agent_processing_time_ms = Column(Integer)
    total_processing_time_ms = Column(Integer)
    agent_request_tokens = Column(Integer)
    agent_response_tokens = Column(Integer)

    # Agent response metadata
    agent_response_success = Column(Boolean)
    agent_response_length = Column(Integer)
    agent_tools_used = Column(Integer, default=0)

    # Evolution API response
    evolution_response_code = Column(Integer)
    evolution_success = Column(Boolean)

    # Relationships
    payloads = relationship(
        "TracePayload", back_populates="trace", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MessageTrace(trace_id='{self.trace_id}', status='{self.status}', sender='{self.sender_phone}')>"

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
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
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

    __tablename__ = "trace_payloads"

    id = Column(Integer, primary_key=True)
    trace_id = Column(String, ForeignKey("message_traces.trace_id"), index=True)

    # Stage and payload identification
    stage = Column(
        String, index=True
    )  # webhook_received, agent_request, agent_response, evolution_send
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
            self.contains_media = any(
                media in json_lower
                for media in ["image", "video", "audio", "document", "media"]
            )

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
