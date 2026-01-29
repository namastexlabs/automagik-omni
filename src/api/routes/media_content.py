"""
Media Content API endpoints.
Provides endpoints for managing processed media content (transcriptions, descriptions).
"""

import asyncio
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.api.deps import get_database, verify_api_key
from src.db.trace_models import MediaContent, BatchJob, OmniMessageRecord
from src.db.database import SessionLocal
from src.services.media_processing import media_processing_service
from src.services.message_import import MessageImportService
from src.services.chat_id_resolver import ChatIdResolver
from src.services.sync_job import start_sync_job, stop_sync_job, get_sync_job_status
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
    content_types: List[str] = ["audio"]  # audio, image, video, document
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
    request_params: Optional[dict] = None  # Parsed request params for UI display
    status: str
    total_found: int = 0  # All items matching criteria (before filtering)
    total_items: int = 0  # Items to process (after filtering)
    processed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0  # Already processed (had MediaContent)
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


class BatchJobItemResult(BaseModel):
    """Individual item result from a batch job."""

    message_id: str
    content_type: str
    status: str  # completed, failed, skipped
    error_message: Optional[str] = None
    processor_name: Optional[str] = None
    content_preview: Optional[str] = None  # First 200 chars of content
    cost_usd: Optional[float] = None
    processed_at: Optional[datetime] = None


class BatchJobDetailsResponse(BaseModel):
    """Response model for job details with individual items."""

    job_id: str
    job_type: str
    status: str
    instance_name: Optional[str]
    # Summary stats
    total_found: int = 0
    processed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    # Item lists
    processed_items: List[BatchJobItemResult] = []
    failed_items: List[BatchJobItemResult] = []
    # Pagination
    page: int = 1
    page_size: int = 50
    has_more: bool = False


class ReprocessTraceRequest(BaseModel):
    """Request model for single trace reprocessing."""

    trace_id: str
    language: str = "pt"


class MessageImportRequest(BaseModel):
    """Request model for message import from Evolution."""

    instance_name: str
    days: int = 30
    batch_size: int = 500
    async_mode: bool = True


class MessageImportJobResponse(BaseModel):
    """Response model for async message import job."""

    job_id: str
    job_type: str
    status: str
    instance_name: str
    days: int
    message: str


class MessageImportStatsResponse(BaseModel):
    """Response model for sync message import."""

    instance_name: str
    total_found: int
    total_imported: int
    already_exists: int
    failed: int
    with_media: int
    source: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]


class StoredMessagesStatsResponse(BaseModel):
    """Response model for stored messages statistics."""

    instance_name: Optional[str]
    total_messages: int
    by_source: dict
    by_type: dict
    by_media_status: dict
    with_media: int


class OmniMediaBatchRequest(BaseModel):
    """Request for batch processing from omni_messages (unified store)."""

    content_type: str = "audio"  # 'audio', 'image', 'document'
    instance_name: Optional[str] = None
    days_back: int = 30
    limit: int = 100
    language: str = "pt"  # For audio transcription
    force: bool = False
    async_mode: bool = True


def _run_batch_processing_sync(job_id: str, request_params: dict):
    """
    Synchronous wrapper to run batch processing in a thread pool.
    Creates a new event loop in the thread to run the async function.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_batch_processing(job_id, request_params))
    finally:
        loop.close()


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

        total_found = 0  # All items matching criteria
        already_processed = 0  # Items skipped (had MediaContent)
        total_items = 0  # Items to process this run
        processed_items = 0
        failed_items = 0
        skipped_items = 0
        total_cost = Decimal("0")
        total_tokens = 0
        all_results = []

        # Helper to accumulate totals across content types
        def add_to_totals(found: int, to_process: int, skipped: int):
            nonlocal total_found, total_items, already_processed
            total_found += found
            total_items += to_process
            already_processed += skipped
            # Update job with running totals
            _update_job_totals(db, job_id, total_found, total_items, already_processed)

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
                    batch_job_id=job_id,
                    totals_callback=add_to_totals,
                )
            elif content_type == "image":
                result = await media_processing_service.batch_reprocess_images(
                    instance_name=instance_name,
                    days_back=days_back,
                    limit=limit,
                    force=force,
                    db=db,
                    progress_callback=lambda item: _update_job_progress(db, job_id, item),
                    batch_job_id=job_id,
                    totals_callback=add_to_totals,
                )
            elif content_type == "video":
                result = await media_processing_service.batch_reprocess_videos(
                    instance_name=instance_name,
                    days_back=days_back,
                    limit=limit,
                    force=force,
                    db=db,
                    progress_callback=lambda item: _update_job_progress(db, job_id, item),
                    batch_job_id=job_id,
                    totals_callback=add_to_totals,
                )
            elif content_type == "document":
                result = await media_processing_service.batch_reprocess_documents(
                    instance_name=instance_name,
                    days_back=days_back,
                    limit=limit,
                    force=force,
                    db=db,
                    progress_callback=lambda item: _update_job_progress(db, job_id, item),
                    batch_job_id=job_id,
                    totals_callback=add_to_totals,
                )
            else:
                continue

            # Aggregate stats including new fields
            total_found += result.get("total_found", 0)
            already_processed += result.get("already_processed", 0)
            total_items += result.get("total", 0)
            processed_items += result.get("processed", 0)
            # Include download_failed in failed count
            failed_items += result.get("failed", 0) + result.get("download_failed", 0)
            skipped_items += result.get("skipped", 0)
            all_results.extend(result.get("results", []))

            # Aggregate costs from results
            for r in result.get("results", []):
                if r.get("cost_usd"):
                    total_cost += Decimal(str(r["cost_usd"]))
                if r.get("tokens"):
                    total_tokens += r["tokens"]

        # Update job as completed with all stats
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        job.status = "completed"
        job.completed_at = datetime_utcnow()
        job.total_found = total_found  # All items found
        job.total_items = total_items  # Items to process
        job.processed_items = processed_items
        job.failed_items = failed_items
        job.skipped_items = already_processed  # Store already_processed as skipped_items
        job.total_cost_usd = total_cost if total_cost > 0 else None
        job.total_tokens = total_tokens if total_tokens > 0 else None
        # Store detailed breakdown in results_summary
        job.results_summary = json.dumps(
            {
                "results_count": len(all_results),
                "breakdown": {
                    "total_found": total_found,
                    "already_processed": already_processed,
                    "to_process": total_items,
                    "processed": processed_items,
                    "failed": failed_items,
                },
            }
        )
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


def _update_job_totals(db: Session, job_id: str, total_found: int, total_to_process: int, skipped: int):
    """Update job totals at the start of processing."""
    try:
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if job:
            job.total_found = total_found
            job.total_items = total_to_process
            job.skipped_items = skipped
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to update job totals: {e}")


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
        valid_types = {"audio", "image", "video", "document"}
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

            # Schedule background processing in a thread pool to avoid blocking the event loop
            # Using run_in_executor ensures synchronous DB operations don't block other requests
            import concurrent.futures

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                executor,
                _run_batch_processing_sync,
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

            if "video" in request.content_types:
                video_result = await media_processing_service.batch_reprocess_videos(
                    instance_name=request.instance_name,
                    days_back=request.days_back,
                    limit=request.limit,
                    force=request.force,
                    db=db,
                )
                results["total"] += video_result["total"]
                results["processed"] += video_result["processed"]
                results["failed"] += video_result["failed"]
                results["skipped"] += video_result["skipped"]
                results["results"].extend(video_result["results"])

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

        # Parse request_params JSON
        request_params = None
        if job.request_params:
            try:
                request_params = json.loads(job.request_params)
            except (json.JSONDecodeError, TypeError):
                pass

        return BatchJobStatusResponse(
            job_id=job.job_id,
            job_type=job.job_type,
            instance_name=job.instance_name,
            request_params=request_params,
            status=job.status,
            total_found=job.total_found or 0,
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

        def build_response(job):
            # Parse request_params JSON
            request_params = None
            if job.request_params:
                try:
                    request_params = json.loads(job.request_params)
                except (json.JSONDecodeError, TypeError):
                    pass
            return BatchJobStatusResponse(
                job_id=job.job_id,
                job_type=job.job_type,
                instance_name=job.instance_name,
                request_params=request_params,
                status=job.status,
                total_found=job.total_found or 0,
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

        return [build_response(job) for job in jobs]

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


@router.get("/batch-jobs/{job_id}/details", response_model=BatchJobDetailsResponse)
async def get_batch_job_details(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Get detailed results for a batch job, including individual processed and failed items.

    Returns processed items with content preview and failed items with error messages.
    """
    from src.db.trace_models import MediaContent

    try:
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        # Parse request params to get content types and time range
        request_params = {}
        if job.request_params:
            try:
                request_params = json.loads(job.request_params)
            except (json.JSONDecodeError, TypeError):
                pass

        content_types = request_params.get("content_types", ["audio"])
        instance_name = job.instance_name or request_params.get("instance_name")

        # Map content types to media_content content_type values
        content_type_map = {
            "audio": "audio_transcript",
            "image": "image_description",
            "video": "video_description",
            "document": "document_content",
        }
        mc_content_types = [content_type_map.get(ct, ct) for ct in content_types]

        # Try to query by batch_job_id first (new jobs will have this set)
        # Fall back to time-based filtering for older jobs without batch_job_id
        has_batch_job_records = db.query(MediaContent).filter(MediaContent.batch_job_id == job_id).first() is not None

        if has_batch_job_records:
            # Use precise batch_job_id filtering
            base_query = db.query(MediaContent).filter(
                MediaContent.batch_job_id == job_id,
            )
        else:
            # Fall back to time-based filtering for older jobs
            cutoff_start = job.created_at - timedelta(minutes=5) if job.created_at else None
            cutoff_end = job.completed_at + timedelta(minutes=5) if job.completed_at else datetime_utcnow()

            base_query = db.query(MediaContent).filter(
                MediaContent.content_type.in_(mc_content_types),
            )

            if instance_name:
                base_query = base_query.filter(MediaContent.instance_name == instance_name)

            if cutoff_start:
                base_query = base_query.filter(MediaContent.created_at >= cutoff_start)

            base_query = base_query.filter(MediaContent.created_at <= cutoff_end)

        # Get processed items (status = completed)
        processed_query = base_query.filter(MediaContent.status == "completed")
        processed_count = processed_query.count()

        # Get failed items (status = failed or has error_message)
        failed_query = base_query.filter((MediaContent.status == "failed") | (MediaContent.error_message.isnot(None)))

        # Paginate processed items
        offset = (page - 1) * page_size
        processed_records = (
            processed_query.order_by(MediaContent.created_at.desc()).offset(offset).limit(page_size).all()
        )

        # Always include all failed items (usually small number)
        failed_records = failed_query.order_by(MediaContent.created_at.desc()).limit(100).all()

        # Build response items
        processed_items = []
        # Collect successfully processed message IDs to filter out from failed
        successful_message_ids = set()
        for mc in processed_records:
            successful_message_ids.add((mc.original_message_id, mc.content_type))
            processed_items.append(
                BatchJobItemResult(
                    message_id=mc.original_message_id or "unknown",
                    content_type=mc.content_type,
                    status="completed",
                    processor_name=mc.processor_name,
                    content_preview=mc.content[:200] + "..." if mc.content and len(mc.content) > 200 else mc.content,
                    cost_usd=float(mc.cost_total_usd) if mc.cost_total_usd else None,
                    processed_at=mc.processed_at,
                )
            )

        # Filter out failed items that were later successfully processed
        failed_items = []
        for mc in failed_records:
            # Skip if this item has a successful version
            if (mc.original_message_id, mc.content_type) in successful_message_ids:
                continue
            failed_items.append(
                BatchJobItemResult(
                    message_id=mc.original_message_id or "unknown",
                    content_type=mc.content_type,
                    status="failed",
                    error_message=mc.error_message,
                    processor_name=mc.processor_name,
                    processed_at=mc.created_at,
                )
            )

        has_more = (offset + len(processed_records)) < processed_count

        return BatchJobDetailsResponse(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            instance_name=instance_name,
            total_found=job.total_found or 0,
            processed_count=processed_count,
            failed_count=len(failed_items),  # Use actual filtered count
            skipped_count=job.skipped_items or 0,
            processed_items=processed_items,
            failed_items=failed_items,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job details: {e}", exc_info=True)
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


# =============================================================================
# Message Import Endpoints (Import from evo_Message to omni_messages)
# =============================================================================


def _run_message_import_sync(job_id: str, instance_name: str, days: int, batch_size: int):
    """Synchronous wrapper to run message import in a thread pool."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_message_import(job_id, instance_name, days, batch_size))
    finally:
        loop.close()


async def _run_message_import(job_id: str, instance_name: str, days: int, batch_size: int):
    """Background task to import messages from Evolution to omni_messages."""
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

        # Run import
        service = MessageImportService(db)

        def progress_callback(processed: int, total: int):
            try:
                job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
                if job:
                    job.processed_items = processed
                    job.total_items = total
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to update import progress: {e}")

        stats = service.import_from_evolution(
            instance_name=instance_name,
            days=days,
            batch_size=batch_size,
            progress_callback=progress_callback,
        )

        # Update job as completed
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        job.status = "completed"
        job.completed_at = datetime_utcnow()
        job.total_found = stats.total_found
        job.total_items = stats.total_imported + stats.already_exists
        job.processed_items = stats.total_imported
        job.skipped_items = stats.already_exists
        job.failed_items = stats.failed
        job.results_summary = json.dumps(
            {
                "with_media": stats.with_media,
                "source": "evo_Message",
                "duration_seconds": (stats.completed_at - stats.started_at).total_seconds()
                if stats.completed_at
                else None,
            }
        )
        job.current_item = None
        db.commit()

        logger.info(
            f"Message import job {job_id} completed: imported {stats.total_imported}, skipped {stats.already_exists}"
        )

    except Exception as e:
        logger.error(f"Error in message import job {job_id}: {e}", exc_info=True)
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


@router.post("/messages/import", response_model=None)
async def import_messages(
    request: MessageImportRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Import messages from Evolution's evo_Message table into omni_messages.

    This enables media processing on ALL messages (not just webhook-received)
    and reduces dependency on Evolution API for message queries.

    If async_mode=True (default), returns immediately with job_id for progress polling.
    If async_mode=False, waits for completion (may timeout for large imports).
    """
    try:
        if request.async_mode:
            # Create batch job record
            import uuid

            job_id = str(uuid.uuid4())
            job = BatchJob(
                job_id=job_id,
                job_type="message_import",
                instance_name=request.instance_name,
                request_params=json.dumps(
                    {
                        "instance_name": request.instance_name,
                        "days": request.days,
                        "batch_size": request.batch_size,
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

            # Schedule background processing in a thread pool
            import concurrent.futures

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                executor,
                _run_message_import_sync,
                job_id,
                request.instance_name,
                request.days,
                request.batch_size,
            )

            return MessageImportJobResponse(
                job_id=job_id,
                job_type="message_import",
                status="pending",
                instance_name=request.instance_name,
                days=request.days,
                message=f"Import started. Poll /batch-jobs/{job_id} for progress.",
            )
        else:
            # Sync mode - process and wait
            service = MessageImportService(db)
            stats = service.import_from_evolution(
                instance_name=request.instance_name,
                days=request.days,
                batch_size=request.batch_size,
            )
            return MessageImportStatsResponse(**stats.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in message import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/stored/stats", response_model=StoredMessagesStatsResponse)
async def get_stored_messages_stats(
    instance_name: Optional[str] = Query(None, description="Filter by instance"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """Get statistics for stored messages in omni_messages table."""
    try:
        from sqlalchemy import func

        base_query = db.query(OmniMessageRecord)
        if instance_name:
            base_query = base_query.filter(OmniMessageRecord.instance_name == instance_name)

        # Total count
        total = base_query.count()

        # By source
        source_counts = dict(
            db.query(OmniMessageRecord.source, func.count(OmniMessageRecord.id))
            .filter(OmniMessageRecord.instance_name == instance_name if instance_name else True)
            .group_by(OmniMessageRecord.source)
            .all()
        )

        # By type
        type_counts = dict(
            db.query(OmniMessageRecord.message_type, func.count(OmniMessageRecord.id))
            .filter(OmniMessageRecord.instance_name == instance_name if instance_name else True)
            .group_by(OmniMessageRecord.message_type)
            .all()
        )

        # By media status
        media_status_counts = dict(
            db.query(OmniMessageRecord.media_status, func.count(OmniMessageRecord.id))
            .filter(OmniMessageRecord.instance_name == instance_name if instance_name else True)
            .filter(OmniMessageRecord.has_media == True)  # noqa: E712
            .group_by(OmniMessageRecord.media_status)
            .all()
        )

        # With media
        with_media = base_query.filter(OmniMessageRecord.has_media == True).count()  # noqa: E712

        return StoredMessagesStatsResponse(
            instance_name=instance_name,
            total_messages=total,
            by_source=source_counts,
            by_type=type_counts,
            by_media_status=media_status_counts,
            with_media=with_media,
        )

    except Exception as e:
        logger.error(f"Error getting stored messages stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/stored")
async def list_stored_messages(
    instance_name: str = Query(..., description="Instance name"),
    chat_id: Optional[str] = Query(None, description="Filter by chat ID"),
    unified: bool = Query(
        False, description="Use canonical_chat_id for unified conversation queries (merges @lid and @s.whatsapp.net)"
    ),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    has_media: Optional[bool] = Query(None, description="Filter by media presence"),
    source: Optional[str] = Query(None, description="Filter by source (webhook, sync, api)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_raw: bool = Query(False, description="Include raw message content"),
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    List stored messages from omni_messages table.

    When unified=true, uses canonical_chat_id to return messages from unified conversations.
    This merges messages from different WhatsApp chat ID formats (@lid and @s.whatsapp.net)
    that belong to the same contact.
    """
    try:
        query = db.query(OmniMessageRecord).filter(OmniMessageRecord.instance_name == instance_name)

        if chat_id:
            if unified:
                # Resolve to canonical chat ID and query by that
                resolver = ChatIdResolver(db)
                canonical_id = resolver.get_canonical_id(instance_name, chat_id)
                query = query.filter(OmniMessageRecord.canonical_chat_id == canonical_id)
            else:
                # Direct chat_id match (legacy behavior)
                query = query.filter(OmniMessageRecord.chat_id == chat_id)

        if message_type:
            query = query.filter(OmniMessageRecord.message_type == message_type)
        if has_media is not None:
            query = query.filter(OmniMessageRecord.has_media == has_media)
        if source:
            query = query.filter(OmniMessageRecord.source == source)

        total = query.count()
        messages = query.order_by(OmniMessageRecord.message_timestamp.desc()).offset(offset).limit(limit).all()

        return {
            "messages": [msg.to_dict(include_raw=include_raw) for msg in messages],
            "total_count": total,
            "page": offset // limit + 1,
            "page_size": limit,
            "has_more": offset + limit < total,
            "instance_name": instance_name,
            "chat_id": chat_id,
            "unified": unified,
        }

    except Exception as e:
        logger.error(f"Error listing stored messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Batch Processing from omni_messages (Unified Store)
# =============================================================================


def _run_omni_batch_processing_sync(job_id: str, request_params: dict):
    """Synchronous wrapper to run omni batch processing in a thread pool."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_omni_batch_processing(job_id, request_params))
    finally:
        loop.close()


async def _run_omni_batch_processing(job_id: str, request_params: dict):
    """Background task to batch process media from omni_messages."""
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

        content_type = request_params.get("content_type", "audio")
        instance_name = request_params.get("instance_name")
        days_back = request_params.get("days_back", 30)
        limit = request_params.get("limit", 100)
        language = request_params.get("language", "pt")
        force = request_params.get("force", False)

        result = await media_processing_service.batch_reprocess_from_omni_messages(
            instance_name=instance_name,
            content_type=content_type,
            days_back=days_back,
            limit=limit,
            language=language,
            force=force,
            db=db,
            progress_callback=lambda item: _update_job_progress(db, job_id, item),
            batch_job_id=job_id,
            totals_callback=lambda found, to_process, skipped: _update_job_totals(
                db, job_id, found, to_process, skipped
            ),
        )

        # Calculate totals
        total_cost = Decimal("0")
        total_tokens = 0
        for r in result.get("results", []):
            if r.get("cost_usd"):
                total_cost += Decimal(str(r["cost_usd"]))
            if r.get("tokens"):
                total_tokens += r["tokens"]

        # Update job as completed
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        job.status = "completed"
        job.completed_at = datetime_utcnow()
        job.total_found = result.get("total_found", 0)
        job.total_items = result.get("total", 0)
        job.processed_items = result.get("processed", 0)
        job.failed_items = result.get("failed", 0) + result.get("download_failed", 0)
        job.skipped_items = result.get("already_processed", 0)
        job.total_cost_usd = total_cost if total_cost > 0 else None
        job.total_tokens = total_tokens if total_tokens > 0 else None
        job.results_summary = json.dumps(
            {
                "download_failed": result.get("download_failed", 0),
                "source": "omni_messages",
            }
        )
        job.current_item = None
        db.commit()

        logger.info(f"Omni batch job {job_id} completed: {result.get('processed', 0)} processed")

    except Exception as e:
        logger.error(f"Error in omni batch job {job_id}: {e}", exc_info=True)
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


@router.post("/messages/stored/reprocess-batch")
async def reprocess_from_omni_messages(
    request: OmniMediaBatchRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Batch reprocess media from the unified omni_messages table.

    This processes media from ALL sources (webhook AND synced messages),
    enabling media processing on historical messages imported from evo_Message.

    Workflow:
    1. Query omni_messages for media messages of the specified type
    2. Download media files (if not already downloaded)
    3. Process media (transcription, description, extraction)
    4. Store results in omni_media_content and update media_status

    If async_mode=True (default), returns immediately with job_id for progress polling.
    """
    try:
        valid_types = {"audio", "image", "document"}
        if request.content_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content_type: {request.content_type}. Valid: {valid_types}",
            )

        if request.async_mode:
            import uuid

            job_id = str(uuid.uuid4())
            job = BatchJob(
                job_id=job_id,
                job_type=f"omni_{request.content_type}_reprocess",
                instance_name=request.instance_name,
                request_params=json.dumps(
                    {
                        "content_type": request.content_type,
                        "instance_name": request.instance_name,
                        "days_back": request.days_back,
                        "limit": request.limit,
                        "language": request.language,
                        "force": request.force,
                        "source": "omni_messages",
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

            # Schedule background processing in a thread pool
            import concurrent.futures

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                executor,
                _run_omni_batch_processing_sync,
                job_id,
                {
                    "content_type": request.content_type,
                    "instance_name": request.instance_name,
                    "days_back": request.days_back,
                    "limit": request.limit,
                    "language": request.language,
                    "force": request.force,
                },
            )

            return BatchJobResponse(
                job_id=job_id,
                job_type=f"omni_{request.content_type}_reprocess",
                status="pending",
                message=f"Processing {request.content_type} from omni_messages. Poll /batch-jobs/{job_id} for progress.",
            )
        else:
            result = await media_processing_service.batch_reprocess_from_omni_messages(
                instance_name=request.instance_name,
                content_type=request.content_type,
                days_back=request.days_back,
                limit=request.limit,
                language=request.language,
                force=request.force,
                db=db,
            )
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in omni batch reprocess: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Continuous Sync Job Management
# =============================================================================


class SyncJobRequest(BaseModel):
    """Request for starting/configuring sync job."""

    instances: Optional[List[str]] = None  # None = all instances
    interval_minutes: int = 5


class DiscordImportRequest(BaseModel):
    """Request for Discord history import."""

    instance_name: str
    guild_id: str
    days_back: int = 7
    max_messages_per_channel: int = 500
    channel_ids: Optional[List[str]] = None  # None = all channels
    skip_channels: Optional[List[str]] = None
    async_mode: bool = True


@router.post("/sync-job/start")
async def start_sync(
    request: SyncJobRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Start the continuous message sync job.

    This job periodically syncs new messages from evo_Message to omni_messages,
    enabling media processing on all historical messages.
    """
    try:
        status = await start_sync_job(
            instances=request.instances,
            interval_minutes=request.interval_minutes,
        )
        return {
            "message": "Sync job started",
            **status,
        }
    except Exception as e:
        logger.error(f"Error starting sync job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-job/stop")
async def stop_sync(
    api_key: str = Depends(verify_api_key),
):
    """Stop the continuous message sync job."""
    try:
        status = await stop_sync_job()
        return {
            "message": "Sync job stopped",
            **status,
        }
    except Exception as e:
        logger.error(f"Error stopping sync job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-job/status")
async def get_sync_status(
    api_key: str = Depends(verify_api_key),
):
    """Get current status of the continuous sync job."""
    try:
        return get_sync_job_status()
    except Exception as e:
        logger.error(f"Error getting sync job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Discord History Import
# =============================================================================


@router.post("/messages/import/discord")
async def import_discord_history(
    request: DiscordImportRequest,
    db: Session = Depends(get_database),
    api_key: str = Depends(verify_api_key),
):
    """
    Import message history from a Discord guild into omni_messages.

    This fetches historical messages from Discord channels using the Discord API.
    Requires the bot to be in the guild and have "Read Message History" permission.

    Note: The bot must be running and connected to Discord for this to work.

    If async_mode=True (default), returns immediately with job_id for progress polling.
    """
    try:
        # Import here to avoid circular imports and check if Discord is available

        # Get the Discord handler instance
        from src.api.app import channel_registry

        discord_handler = channel_registry.get_handler("discord")

        if not discord_handler:
            raise HTTPException(
                status_code=400,
                detail="Discord handler not available. Ensure Discord is enabled.",
            )

        # Check if the instance exists and is connected
        if request.instance_name not in discord_handler._bot_instances:
            raise HTTPException(
                status_code=404,
                detail=f"Discord instance '{request.instance_name}' not found or not connected.",
            )

        bot_instance = discord_handler._bot_instances[request.instance_name]
        if bot_instance.status != "connected":
            raise HTTPException(
                status_code=400,
                detail=f"Discord instance '{request.instance_name}' is not connected (status: {bot_instance.status}).",
            )

        # Find the guild
        guild = None
        for g in bot_instance.client.guilds:
            if str(g.id) == request.guild_id:
                guild = g
                break

        if not guild:
            raise HTTPException(
                status_code=404,
                detail=f"Guild {request.guild_id} not found. Ensure the bot is in this server.",
            )

        if request.async_mode:
            # Create batch job record
            import uuid

            job_id = str(uuid.uuid4())
            job = BatchJob(
                job_id=job_id,
                job_type="discord_import",
                instance_name=request.instance_name,
                request_params=json.dumps(
                    {
                        "instance_name": request.instance_name,
                        "guild_id": request.guild_id,
                        "guild_name": guild.name,
                        "days_back": request.days_back,
                        "max_messages_per_channel": request.max_messages_per_channel,
                        "channel_ids": request.channel_ids,
                        "skip_channels": request.skip_channels,
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

            # Schedule background processing
            asyncio.create_task(
                _run_discord_import(
                    job_id=job_id,
                    client=bot_instance.client,
                    guild=guild,
                    instance_name=request.instance_name,
                    days_back=request.days_back,
                    max_messages_per_channel=request.max_messages_per_channel,
                    channel_ids=request.channel_ids,
                    skip_channels=request.skip_channels,
                )
            )

            return {
                "job_id": job_id,
                "job_type": "discord_import",
                "status": "pending",
                "instance_name": request.instance_name,
                "guild_id": request.guild_id,
                "guild_name": guild.name,
                "message": f"Discord import started. Poll /batch-jobs/{job_id} for progress.",
            }
        else:
            # Sync mode
            from src.services.discord_import import DiscordImportService

            service = DiscordImportService(db)
            stats = await service.import_guild_history(
                client=bot_instance.client,
                guild=guild,
                instance_name=request.instance_name,
                days_back=request.days_back,
                max_messages_per_channel=request.max_messages_per_channel,
                channel_ids=request.channel_ids,
                skip_channels=request.skip_channels,
            )
            return stats.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Discord import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_discord_import(
    job_id: str,
    client,
    guild,
    instance_name: str,
    days_back: int,
    max_messages_per_channel: int,
    channel_ids: Optional[List[str]],
    skip_channels: Optional[List[str]],
):
    """Background task to import Discord history."""
    # Yield immediately to allow the API response to return
    await asyncio.sleep(0)

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

        # Run import
        from src.services.discord_import import DiscordImportService

        service = DiscordImportService(db)

        def progress_callback(channel_name: str, imported: int):
            try:
                job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
                if job:
                    job.current_item = f"#{channel_name}"
                    job.processed_items = (job.processed_items or 0) + imported
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to update Discord import progress: {e}")

        stats = await service.import_guild_history(
            client=client,
            guild=guild,
            instance_name=instance_name,
            days_back=days_back,
            max_messages_per_channel=max_messages_per_channel,
            channel_ids=channel_ids,
            skip_channels=skip_channels,
            progress_callback=progress_callback,
        )

        # Update job as completed
        job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        job.status = "completed"
        job.completed_at = datetime_utcnow()
        job.total_found = stats.total_found
        job.total_items = stats.total_imported + stats.already_exists
        job.processed_items = stats.total_imported
        job.skipped_items = stats.already_exists
        job.failed_items = stats.failed
        job.results_summary = json.dumps(
            {
                "with_media": stats.with_media,
                "channels_processed": stats.channels_processed,
                "source": "discord_api",
                "duration_seconds": (stats.completed_at - stats.started_at).total_seconds()
                if stats.completed_at
                else None,
            }
        )
        job.current_item = None
        db.commit()

        logger.info(f"Discord import job {job_id} completed: {stats.to_dict()}")

    except Exception as e:
        logger.error(f"Error in Discord import job {job_id}: {e}", exc_info=True)
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
