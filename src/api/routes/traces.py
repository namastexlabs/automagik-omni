"""
Message Trace API endpoints.
Provides endpoints for querying message traces and analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel

from src.api.deps import get_database, verify_api_key
from src.db.trace_models import MessageTrace
from src.services.trace_service import TraceService

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API responses
class TraceResponse(BaseModel):
    """Response model for message trace."""

    trace_id: str
    instance_name: str
    whatsapp_message_id: Optional[str]
    sender_phone: Optional[str]
    sender_name: Optional[str]
    message_type: Optional[str]
    has_media: bool
    has_quoted_message: bool
    session_name: Optional[str]
    agent_session_id: Optional[str]
    status: str
    error_message: Optional[str]
    error_stage: Optional[str]
    received_at: Optional[str]
    completed_at: Optional[str]
    agent_processing_time_ms: Optional[int]
    total_processing_time_ms: Optional[int]
    agent_response_success: Optional[bool]
    evolution_success: Optional[bool]

    class Config:
        from_attributes = True


class TracePayloadResponse(BaseModel):
    """Response model for trace payload."""

    id: int
    trace_id: str
    stage: str
    payload_type: str
    timestamp: Optional[str]
    status_code: Optional[int]
    error_details: Optional[str]
    payload_size_original: Optional[int]
    payload_size_compressed: Optional[int]
    compression_ratio: Optional[float]
    contains_media: bool
    contains_base64: bool
    payload: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class TraceAnalytics(BaseModel):
    """Analytics response model."""

    total_messages: int
    successful_messages: int
    failed_messages: int
    success_rate: float
    avg_processing_time_ms: Optional[float]
    avg_agent_time_ms: Optional[float]
    message_types: Dict[str, int]
    error_stages: Dict[str, int]
    instances: Dict[str, int]


class TraceQuery(BaseModel):
    """Query parameters for trace search."""

    phone: Optional[str] = None
    instance_name: Optional[str] = None
    status: Optional[str] = None
    message_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


@router.get("/traces", response_model=List[TraceResponse])
async def list_traces(
    phone: Optional[str] = Query(None, description="Filter by sender phone number"),
    instance_name: Optional[str] = Query(None, description="Filter by instance name"),
    status: Optional[str] = Query(
        None, description="Filter by status (received, processing, completed, failed)"
    ),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    start_date: Optional[datetime] = Query(
        None, description="Start date filter (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End date filter (ISO format)"
    ),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of traces to return"
    ),
    offset: int = Query(0, ge=0, description="Number of traces to skip"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """List message traces with optional filtering."""

    try:
        query = db.query(MessageTrace)

        # Apply filters
        if phone:
            query = query.filter(MessageTrace.sender_phone == phone)
        if instance_name:
            query = query.filter(MessageTrace.instance_name == instance_name)
        if status:
            query = query.filter(MessageTrace.status == status)
        if message_type:
            query = query.filter(MessageTrace.message_type == message_type)
        if start_date:
            query = query.filter(MessageTrace.received_at >= start_date)
        if end_date:
            query = query.filter(MessageTrace.received_at <= end_date)

        # Order by most recent first
        query = query.order_by(desc(MessageTrace.received_at))

        # Apply pagination
        traces = query.offset(offset).limit(limit).all()

        return [TraceResponse(**trace.to_dict()) for trace in traces]

    except Exception as e:
        logger.error(f"Error listing traces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list traces: {str(e)}",
        )


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get a specific trace by ID."""

    try:
        trace = TraceService.get_trace(trace_id, db)
        if not trace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trace '{trace_id}' not found",
            )

        return TraceResponse(**trace.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace {trace_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trace: {str(e)}",
        )


@router.get("/traces/{trace_id}/payloads", response_model=List[TracePayloadResponse])
async def get_trace_payloads(
    trace_id: str,
    include_payload: bool = Query(
        False, description="Include actual payload data in response"
    ),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get all payloads for a specific trace."""

    try:
        # Verify trace exists
        trace = TraceService.get_trace(trace_id, db)
        if not trace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trace '{trace_id}' not found",
            )

        payloads = TraceService.get_trace_payloads(trace_id, db)

        response_payloads = []
        for payload in payloads:
            payload_dict = payload.to_dict(include_payload=include_payload)
            response_payloads.append(TracePayloadResponse(**payload_dict))

        return response_payloads

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payloads for trace {trace_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trace payloads: {str(e)}",
        )


@router.get("/traces/analytics/summary", response_model=TraceAnalytics)
async def get_trace_analytics(
    start_date: Optional[datetime] = Query(
        None, description="Start date for analytics (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End date for analytics (ISO format)"
    ),
    instance_name: Optional[str] = Query(None, description="Filter by instance name"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get analytics summary for message traces."""

    try:
        # Default to last 24 hours if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(hours=24)
        if not end_date:
            end_date = datetime.utcnow()

        query = db.query(MessageTrace).filter(
            and_(
                MessageTrace.received_at >= start_date,
                MessageTrace.received_at <= end_date,
            )
        )

        if instance_name:
            query = query.filter(MessageTrace.instance_name == instance_name)

        # Get all traces for the period
        traces = query.all()

        # Calculate basic metrics
        total_messages = len(traces)
        successful_messages = len([t for t in traces if t.status == "completed"])
        failed_messages = len([t for t in traces if t.status == "failed"])
        success_rate = (
            (successful_messages / total_messages * 100) if total_messages > 0 else 0
        )

        # Calculate average processing times
        completed_traces = [t for t in traces if t.total_processing_time_ms is not None]
        avg_processing_time = (
            sum(t.total_processing_time_ms for t in completed_traces)
            / len(completed_traces)
            if completed_traces
            else None
        )

        agent_traces = [t for t in traces if t.agent_processing_time_ms is not None]
        avg_agent_time = (
            sum(t.agent_processing_time_ms for t in agent_traces) / len(agent_traces)
            if agent_traces
            else None
        )

        # Group by message types
        message_types = {}
        for trace in traces:
            msg_type = trace.message_type or "unknown"
            message_types[msg_type] = message_types.get(msg_type, 0) + 1

        # Group by error stages
        error_stages = {}
        for trace in traces:
            if trace.error_stage:
                error_stages[trace.error_stage] = (
                    error_stages.get(trace.error_stage, 0) + 1
                )

        # Group by instances
        instances = {}
        for trace in traces:
            inst_name = trace.instance_name or "unknown"
            instances[inst_name] = instances.get(inst_name, 0) + 1

        return TraceAnalytics(
            total_messages=total_messages,
            successful_messages=successful_messages,
            failed_messages=failed_messages,
            success_rate=round(success_rate, 2),
            avg_processing_time_ms=(
                round(avg_processing_time, 2) if avg_processing_time else None
            ),
            avg_agent_time_ms=round(avg_agent_time, 2) if avg_agent_time else None,
            message_types=message_types,
            error_stages=error_stages,
            instances=instances,
        )

    except Exception as e:
        logger.error(f"Error getting trace analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}",
        )


@router.get("/traces/phone/{phone_number}", response_model=List[TraceResponse])
async def get_traces_by_phone(
    phone_number: str,
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of traces to return"
    ),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get recent traces for a specific phone number."""

    try:
        traces = TraceService.get_traces_by_phone(phone_number, limit, db)
        return [TraceResponse(**trace.to_dict()) for trace in traces]

    except Exception as e:
        logger.error(f"Error getting traces for phone {phone_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get traces for phone number: {str(e)}",
        )


@router.delete("/traces/cleanup")
async def cleanup_old_traces(
    days_old: int = Query(
        30, ge=1, le=365, description="Delete traces older than this many days"
    ),
    dry_run: bool = Query(
        True, description="If true, return count without actually deleting"
    ),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Clean up old traces (admin endpoint)."""

    try:
        if dry_run:
            # Count traces that would be deleted
            from datetime import timedelta

            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            count = (
                db.query(MessageTrace)
                .filter(MessageTrace.received_at < cutoff_date)
                .count()
            )

            return {
                "status": "dry_run",
                "traces_to_delete": count,
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"Would delete {count} traces older than {days_old} days",
            }
        else:
            # Actually delete traces
            deleted_count = TraceService.cleanup_old_traces(days_old, db)

            return {
                "status": "completed",
                "traces_deleted": deleted_count,
                "message": f"Deleted {deleted_count} traces older than {days_old} days",
            }

    except Exception as e:
        logger.error(f"Error during trace cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup traces: {str(e)}",
        )
