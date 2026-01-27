"""
Continuous Sync Job

Periodically syncs new messages from Evolution's evo_Message table
to the unified omni_messages store.

Features:
- Incremental sync (only new messages since last sync)
- Configurable interval
- Automatic retry on failure
- Metrics tracking
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy import func

from src.db.database import SessionLocal
from src.db.trace_models import OmniMessageRecord
from src.services.message_import import MessageImportService
from src.utils.datetime_utils import datetime_utcnow

logger = logging.getLogger(__name__)


class SyncJobMetrics:
    """Tracks sync job metrics."""

    def __init__(self):
        self.last_sync_at: Optional[datetime] = None
        self.last_sync_duration_seconds: float = 0
        self.last_sync_imported: int = 0
        self.last_sync_skipped: int = 0
        self.total_syncs: int = 0
        self.total_imported: int = 0
        self.total_errors: int = 0
        self.is_running: bool = False
        self.started_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_duration_seconds": self.last_sync_duration_seconds,
            "last_sync_imported": self.last_sync_imported,
            "last_sync_skipped": self.last_sync_skipped,
            "total_syncs": self.total_syncs,
            "total_imported": self.total_imported,
            "total_errors": self.total_errors,
            "is_running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


class ContinuousSyncJob:
    """
    Background job that continuously syncs messages from evo_Message to omni_messages.

    Usage:
        sync_job = ContinuousSyncJob()
        await sync_job.start(interval_minutes=5)

        # To stop:
        await sync_job.stop()

        # Check status:
        status = sync_job.get_status()
    """

    def __init__(self):
        self.metrics = SyncJobMetrics()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._instances: list = []  # List of instances to sync

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the sync job."""
        return {
            "running": self._running,
            "instances": self._instances,
            **self.metrics.to_dict(),
        }

    async def start(
        self,
        instances: Optional[list] = None,
        interval_minutes: int = 5,
        initial_days_back: int = 7,
    ):
        """
        Start the continuous sync job.

        Args:
            instances: List of instance names to sync. If None, syncs all instances.
            interval_minutes: How often to check for new messages
            initial_days_back: How far back to look on first sync for each instance
        """
        if self._running:
            logger.warning("Sync job already running")
            return

        self._running = True
        self._instances = instances or []
        self.metrics.is_running = True
        self.metrics.started_at = datetime_utcnow()

        logger.info(
            f"Starting continuous sync job (interval: {interval_minutes} min, instances: {self._instances or 'all'})"
        )

        self._task = asyncio.create_task(self._run_loop(interval_minutes, initial_days_back))

    async def stop(self):
        """Stop the continuous sync job."""
        if not self._running:
            return

        self._running = False
        self.metrics.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Continuous sync job stopped")

    async def _run_loop(self, interval_minutes: int, initial_days_back: int):
        """Main sync loop."""
        while self._running:
            try:
                await self._sync_all_instances(initial_days_back)
                # After first run, only look back 1 day
                initial_days_back = 1
            except Exception as e:
                logger.error(f"Error in sync loop: {e}", exc_info=True)
                self.metrics.total_errors += 1

            # Wait for next interval
            await asyncio.sleep(interval_minutes * 60)

    async def _sync_all_instances(self, days_back: int):
        """Sync all configured instances."""
        db = SessionLocal()
        try:
            # Get list of instances to sync
            if self._instances:
                instances = self._instances
            else:
                # Get all instances from database
                from src.db.models import EvolutionInstance

                instances = [i.name for i in db.query(EvolutionInstance.name).all()]

            logger.info(f"Starting sync for {len(instances)} instances")

            total_imported = 0
            total_skipped = 0
            start_time = datetime_utcnow()

            for instance_name in instances:
                try:
                    stats = await self._sync_instance(db, instance_name, days_back)
                    total_imported += stats.get("total_imported", 0)
                    total_skipped += stats.get("already_exists", 0)
                except Exception as e:
                    logger.error(f"Error syncing instance {instance_name}: {e}")
                    self.metrics.total_errors += 1

            # Update metrics
            end_time = datetime_utcnow()
            self.metrics.last_sync_at = end_time
            self.metrics.last_sync_duration_seconds = (end_time - start_time).total_seconds()
            self.metrics.last_sync_imported = total_imported
            self.metrics.last_sync_skipped = total_skipped
            self.metrics.total_syncs += 1
            self.metrics.total_imported += total_imported

            logger.info(
                f"Sync complete: {total_imported} imported, {total_skipped} skipped "
                f"in {self.metrics.last_sync_duration_seconds:.1f}s"
            )

        finally:
            db.close()

    async def _sync_instance(self, db: SQLAlchemySession, instance_name: str, days_back: int) -> Dict[str, Any]:
        """Sync a single instance."""
        # Get last sync timestamp for this instance
        last_sync = (
            db.query(func.max(OmniMessageRecord.synced_at))
            .filter(OmniMessageRecord.instance_name == instance_name)
            .filter(OmniMessageRecord.source == "sync")
            .scalar()
        )

        if last_sync:
            # Calculate days since last sync
            days_since_sync = (datetime_utcnow() - last_sync).days + 1
            days_back = min(days_since_sync, days_back)

        logger.debug(f"Syncing {instance_name} for last {days_back} days")

        # Run sync
        service = MessageImportService(db)
        stats = service.import_from_evolution(
            instance_name=instance_name,
            days=days_back,
            batch_size=500,
        )

        return stats.to_dict()


# Global instance
continuous_sync_job = ContinuousSyncJob()


async def start_sync_job(
    instances: Optional[list] = None,
    interval_minutes: int = 5,
) -> Dict[str, Any]:
    """
    Start the continuous sync job.

    Args:
        instances: List of instance names to sync (None = all)
        interval_minutes: Sync interval in minutes

    Returns:
        Status dict
    """
    await continuous_sync_job.start(
        instances=instances,
        interval_minutes=interval_minutes,
    )
    return continuous_sync_job.get_status()


async def stop_sync_job() -> Dict[str, Any]:
    """Stop the continuous sync job."""
    await continuous_sync_job.stop()
    return continuous_sync_job.get_status()


def get_sync_job_status() -> Dict[str, Any]:
    """Get current status of the sync job."""
    return continuous_sync_job.get_status()
