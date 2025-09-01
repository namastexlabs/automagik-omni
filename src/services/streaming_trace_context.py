"""
Enhanced Trace Context for Streaming Responses

This module extends the base trace context to properly handle streaming responses
from hive agents, capturing first token timing, incremental content, and final
output for accurate trace analysis.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import utcnow

# Import TYPE_CHECKING to avoid circular import
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.trace_service import TraceContext
else:
    # Import at runtime to avoid circular dependency
    import src.services.trace_service

    TraceContext = src.services.trace_service.TraceContext

logger = logging.getLogger(__name__)


@dataclass
class StreamingMetrics:
    """Metrics for streaming response analysis."""

    first_token_time: Optional[datetime] = None
    final_token_time: Optional[datetime] = None
    total_tokens: int = 0
    total_chunks: int = 0
    accumulated_content: str = ""
    streaming_events: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.streaming_events is None:
            self.streaming_events = []


class StreamingTraceContext(TraceContext):
    """
    Enhanced trace context for streaming responses.

    Extends the base TraceContext to properly capture:
    - First token timing (time to first content)
    - Incremental content accumulation
    - Final complete response
    - Streaming event metadata
    """

    def __init__(self, trace_id: str, db_session):
        super().__init__(trace_id, db_session)
        self.streaming_metrics = StreamingMetrics()
        self._request_start_time = None
        self._agent_called_time = None

    def log_agent_request(self, agent_payload: Dict[str, Any]) -> None:
        """Log agent API request payload and start timing."""
        self._request_start_time = time.time()
        self._agent_called_time = utcnow()

        # Log the initial request
        super().log_agent_request(agent_payload)

        # Add streaming-specific payload info
        streaming_info = {
            "stream_mode": True,
            "trace_type": "streaming",
            "request_timestamp": self._agent_called_time.isoformat(),
        }

        enhanced_payload = {**agent_payload, **streaming_info}
        self.log_stage("streaming_request", enhanced_payload, "request")

    def log_streaming_start(self, stream_config: Dict[str, Any]) -> None:
        """Log the start of streaming response."""
        stream_start_payload = {
            "streaming_started": True,
            "stream_config": stream_config,
            "timestamp": utcnow().isoformat(),
        }
        self.log_stage("streaming_start", stream_start_payload, "stream_event")

    def log_first_token(self, first_content: str, event_data: Dict[str, Any] = None) -> None:
        """Log the first token/content received from streaming."""
        if self.streaming_metrics.first_token_time is None:
            self.streaming_metrics.first_token_time = utcnow()

            # Calculate first token latency
            if self._request_start_time:
                first_token_latency_ms = int((time.time() - self._request_start_time) * 1000)
            else:
                first_token_latency_ms = 0

            first_token_payload = {
                "first_token_received": True,
                "first_content": first_content[:200],  # Truncate for storage
                "first_token_latency_ms": first_token_latency_ms,
                "timestamp": self.streaming_metrics.first_token_time.isoformat(),
                "event_data": event_data or {},
            }

            self.log_stage("first_token", first_token_payload, "stream_event")
            logger.info(f"First token received in {first_token_latency_ms}ms")

    def log_streaming_chunk(self, chunk_content: str, chunk_index: int, event_data: Dict[str, Any] = None) -> None:
        """Log a streaming content chunk."""
        self.streaming_metrics.total_chunks += 1
        self.streaming_metrics.accumulated_content += chunk_content

        # Store event for analysis
        chunk_event = {
            "chunk_index": chunk_index,
            "content": chunk_content,
            "timestamp": utcnow().isoformat(),
            "event_data": event_data or {},
        }
        self.streaming_metrics.streaming_events.append(chunk_event)

        # Log significant chunks (every 10th or large chunks)
        if chunk_index % 10 == 0 or len(chunk_content) > 500:
            chunk_payload = {
                "chunk_index": chunk_index,
                "chunk_size": len(chunk_content),
                "total_chunks_so_far": self.streaming_metrics.total_chunks,
                "accumulated_size": len(self.streaming_metrics.accumulated_content),
                "content_preview": chunk_content[:100],
                "timestamp": utcnow().isoformat(),
            }
            self.log_stage("streaming_chunk", chunk_payload, "stream_event")

    def log_streaming_complete(self, final_content: str, completion_data: Dict[str, Any] = None) -> None:
        """Log the completion of streaming response with full content."""
        self.streaming_metrics.final_token_time = utcnow()

        # Calculate total streaming time
        if self._request_start_time:
            total_streaming_time_ms = int((time.time() - self._request_start_time) * 1000)
        else:
            total_streaming_time_ms = 0

        # Calculate first-token-to-final timing
        if self.streaming_metrics.first_token_time and self._agent_called_time:
            first_to_final_ms = int(
                (self.streaming_metrics.final_token_time - self.streaming_metrics.first_token_time).total_seconds()
                * 1000
            )
        else:
            first_to_final_ms = 0

        # Prepare comprehensive completion payload
        completion_payload = {
            "streaming_completed": True,
            "final_content": final_content,
            "total_streaming_time_ms": total_streaming_time_ms,
            "first_to_final_ms": first_to_final_ms,
            "total_chunks": self.streaming_metrics.total_chunks,
            "total_content_length": len(final_content),
            "completion_timestamp": self.streaming_metrics.final_token_time.isoformat(),
            "streaming_events_count": len(self.streaming_metrics.streaming_events),
            "completion_data": completion_data or {},
        }

        # Log the completion
        self.log_stage("streaming_complete", completion_payload, "stream_event")

        # Now log as standard agent response for compatibility
        agent_response = {
            "message": final_content,
            "success": True,
            "streaming": True,
            "metrics": {
                "total_streaming_time_ms": total_streaming_time_ms,
                "first_token_latency_ms": completion_payload.get("first_token_latency_ms", 0),
                "first_to_final_ms": first_to_final_ms,
                "total_chunks": self.streaming_metrics.total_chunks,
            },
        }

        super().log_agent_response(
            agent_response=agent_response, processing_time_ms=total_streaming_time_ms, status_code=200
        )

        # Update final trace status with streaming metrics
        self.update_trace_status(
            status="completed",
            agent_response_at=self.streaming_metrics.final_token_time,
            agent_processing_time_ms=total_streaming_time_ms,
            agent_response_success=True,
            agent_response_length=len(final_content),
            agent_tools_used=0,  # Will be updated if tools were used
        )

        logger.info(
            f"Streaming completed: {total_streaming_time_ms}ms total, {self.streaming_metrics.total_chunks} chunks"
        )

    def log_streaming_error(self, error: Exception, error_stage: str = "streaming") -> None:
        """Log streaming error with context."""
        error_payload = {
            "streaming_error": True,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "error_stage": error_stage,
            "timestamp": utcnow().isoformat(),
            "partial_content": self.streaming_metrics.accumulated_content[:200]
            if self.streaming_metrics.accumulated_content
            else None,
            "chunks_received": self.streaming_metrics.total_chunks,
        }

        self.log_stage("streaming_error", error_payload, "error")

        # Update trace status to error
        self.update_trace_status(
            status="error", error_message=str(error), error_stage=error_stage, agent_response_success=False
        )

        logger.error(f"Streaming error in {error_stage}: {error}")

    def get_streaming_summary(self) -> Dict[str, Any]:
        """Get a summary of streaming metrics for analysis."""
        if not self.streaming_metrics.first_token_time:
            return {"status": "no_streaming_data"}

        summary = {
            "first_token_time": self.streaming_metrics.first_token_time.isoformat(),
            "total_chunks": self.streaming_metrics.total_chunks,
            "total_content_length": len(self.streaming_metrics.accumulated_content),
            "events_captured": len(self.streaming_metrics.streaming_events),
        }

        if self.streaming_metrics.final_token_time:
            summary["final_token_time"] = self.streaming_metrics.final_token_time.isoformat()
            summary["total_streaming_duration_ms"] = int(
                (self.streaming_metrics.final_token_time - self.streaming_metrics.first_token_time).total_seconds()
                * 1000
            )
            summary["status"] = "completed"
        else:
            summary["status"] = "incomplete"

        return summary


def create_streaming_trace_context(
    instance_name: str,
    whatsapp_message_id: str,
    sender_phone: str,
    sender_name: str,
    sender_jid: str,
    message_type: str = "text",
    **kwargs,
) -> Optional[StreamingTraceContext]:
    """
    Create a streaming-aware trace context using the database.

    Args:
        instance_name: Name of the instance
        whatsapp_message_id: WhatsApp message ID
        sender_phone: Sender phone number
        sender_name: Sender display name
        sender_jid: Sender JID
        message_type: Message type (default: "text")
        **kwargs: Additional parameters for base TraceContext

    Returns:
        StreamingTraceContext instance or None if tracing disabled
    """
    from src.db.database import get_db
    from src.services.trace_service import TraceService

    # Create message data structure that TraceService expects
    message_data = {
        "data": {
            "key": {"id": whatsapp_message_id, "remoteJid": sender_jid},
            "message": {
                "conversation": kwargs.get("message_text", ""),
                "messageContextInfo": {"deviceListMetadata": {}, "deviceListMetadataVersion": 2},
            },
            "messageTimestamp": int(time.time()),
            "pushName": sender_name,
            "status": "PENDING",
        },
        "destination": instance_name,
        "server_url": "streaming_test",
    }

    # Get database session
    try:
        db = next(get_db())

        # Create trace using TraceService
        streaming_trace = TraceService.create_streaming_trace(message_data, instance_name, db)

        return streaming_trace

    except Exception as e:
        logger.error(f"Failed to create streaming trace context: {e}")
        return None
