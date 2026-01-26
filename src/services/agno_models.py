"""
Pydantic models for Agno API events and responses.
These models define the structure of events received from Agno's streaming API,
including RunStarted, RunResponseContent, and RunCompleted events.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from enum import Enum

logger = logging.getLogger(__name__)


class AgnoEventType(str, Enum):
    """Types of events received from Agno streaming API."""

    RUN_STARTED = "RunStarted"
    RUN_RESPONSE_CONTENT = "RunResponseContent"
    RUN_COMPLETED = "RunCompleted"
    ERROR = "Error"
    HEARTBEAT = "Heartbeat"


class BaseAgnoEvent(BaseModel):
    """Base class for all Agno events."""

    event: AgnoEventType = Field(..., description="Type of the event")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")
    run_id: Optional[str] = Field(None, description="Run ID associated with this event")

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        """Parse timestamp from various formats."""
        if v is None:
            return datetime.now(timezone.utc)
        if isinstance(v, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try common formats
                    return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    logger.warning(f"Could not parse timestamp: {v}")
                    return datetime.now(timezone.utc)
        return v


class RunStartedEvent(BaseAgnoEvent):
    """Event emitted when a run starts."""

    event: AgnoEventType = Field(default=AgnoEventType.RUN_STARTED)
    agent_id: Optional[str] = Field(None, description="Agent ID for the run")
    team_id: Optional[str] = Field(None, description="Team ID for the run")
    message: Optional[str] = Field(None, description="Initial message that started the run")


class RunResponseContentEvent(BaseAgnoEvent):
    """Event emitted with streaming response content."""

    event: AgnoEventType = Field(default=AgnoEventType.RUN_RESPONSE_CONTENT)
    content: str = Field(..., description="Streaming content chunk")
    delta: Optional[str] = Field(None, description="Content delta (alias for content)")

    @field_validator("content", mode="before")
    @classmethod
    def ensure_content(cls, v, info: ValidationInfo):
        """Ensure content is set from either content or delta field."""
        if v is None and info.data and "delta" in info.data:
            return info.data.get("delta", "")
        return v or ""


class RunCompletedEvent(BaseAgnoEvent):
    """Event emitted when a run completes."""

    event: AgnoEventType = Field(default=AgnoEventType.RUN_COMPLETED)
    content: Optional[str] = Field(None, description="Final complete response")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    completion_reason: Optional[str] = Field(None, description="Reason for completion")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ErrorEvent(BaseAgnoEvent):
    """Event emitted when an error occurs."""

    event: AgnoEventType = Field(default=AgnoEventType.ERROR)
    error_code: Optional[str] = Field(None, description="Error code")
    error_message: str = Field(..., description="Error description")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HeartbeatEvent(BaseAgnoEvent):
    """Heartbeat event to keep connection alive."""

    event: AgnoEventType = Field(default=AgnoEventType.HEARTBEAT)


# Union type for all possible events
AgnoEvent = Union[
    RunStartedEvent,
    RunResponseContentEvent,
    RunCompletedEvent,
    ErrorEvent,
    HeartbeatEvent,
]


class AgnoRunRequest(BaseModel):
    """Request model for creating a new run."""

    message: str = Field(..., description="Message to send to the agent/team")
    stream: bool = Field(default=True, description="Enable streaming response")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AgnoContinueRequest(BaseModel):
    """Request model for continuing a conversation."""

    message: str = Field(..., description="Follow-up message")
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AgnoRunResponse(BaseModel):
    """Response model for run creation."""

    run_id: str = Field(..., description="Unique run identifier")
    status: str = Field(..., description="Run status")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    team_id: Optional[str] = Field(None, description="Team ID")
    created_at: Optional[datetime] = Field(None, description="Run creation timestamp")


def parse_agno_event(event_data: Dict[str, Any]) -> AgnoEvent:
    """
    Parse raw event data into appropriate AgnoEvent model.

    Args:
        event_data: Raw event data from SSE stream

    Returns:
        Parsed AgnoEvent instance

    Raises:
        ValueError: If event data is invalid or unknown event type
    """
    if not isinstance(event_data, dict):
        raise ValueError(f"Event data must be a dictionary, got {type(event_data)}")

    event_type = event_data.get("event")
    if not event_type:
        raise ValueError("Event data missing 'event' field")

    try:
        event_enum = AgnoEventType(event_type)
    except ValueError:
        # Try to map common variations (snake_case to PascalCase)
        event_type_mapping = {
            "run_started": "RunStarted",
            "run_response_content": "RunResponseContent",
            "run_completed": "RunCompleted",
            "error": "Error",
            "heartbeat": "Heartbeat",
            # Team event mappings
            "teamrunresponseconteent": "RunResponseContent",
            "teamrunstarted": "RunStarted",
            "teamruncompleted": "RunCompleted",
        }

        mapped_type = event_type_mapping.get(event_type.lower())
        if mapped_type:
            logger.info(f"Mapping event type '{event_type}' to '{mapped_type}'")
            try:
                event_enum = AgnoEventType(mapped_type)
            except ValueError:
                logger.warning(f"Failed to map event type: {event_type} -> {mapped_type}")
                # Return as generic event
                return BaseAgnoEvent(**event_data)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            # Return as generic event
            return BaseAgnoEvent(**event_data)

    # Map to specific event classes
    event_class_map = {
        AgnoEventType.RUN_STARTED: RunStartedEvent,
        AgnoEventType.RUN_RESPONSE_CONTENT: RunResponseContentEvent,
        AgnoEventType.RUN_COMPLETED: RunCompletedEvent,
        AgnoEventType.ERROR: ErrorEvent,
        AgnoEventType.HEARTBEAT: HeartbeatEvent,
    }

    event_class = event_class_map.get(event_enum, BaseAgnoEvent)

    try:
        return event_class(**event_data)
    except Exception as e:
        logger.error(f"Failed to parse {event_type} event: {e}")
        logger.debug(f"Event data: {event_data}")
        # Fallback to base event
        return BaseAgnoEvent(event=event_enum, **{k: v for k, v in event_data.items() if k != "event"})


# Backward compatibility aliases (to be removed in future version)
HiveEventType = AgnoEventType
BaseHiveEvent = BaseAgnoEvent
HiveEvent = AgnoEvent
HiveRunRequest = AgnoRunRequest
HiveContinueRequest = AgnoContinueRequest
HiveRunResponse = AgnoRunResponse
parse_hive_event = parse_agno_event
