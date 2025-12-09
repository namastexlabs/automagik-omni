"""
Factory reset service for Automagik Omni.

Handles:
- Evolution API instance cleanup
- PostgreSQL table clearing (omni_* and evo_* tables)
- Log file cleanup

PostgreSQL only - SQLite is NOT supported.
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, TypedDict
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import text

from src.db.models import InstanceConfig, User, AccessRule, GlobalSetting
from src.config import config

logger = logging.getLogger(__name__)


@dataclass
class ResetPreview:
    """Preview of what will be reset."""

    instances: List[str]
    instance_count: int
    user_count: int
    trace_count: int
    access_rule_count: int
    setting_count: int
    log_path: Path
    log_size_mb: float
    postgres_tables: List[str]


class FactoryResetResult(TypedDict):
    """Structured result of a factory reset."""

    evolution_instances: Dict[str, str]
    postgres_tables: List[str]
    logs_deleted: int


class ResetService:
    """Service for factory reset operations.

    PostgreSQL only - SQLite is NOT supported.
    """

    def __init__(self):
        self.log_path = Path(config.logging.log_folder)

    def get_preview(self, db: Session) -> ResetPreview:
        """Get a preview of what would be reset."""
        # Get counts
        instances = db.query(InstanceConfig).all()
        instance_names = [i.name for i in instances if i.name]

        # Import trace models only if needed
        try:
            from src.db.trace_models import MessageTrace

            trace_count = db.query(MessageTrace).count()
        except Exception:
            trace_count = 0

        # Calculate log size
        log_size = (
            sum(f.stat().st_size for f in self.log_path.rglob("*") if f.is_file()) / (1024 * 1024)
            if self.log_path.exists()
            else 0
        )

        # Get PostgreSQL tables (omni_* and evo_*)
        postgres_tables = []
        try:
            result = db.execute(
                text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'omni_%' OR tablename LIKE 'evo_%'")
            )
            postgres_tables = [row[0] for row in result]
        except Exception:
            postgres_tables = []

        return ResetPreview(
            instances=instance_names,
            instance_count=len(instance_names),
            user_count=db.query(User).count(),
            trace_count=trace_count,
            access_rule_count=db.query(AccessRule).count(),
            setting_count=db.query(GlobalSetting).count(),
            log_path=self.log_path,
            log_size_mb=round(log_size, 2),
            postgres_tables=postgres_tables,
        )

    async def delete_evolution_instances(self, db: Session) -> Dict[str, str]:
        """Delete all Evolution API instances."""
        results: Dict[str, str] = {}
        instances = db.query(InstanceConfig).filter(InstanceConfig.channel_type == "whatsapp").all()

        if not instances:
            return results

        try:
            from src.channels.whatsapp.evolution_client import EvolutionClient

            for instance in instances:
                if not instance.name:
                    continue
                try:
                    client = EvolutionClient(
                        base_url=instance.evolution_url or config.get_env("EVOLUTION_URL", "http://localhost:18082"),
                        api_key=instance.evolution_key or "",
                    )
                    await client.delete_instance(instance.name)
                    results[instance.name] = "deleted"
                    logger.info(f"Deleted Evolution instance: {instance.name}")
                except Exception as e:
                    results[instance.name] = f"error: {str(e)}"
                    logger.warning(f"Failed to delete Evolution instance {instance.name}: {e}")

        except ImportError:
            logger.warning("Evolution client not available, skipping instance cleanup")

        return results

    def clear_postgres_tables(self, db: Session) -> List[str]:
        """Clear all omni_* and evo_* tables in PostgreSQL."""
        cleared = []

        # Tables to clear in order (respecting foreign keys)
        # omni_* tables (Python/SQLAlchemy)
        omni_tables = [
            "omni_trace_payloads",
            "omni_message_traces",
            "omni_setting_change_history",
            "omni_access_rules",
            "omni_user_external_ids",
            "omni_users",
            "omni_instance_configs",
            "omni_global_settings",
        ]

        # evo_* tables (Evolution/Prisma)
        evo_tables = [
            "evo_Media",
            "evo_MessageUpdate",
            "evo_Message",
            "evo_Chat",
            "evo_Contact",
            "evo_Template",
            "evo_Label",
            "evo_Webhook",
            "evo_Proxy",
            "evo_Setting",
            "evo_Rabbitmq",
            "evo_Nats",
            "evo_Sqs",
            "evo_Kafka",
            "evo_Websocket",
            "evo_Pusher",
            "evo_Session",
            "evo_Instance",
            "evo_IsOnWhatsapp",
        ]

        all_tables = omni_tables + evo_tables

        for table in all_tables:
            try:
                db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                cleared.append(table)
                logger.info(f"Cleared PostgreSQL table: {table}")
            except Exception as e:
                logger.warning(f"Could not clear {table}: {e}")

        db.commit()
        return cleared

    def delete_logs(self) -> int:
        """Delete all log files. Returns count of files deleted."""
        if not self.log_path.exists():
            return 0

        count = sum(1 for f in self.log_path.rglob("*") if f.is_file())
        shutil.rmtree(self.log_path)
        logger.info(f"Deleted {count} log files from {self.log_path}")
        return count

    async def factory_reset(
        self,
        db: Session,
        keep_instances: bool = False,
        clear_postgres: bool = True,
    ) -> FactoryResetResult:
        """
        Perform factory reset.

        Args:
            db: Database session
            keep_instances: If True, don't delete Evolution instances
            clear_postgres: If True, clear PostgreSQL tables (default: True)

        Returns:
            Dict with results of each operation

        PostgreSQL only - SQLite is NOT supported.
        """
        results: FactoryResetResult = {
            "evolution_instances": {},
            "postgres_tables": [],
            "logs_deleted": 0,
        }

        # 1. Delete Evolution instances (unless keeping)
        if not keep_instances:
            results["evolution_instances"] = await self.delete_evolution_instances(db)

        # 2. Clear PostgreSQL tables (omni_* and evo_*)
        if clear_postgres:
            results["postgres_tables"] = self.clear_postgres_tables(db)

        # 3. Delete logs
        results["logs_deleted"] = self.delete_logs()

        return results


# Singleton instance
reset_service = ResetService()
