"""
Media Content API endpoints.
Provides endpoints for managing processed media content (transcriptions, descriptions).
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.api.deps import get_database, verify_api_key
from src.db.trace_models import MediaContent
from src.services.media_processing import media_processing_service

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for API
class MediaContentResponse(BaseModel):
    """Response model for media content."""

    id: int
    instance_name: str
    channel_type: str
    original_message_id: str
    content_type: str
    source_media_type: str
    content: str
    content_format: str
    processor_name: Optional[str] = None
    processor_model: Optional[str] = None
    processing_time_ms: Optional[int] = None
    confidence_score: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchReprocessRequest(BaseModel):
    """Request model for batch reprocessing."""

    instance_name: Optional[str] = None
    days_back: int = 30
    limit: int = 100
    language: str = "pt"
    content_types: List[str] = ["audio"]  # audio, image, document (supports all three)


class BatchReprocessResponse(BaseModel):
    """Response model for batch reprocessing."""

    total: int
    processed: int
    failed: int
    skipped: int
    results: List[dict]


class ReprocessTraceRequest(BaseModel):
    """Request model for single trace reprocessing."""

    trace_id: str
    language: str = "pt"


@router.get("/media-content", response_model=List[MediaContentResponse])
async def list_media_content(
    instance_name: Optional[str] = Query(None, description="Filter by instance"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """List processed media content."""
    try:
        query = db.query(MediaContent)

        if instance_name:
            query = query.filter(MediaContent.instance_name == instance_name)
        if content_type:
            query = query.filter(MediaContent.content_type == content_type)
        if status_filter:
            query = query.filter(MediaContent.status == status_filter)

        query = query.order_by(MediaContent.created_at.desc())
        results = query.offset(offset).limit(limit).all()

        return results

    except Exception as e:
        logger.error(f"Error listing media content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media-content/{message_id}", response_model=MediaContentResponse)
async def get_media_content(
    message_id: str,
    instance_name: Optional[str] = Query(None, description="Instance name"),
    content_type: str = Query("audio_transcript", description="Content type"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get processed content for a specific message."""
    try:
        query = db.query(MediaContent).filter(
            MediaContent.original_message_id == message_id,
            MediaContent.content_type == content_type,
        )

        if instance_name:
            query = query.filter(MediaContent.instance_name == instance_name)

        result = query.first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {content_type} found for message {message_id}",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting media content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/media-content/reprocess-batch", response_model=BatchReprocessResponse)
async def reprocess_batch(
    request: BatchReprocessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Batch reprocess media messages from stored traces.

    This endpoint processes historical messages that weren't processed in real-time.
    For WhatsApp, it extracts base64 from stored webhook payloads.

    Supported content_types: audio, image
    """
    try:
        results = {"total": 0, "processed": 0, "failed": 0, "skipped": 0, "results": []}

        if "audio" in request.content_types:
            audio_result = await media_processing_service.batch_reprocess_audio(
                instance_name=request.instance_name,
                days_back=request.days_back,
                limit=request.limit,
                language=request.language,
                db=db,
            )
            results["total"] += audio_result["total"]
            results["processed"] += audio_result["processed"]
            results["failed"] += audio_result["failed"]
            results["skipped"] += audio_result["skipped"]
            results["results"].extend(audio_result["results"])

        if "image" in request.content_types:
            image_result = await media_processing_service.batch_reprocess_images(
                instance_name=request.instance_name,
                days_back=request.days_back,
                limit=request.limit,
                db=db,
            )
            results["total"] += image_result["total"]
            results["processed"] += image_result["processed"]
            results["failed"] += image_result["failed"]
            results["skipped"] += image_result["skipped"]
            results["results"].extend(image_result["results"])

        if "document" in request.content_types:
            document_result = await media_processing_service.batch_reprocess_documents(
                instance_name=request.instance_name,
                days_back=request.days_back,
                limit=request.limit,
                db=db,
            )
            results["total"] += document_result["total"]
            results["processed"] += document_result["processed"]
            results["failed"] += document_result["failed"]
            results["skipped"] += document_result["skipped"]
            results["results"].extend(document_result["results"])

        if not any(ct in request.content_types for ct in ["audio", "image", "document"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported content types: {request.content_types}. Supported: audio, image, document",
            )

        return BatchReprocessResponse(**results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch reprocess: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/media-content/reprocess-trace", response_model=MediaContentResponse)
async def reprocess_trace(
    request: ReprocessTraceRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Reprocess a single trace by ID."""
    try:
        result = await media_processing_service.reprocess_audio_from_trace(
            trace_id=request.trace_id,
            language=request.language,
            db=db,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not process trace {request.trace_id}",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media-content/stats")
async def get_media_stats(
    instance_name: Optional[str] = Query(None, description="Filter by instance"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get statistics about processed media content."""
    try:
        from sqlalchemy import func

        query = db.query(
            MediaContent.content_type,
            MediaContent.status,
            func.count(MediaContent.id).label("count"),
            func.avg(MediaContent.processing_time_ms).label("avg_processing_time"),
        )

        if instance_name:
            query = query.filter(MediaContent.instance_name == instance_name)

        stats = query.group_by(MediaContent.content_type, MediaContent.status).all()

        result = {}
        for row in stats:
            content_type = row.content_type
            if content_type not in result:
                result[content_type] = {"total": 0, "by_status": {}}

            result[content_type]["by_status"][row.status] = {
                "count": row.count,
                "avg_processing_time_ms": round(row.avg_processing_time) if row.avg_processing_time else None,
            }
            result[content_type]["total"] += row.count

        return {"stats": result}

    except Exception as e:
        logger.error(f"Error getting media stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
