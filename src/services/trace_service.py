"""
Message Trace Service
Manages the lifecycle of message traces through the Omni-Hub system.
"""

import time
import logging
import uuid
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from sqlalchemy.orm import Session

from src.config import config
from src.db.database import get_db
from src.db.trace_models import MessageTrace, TracePayload
from src.utils.datetime_utils import utcnow

logger = logging.getLogger(__name__)


class TraceContext:
    """
    Context object that follows a message through its complete lifecycle.
    Provides methods to log each stage and update trace status.
    """

    def __init__(self, trace_id: str, db_session: Session):
        self.trace_id = trace_id
        self.db_session = db_session
        self.start_time = time.time()
        self._stage_start_times = {}

    def log_stage(
        self,
        stage: str,
        payload: Dict[str, Any],
        payload_type: str = "request",
        status_code: Optional[int] = None,
        error_details: Optional[str] = None,
    ) -> None:
        """
        Log a payload for a specific stage of processing.

        Args:
            stage: Processing stage (webhook_received, agent_request, etc.)
            payload: Dictionary payload to store
            payload_type: Type of payload (request, response, webhook)
            status_code: HTTP status code if applicable
            error_details: Error message if something went wrong
        """
        if not config.tracing.enabled:
            return

        try:
            trace_payload = TracePayload(
                trace_id=self.trace_id,
                stage=stage,
                payload_type=payload_type,
                status_code=status_code,
                error_details=error_details,
            )

            # Set compressed payload
            trace_payload.set_payload(payload)

            # Add to database session
            self.db_session.add(trace_payload)
            self.db_session.commit()

            logger.debug(
                f"Logged {stage} payload for trace {self.trace_id} (compressed: {trace_payload.payload_size_compressed} bytes)"
            )

        except Exception as e:
            logger.error(f"Failed to log trace payload for {stage}: {e}")
            # Don't let tracing failures break message processing

    def update_trace_status(
        self,
        status: str,
        error_message: Optional[str] = None,
        error_stage: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Update the main trace record with status and metadata.

        Args:
            status: New status (processing, completed, failed, etc.)
            error_message: Error message if status is failed
            error_stage: Stage where error occurred
            **kwargs: Additional fields to update on the trace
        """
        if not config.tracing.enabled:
            return

        try:
            trace = (
                self.db_session.query(MessageTrace)
                .filter(MessageTrace.trace_id == self.trace_id)
                .first()
            )

            if trace:
                trace.status = status
                if error_message:
                    trace.error_message = error_message
                if error_stage:
                    trace.error_stage = error_stage

                # Update any additional fields passed as kwargs
                for key, value in kwargs.items():
                    if hasattr(trace, key):
                        setattr(trace, key, value)

                # Update total processing time if completing
                if status in ["completed", "failed"]:
                    trace.completed_at = utcnow()
                    if trace.received_at:
                        # Ensure both datetimes are timezone-aware for subtraction
                        from src.utils.datetime_utils import to_utc

                        completed_utc = (
                            to_utc(trace.completed_at)
                            if trace.completed_at.tzinfo is None
                            else trace.completed_at
                        )
                        received_utc = (
                            to_utc(trace.received_at)
                            if trace.received_at.tzinfo is None
                            else trace.received_at
                        )
                        delta = completed_utc - received_utc
                        trace.total_processing_time_ms = int(
                            delta.total_seconds() * 1000
                        )

                self.db_session.commit()
                logger.debug(f"Updated trace {self.trace_id} status to {status}")
            else:
                logger.warning(f"Trace {self.trace_id} not found for status update")

        except Exception as e:
            logger.error(f"Failed to update trace status: {e}")

    def log_agent_request(self, agent_payload: Dict[str, Any]) -> None:
        """Log agent API request payload."""
        self.log_stage("agent_request", agent_payload, "request")
        self.update_trace_status("agent_called", agent_request_at=utcnow())

    def log_agent_response(
        self,
        agent_response: Dict[str, Any],
        processing_time_ms: int,
        status_code: int = 200,
    ) -> None:
        """Log agent API response payload with timing."""
        self.log_stage("agent_response", agent_response, "response", status_code)

        # Extract agent response metadata
        success = agent_response.get("success", True)
        message_length = len(str(agent_response.get("message", "")))
        usage = agent_response.get("usage", {})
        tools_used = len(agent_response.get("tool_calls", []))

        self.update_trace_status(
            "processing",
            agent_response_at=utcnow(),
            agent_processing_time_ms=processing_time_ms,
            agent_response_success=success,
            agent_response_length=message_length,
            agent_tools_used=tools_used,
            agent_session_id=agent_response.get("session_id"),
            agent_request_tokens=usage.get("request_tokens"),
            agent_response_tokens=usage.get("response_tokens"),
        )

    def log_evolution_send(
        self, send_payload: Dict[str, Any], response_code: int, success: bool
    ) -> None:
        """Log Evolution API send attempt."""
        self.log_stage("evolution_send", send_payload, "request", response_code)

        final_status = "completed" if success else "failed"
        error_msg = None if success else f"Evolution API returned {response_code}"

        self.update_trace_status(
            final_status,
            error_message=error_msg,
            error_stage="evolution_send" if not success else None,
            evolution_send_at=utcnow(),
            evolution_response_code=response_code,
            evolution_success=success,
        )


class TraceService:
    """
    Main service for managing message traces.
    Provides high-level operations for trace management.
    """

    @staticmethod
    def create_trace(
        message_data: Dict[str, Any], instance_name: str, db_session: Session
    ) -> Optional[TraceContext]:
        """
        Create a new message trace and return a context object.

        Args:
            message_data: Incoming webhook message data
            instance_name: Instance name processing the message
            db_session: Database session

        Returns:
            TraceContext object or None if tracing disabled
        """
        if not config.tracing.enabled:
            return None

        try:
            # Extract message metadata
            data = message_data.get("data", {})
            key = data.get("key", {})
            message_obj = data.get("message", {})

            # Generate trace ID
            trace_id = str(uuid.uuid4())

            # Determine message type and metadata
            message_type = TraceService._determine_message_type(message_obj)
            has_media = TraceService._has_media(message_obj)
            has_quoted = "contextInfo" in data and "quotedMessage" in data.get(
                "contextInfo", {}
            )

            # Extract message content length
            message_length = 0
            if "conversation" in message_obj:
                message_length = len(message_obj["conversation"])
            elif "extendedTextMessage" in message_obj:
                message_length = len(message_obj["extendedTextMessage"].get("text", ""))

            # Create trace record
            trace = MessageTrace(
                trace_id=trace_id,
                instance_name=instance_name,
                whatsapp_message_id=key.get("id"),
                sender_phone=TraceService._extract_phone(key.get("remoteJid", "")),
                sender_name=data.get("pushName"),
                sender_jid=key.get("remoteJid"),
                message_type=message_type,
                has_media=has_media,
                has_quoted_message=has_quoted,
                message_length=message_length,
                status="received",
            )

            # Save to database
            db_session.add(trace)
            db_session.commit()

            # Create context object
            context = TraceContext(trace_id, db_session)

            # Log the initial webhook payload
            context.log_stage("webhook_received", message_data, "webhook")

            logger.info(
                f"Created message trace {trace_id} for message {key.get('id')} from {trace.sender_phone}"
            )

            return context

        except Exception as e:
            logger.error(f"Failed to create message trace: {e}")
            return None

    @staticmethod
    def get_trace(trace_id: str, db_session: Session) -> Optional[MessageTrace]:
        """Get a trace by ID."""
        try:
            return (
                db_session.query(MessageTrace)
                .filter(MessageTrace.trace_id == trace_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Failed to get trace {trace_id}: {e}")
            return None

    @staticmethod
    def get_traces_by_phone(
        phone: str, limit: int = 50, db_session: Session = None
    ) -> List[MessageTrace]:
        """Get recent traces for a phone number."""
        if not db_session:
            db_session = next(get_db())

        try:
            return (
                db_session.query(MessageTrace)
                .filter(MessageTrace.sender_phone == phone)
                .order_by(MessageTrace.received_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Failed to get traces for phone {phone}: {e}")
            return []

    @staticmethod
    def get_trace_payloads(trace_id: str, db_session: Session) -> List[TracePayload]:
        """Get all payloads for a trace."""
        try:
            return (
                db_session.query(TracePayload)
                .filter(TracePayload.trace_id == trace_id)
                .order_by(TracePayload.timestamp.asc())
                .all()
            )
        except Exception as e:
            logger.error(f"Failed to get payloads for trace {trace_id}: {e}")
            return []

    @staticmethod
    def cleanup_old_traces(days_old: int = 30, db_session: Session = None) -> int:
        """
        Clean up traces older than specified days.

        Args:
            days_old: Delete traces older than this many days
            db_session: Database session

        Returns:
            Number of traces deleted
        """
        if not db_session:
            db_session = next(get_db())

        try:
            from datetime import timedelta

            cutoff_date = utcnow() - timedelta(days=days_old)

            # Delete old traces (payloads will be deleted via cascade)
            deleted_count = (
                db_session.query(MessageTrace)
                .filter(MessageTrace.received_at < cutoff_date)
                .delete()
            )

            db_session.commit()
            logger.info(f"Cleaned up {deleted_count} traces older than {days_old} days")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old traces: {e}")
            return 0

    @staticmethod
    def _determine_message_type(message_obj: Dict[str, Any]) -> str:
        """Determine message type from message object."""
        if "conversation" in message_obj:
            return "text"
        elif "extendedTextMessage" in message_obj:
            return "text"
        elif "imageMessage" in message_obj:
            return "image"
        elif "videoMessage" in message_obj:
            return "video"
        elif "audioMessage" in message_obj:
            return "audio"
        elif "documentMessage" in message_obj:
            return "document"
        else:
            return "unknown"

    @staticmethod
    def _has_media(message_obj: Dict[str, Any]) -> bool:
        """Check if message contains media."""
        media_types = [
            "imageMessage",
            "videoMessage",
            "audioMessage",
            "documentMessage",
        ]
        return any(media_type in message_obj for media_type in media_types)

    @staticmethod
    def _extract_phone(jid: str) -> str:
        """Extract phone number from WhatsApp JID."""
        if "@" in jid:
            return jid.split("@")[0]
        return jid


@contextmanager
def get_trace_context(
    message_data: Dict[str, Any], instance_name: str
) -> Optional[TraceContext]:
    """
    Context manager for message tracing.

    Usage:
        with get_trace_context(webhook_data, instance_name) as trace:
            if trace:
                trace.log_agent_request(agent_payload)
                # ... processing ...
                trace.log_agent_response(agent_response, timing)
    """
    db = next(get_db())
    trace_context = None

    try:
        trace_context = TraceService.create_trace(message_data, instance_name, db)
        if trace_context:
            trace_context.update_trace_status(
                "processing", processing_started_at=utcnow()
            )
        yield trace_context
    except Exception as e:
        if trace_context:
            trace_context.update_trace_status(
                "failed", error_message=str(e), error_stage="processing"
            )
        logger.error(f"Error in trace context: {e}")
        yield trace_context
    finally:
        db.close()
