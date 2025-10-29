#!/usr/bin/env python3
"""
Fix existing traces with 'unknown' message_type by re-analyzing their payloads.
This script reads the webhook_received payload and determines the correct message type.
"""

import sys
import logging
from sqlalchemy.orm import Session

# Add src to path
sys.path.insert(0, "/home/cezar/automagik/automagik-omni")

from src.db.database import SessionLocal
from src.db.trace_models import MessageTrace, TracePayload
from src.services.trace_service import TraceService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_unknown_message_types(dry_run: bool = True):
    """
    Find all traces with message_type='unknown' and update them based on their payloads.

    Args:
        dry_run: If True, only show what would be changed without actually updating
    """
    db: Session = SessionLocal()

    try:
        # Find all traces with unknown message type
        unknown_traces = db.query(MessageTrace).filter(MessageTrace.message_type == "unknown").all()

        logger.info(f"Found {len(unknown_traces)} traces with 'unknown' message_type")

        updated_count = 0
        failed_count = 0

        for trace in unknown_traces:
            try:
                # Get the webhook_received payload
                webhook_payload = (
                    db.query(TracePayload)
                    .filter(
                        TracePayload.trace_id == trace.trace_id,
                        TracePayload.stage == "webhook_received",
                    )
                    .first()
                )

                if not webhook_payload:
                    logger.warning(f"No webhook payload found for trace {trace.trace_id}")
                    failed_count += 1
                    continue

                # Get the payload data
                payload_data = webhook_payload.get_payload()
                if not payload_data:
                    logger.warning(f"Could not decompress payload for trace {trace.trace_id}")
                    failed_count += 1
                    continue

                # Extract message object
                data = payload_data.get("data", {})
                message_obj = data.get("message", {})

                if not message_obj:
                    logger.warning(f"No message object found in payload for trace {trace.trace_id}")
                    failed_count += 1
                    continue

                # Determine the correct message type
                new_message_type = TraceService._determine_message_type(message_obj)

                if new_message_type != "unknown":
                    logger.info(
                        f"Trace {trace.trace_id[:8]}... : {trace.message_type} -> {new_message_type} "
                        f"(keys: {list(message_obj.keys())})"
                    )

                    if not dry_run:
                        trace.message_type = new_message_type
                        updated_count += 1
                    else:
                        updated_count += 1
                else:
                    logger.debug(f"Trace {trace.trace_id[:8]}... : Still unknown (keys: {list(message_obj.keys())})")

            except Exception as e:
                logger.error(f"Error processing trace {trace.trace_id}: {e}")
                failed_count += 1
                continue

        # Commit changes if not dry run
        if not dry_run:
            db.commit()
            logger.info(f"✅ Updated {updated_count} traces")
        else:
            logger.info(f"✅ Would update {updated_count} traces (dry run)")

        logger.info(f"❌ Failed to process {failed_count} traces")

    except Exception as e:
        logger.error(f"Error during migration: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix unknown message types in traces")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually update the database (default is dry-run)",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    if args.execute:
        logger.info("EXECUTING: Will update database")
    else:
        logger.info("DRY RUN: No changes will be made (use --execute to apply changes)")
    logger.info("=" * 80)

    fix_unknown_message_types(dry_run=not args.execute)

    logger.info("=" * 80)
    logger.info("Done!")
    logger.info("=" * 80)
