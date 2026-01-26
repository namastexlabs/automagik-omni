"""
Media Content API endpoints.
Provides endpoints for managing processed media content (transcriptions, descriptions).
"""

import asyncio
import json
import logging
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.api.deps import get_database, verify_api_key
from src.db.trace_models import MediaContent, BatchJob
from src.db.database import SessionLocal
from src.services.media_processing import media_processing_service
from src.utils.datetime_utils import datetime_utcnow

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
    limit: Optional[int] = 100  # None or 0 means no limit (all items)
    language: str = "pt"
    content_types: List[str] = ["audio"]  # audio, image, document
    force: bool = False  # Force reprocess even if already completed
    async_mode: bool = True  # If True, returns job_id immediately; if False, waits for completion


class BatchReprocessResponse(BaseModel):
    """Response model for sync batch reprocessing."""

    total: int
    processed: int
    failed: int
    skipped: int
    results: List[dict]


class BatchJobResponse(BaseModel):
    """Response model for async batch job."""

    job_id: str
    job_type: str
    status: str
    message: str


class BatchJobStatusResponse(BaseModel):
    """Response model for job status."""

    job_id: str
    job_type: str
    instance_name: Optional[str]
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    skipped_items: int
    current_item: Optional[str]
    progress_percent: float
    total_cost_usd: Optional[float]
    total_tokens: Optional[int]
    error_message: Optional[str]
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReprocessTraceRequest(BaseModel):
    """Request model for single trace reprocessing."""

    trace_id: str
    language: str = "pt"


async def _run_batch_processing(job_id: str, request_params: dict):
    """
    Background task to run batch processing and update job status.
    Uses its own database session.
    """
    db = SessionLocal()
    try:
        # Update job to processing
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "processing"
        job.started_at = datetime_utcnow()
        db.commit()

        content_types = request_params.get("content_types", ["audio"])
        instance_name = request_params.get("instance_name")
        days_back = request_params.get("days_back", 30)
        limit = request_params.get("limit", 100)
        language = request_params.get("language", "pt")
        force = request_params.get("force", False)

        total_items = 0
        processed_items = 0
        failed_items = 0
        skipped_items = 0
        total_cost = Decimal("0")
        total_tokens = 0
        all_results = []

        # Process each content type
        for content_type in content_types:
            if content_type == "audio":
                result = await media_processing_service.batch_reprocess_audio(
                    instance_name=instance_name,
                    days_back=days_back,
                    limit=limit,
                    language=language,
                    force=force,
                    db=db,
                    progress_callback=lambda item: _update_job_progress(db, job_id, item),
                )
            elif content_type == "image":
                result = await media_processing_service.batch_reprocess_images(
                    instance_name=instance_name,
                    days_back=days_back,
                    limit=limit,
                    force=force,
                    db=db,
                    progress_callback=lambda item: _update_job_progress(db, job_id, item),
                )
            elif content_type == "document":
                result = await media_processing_service.batch_reprocess_documents(
                    instance_name=instance_name,
                    days_back=days_back,
                    limit=limit,
                    force=force,
                    db=db,
                    progress_callback=lambda item: _update_job_progress(db, job_id, item),
                )
            else:
                continue

            total_items += result.get("total", 0)
            processed_items += result.get("processed", 0)
            failed_items += result.get("failed", 0)
            skipped_items += result.get("skipped", 0)
            all_results.extend(result.get("results", []))

            # Aggregate costs from results
            for r in result.get("results", []):
                if r.get("cost_usd"):
                    total_cost += Decimal(str(r["cost_usd"]))
                if r.get("tokens"):
                    total_tokens += r["tokens"]

        # Update job as completed
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        job.status = "completed"
        job.completed_at = datetime_utcnow()
        job.total_items = total_items
        job.processed_items = processed_items
        job.failed_items = failed_items
        job.skipped_items = skipped_items
        job.total_cost_usd = total_cost if total_cost > 0 else None
        job.total_tokens = total_tokens if total_tokens > 0 else None
        job.results_summary = json.dumps({"results_count": len(all_results)})
        job.current_item = None
        db.commit()

        logger.info(f"Batch job {job_id} completed: {processed_items}/{total_items} processed")

    except Exception as e:
        logger.error(f"Error in batch job {job_id}: {e}", exc_info=True)
        try:
            job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime_utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _update_job_progress(db: Session, job_id: str, current_item: str):
    """Update job progress with current item being processed."""
    try:
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if job:
            job.current_item = current_item
            job.processed_items = (job.processed_items or 0) + 1
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to update job progress: {e}")


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


@router.post("/media-content/reprocess-batch")
async def reprocess_batch(
    request: BatchReprocessRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Batch reprocess media messages from stored traces.

    If async_mode=True (default), returns immediately with job_id for progress polling.
    If async_mode=False, waits for completion and returns full results (may timeout for large batches).
    """
    try:
        # Validate content types
        valid_types = {"audio", "image", "document"}
        invalid_types = set(request.content_types) - valid_types
        if invalid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content types: {invalid_types}. Valid: {valid_types}",
            )

        if request.async_mode:
            # Create batch job record
            import uuid

            job_id = str(uuid.uuid4())
            job = BatchJob(
                job_id=job_id,
                job_type="media_reprocess",
                instance_name=request.instance_name,
                request_params=json.dumps(
                    {
                        "instance_name": request.instance_name,
                        "days_back": request.days_back,
                        "limit": request.limit,
                        "language": request.language,
                        "content_types": request.content_types,
                        "force": request.force,
                    }
                ),
                status="pending",
                total_items=0,
                processed_items=0,
                failed_items=0,
                skipped_items=0,
            )
            db.add(job)
            db.commit()

            # Schedule background processing using asyncio.create_task
            # This truly runs in background without blocking the response
            asyncio.create_task(
                _run_batch_processing(
                    job_id,
                    {
                        "instance_name": request.instance_name,
                        "days_back": request.days_back,
                        "limit": request.limit if request.limit else None,  # 0 or None = no limit
                        "language": request.language,
                        "content_types": request.content_types,
                        "force": request.force,
                    },
                )
            )

            return BatchJobResponse(
                job_id=job_id,
                job_type="media_reprocess",
                status="pending",
                message=f"Job started. Poll /batch-jobs/{job_id} for progress.",
            )

        else:
            # Sync mode - process and wait (may timeout)
            results = {"total": 0, "processed": 0, "failed": 0, "skipped": 0, "results": []}

            if "audio" in request.content_types:
                audio_result = await media_processing_service.batch_reprocess_audio(
                    instance_name=request.instance_name,
                    days_back=request.days_back,
                    limit=request.limit,
                    language=request.language,
                    force=request.force,
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
                    force=request.force,
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
                    force=request.force,
                    db=db,
                )
                results["total"] += document_result["total"]
                results["processed"] += document_result["processed"]
                results["failed"] += document_result["failed"]
                results["skipped"] += document_result["skipped"]
                results["results"].extend(document_result["results"])

            return BatchReprocessResponse(**results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch reprocess: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-jobs/{job_id}", response_model=BatchJobStatusResponse)
async def get_batch_job_status(
    job_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get status and progress of a batch job."""
    try:
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        return BatchJobStatusResponse(
            job_id=job.job_id,
            job_type=job.job_type,
            instance_name=job.instance_name,
            status=job.status,
            total_items=job.total_items or 0,
            processed_items=job.processed_items or 0,
            failed_items=job.failed_items or 0,
            skipped_items=job.skipped_items or 0,
            current_item=job.current_item,
            progress_percent=round((job.processed_items / job.total_items) * 100, 1) if job.total_items else 0,
            total_cost_usd=float(job.total_cost_usd) if job.total_cost_usd else None,
            total_tokens=job.total_tokens,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-jobs", response_model=List[BatchJobStatusResponse])
async def list_batch_jobs(
    instance_name: Optional[str] = Query(None, description="Filter by instance"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """List batch jobs with optional filters."""
    try:
        query = db.query(BatchJob)

        if instance_name:
            query = query.filter(BatchJob.instance_name == instance_name)
        if status_filter:
            query = query.filter(BatchJob.status == status_filter)

        jobs = query.order_by(BatchJob.created_at.desc()).limit(limit).all()

        return [
            BatchJobStatusResponse(
                job_id=job.job_id,
                job_type=job.job_type,
                instance_name=job.instance_name,
                status=job.status,
                total_items=job.total_items or 0,
                processed_items=job.processed_items or 0,
                failed_items=job.failed_items or 0,
                skipped_items=job.skipped_items or 0,
                current_item=job.current_item,
                progress_percent=round((job.processed_items / job.total_items) * 100, 1) if job.total_items else 0,
                total_cost_usd=float(job.total_cost_usd) if job.total_cost_usd else None,
                total_tokens=job.total_tokens,
                error_message=job.error_message,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            for job in jobs
        ]

    except Exception as e:
        logger.error(f"Error listing batch jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch-jobs/{job_id}")
async def cancel_batch_job(
    job_id: str,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Cancel a pending or running batch job."""
    try:
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        if job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {job.status}",
            )

        job.status = "cancelled"
        job.completed_at = datetime_utcnow()
        db.commit()

        return {"message": f"Job {job_id} cancelled", "status": "cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/media-content/reprocess-trace", response_model=MediaContentResponse)
async def reprocess_trace(
    request: ReprocessTraceRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Reprocess a single trace by ID."""
    try:
        # Try audio first (most common)
        result = await media_processing_service.reprocess_audio_from_trace(
            trace_id=request.trace_id,
            language=request.language,
            db=db,
        )

        if not result:
            # Try image
            result = await media_processing_service.reprocess_image_from_trace(
                trace_id=request.trace_id,
                db=db,
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not process trace {request.trace_id}. Check if it's a valid media trace.",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
