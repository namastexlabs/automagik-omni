#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL database.

This script transfers all data from the SQLite database to PostgreSQL,
preserving all relationships and data integrity.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.db.models import Base, InstanceConfig, User
from src.db.trace_models import MessageTrace, TracePayload

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_sqlite_url():
    """Get SQLite database URL."""
    sqlite_path = os.path.join(project_root, 'data', 'automagik-omni.db')
    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite database not found at: {sqlite_path}")
        sys.exit(1)
    return f"sqlite:///{sqlite_path}"


def get_postgres_url():
    """Get PostgreSQL database URL from config."""
    url = config.database.database_url
    if not url.startswith('postgresql://'):
        logger.error("PostgreSQL URL not configured. Please set AUTOMAGIK_OMNI_DATABASE_URL")
        sys.exit(1)
    return url


def migrate_table_data(source_engine, target_engine, table_name, skip_orphaned=True):
    """Migrate data from one table to another."""
    logger.info(f"Migrating table: {table_name}")
    
    # Use raw SQL for reading from source
    with source_engine.connect() as source_conn:
        result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        columns = result.keys()
        
    if not rows:
        logger.info(f"  No data to migrate in {table_name}")
        return 0
    
    # Convert rows to dictionaries
    data = [dict(zip(columns, row)) for row in rows]
    
    # Define boolean fields for each table
    boolean_fields = {
        'instance_configs': ['webhook_base64', 'is_default', 'is_active'],
        'message_traces': ['has_media', 'has_quoted_message', 'agent_response_success', 'evolution_success'],
        'trace_payloads': ['contains_media', 'contains_base64']
    }
    
    # Convert SQLite boolean integers (0/1) to PostgreSQL booleans (True/False)
    if table_name in boolean_fields:
        for row in data:
            for field in boolean_fields[table_name]:
                if field in row and isinstance(row[field], int):
                    row[field] = bool(row[field])
    
    # Special handling for different tables
    if table_name == 'instance_configs':
        # Ensure required fields have defaults
        for row in data:
            if 'channel_type' not in row or row['channel_type'] is None:
                row['channel_type'] = 'whatsapp'
            if 'webhook_base64' not in row or row['webhook_base64'] is None:
                row['webhook_base64'] = True
            if 'agent_timeout' not in row or row['agent_timeout'] is None:
                row['agent_timeout'] = 60
    
    # Handle orphaned records for tables with foreign keys
    if skip_orphaned:
        if table_name == 'message_traces':
            # Get existing instance names from target database
            with target_engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM instance_configs"))
                valid_instances = {row[0] for row in result}
            
            # Filter out records with invalid instance references
            original_count = len(data)
            data = [row for row in data if row.get('instance_name') in valid_instances]
            filtered_count = original_count - len(data)
            if filtered_count > 0:
                logger.warning(f"  Filtered {filtered_count} orphaned records with invalid instance references")
        
        elif table_name == 'trace_payloads':
            # Get existing trace_ids from target database
            with target_engine.connect() as conn:
                result = conn.execute(text("SELECT trace_id FROM message_traces"))
                valid_traces = {row[0] for row in result}
            
            # Filter out records with invalid trace references
            original_count = len(data)
            data = [row for row in data if row.get('trace_id') in valid_traces]
            filtered_count = original_count - len(data)
            if filtered_count > 0:
                logger.warning(f"  Filtered {filtered_count} orphaned records with invalid trace references")
    
    # Insert data into target
    with target_engine.begin() as target_conn:
        # Insert data
        for row in data:
            # Build insert statement dynamically
            columns_str = ', '.join(row.keys())
            values_str = ', '.join([f":{k}" for k in row.keys()])
            insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"
            target_conn.execute(text(insert_sql), row)
    
    logger.info(f"  Migrated {len(data)} records")
    return len(data)


def migrate_database():
    """Main migration function."""
    logger.info("Starting database migration from SQLite to PostgreSQL...")
    
    # Get database URLs
    sqlite_url = get_sqlite_url()
    postgres_url = get_postgres_url()
    
    logger.info(f"Source: {sqlite_url}")
    logger.info(f"Target: {postgres_url}")
    
    # Create engines
    source_engine = create_engine(sqlite_url)
    target_engine = create_engine(postgres_url)
    
    # Tables to migrate in order (respecting foreign key constraints)
    tables_to_migrate = [
        'instance_configs',
        'users',
        'message_traces',
        'trace_payloads',
    ]
    
    # Clear all tables in reverse order to respect foreign key constraints
    logger.info("Clearing existing data in target database...")
    with target_engine.begin() as conn:
        for table in reversed(tables_to_migrate):
            conn.execute(text(f"DELETE FROM {table}"))
            logger.info(f"  Cleared table: {table}")
    
    total_records = 0
    
    try:
        for table_name in tables_to_migrate:
            records = migrate_table_data(source_engine, target_engine, table_name)
            total_records += records
        
        # Update sequences for PostgreSQL (for auto-increment fields)
        with target_engine.begin() as conn:
            # Update instance_configs id sequence
            result = conn.execute(text("SELECT MAX(id) FROM instance_configs"))
            max_id = result.scalar()
            if max_id:
                conn.execute(text(f"""
                    SELECT setval('instance_configs_id_seq', {max_id}, true)
                """))
            
            # Update trace_payloads id sequence if it exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.sequences 
                WHERE sequence_name = 'trace_payloads_id_seq'
            """))
            if result.scalar() > 0:
                result = conn.execute(text("SELECT MAX(id) FROM trace_payloads"))
                max_id = result.scalar()
                if max_id:
                    conn.execute(text(f"""
                        SELECT setval('trace_payloads_id_seq', {max_id}, true)
                    """))
        
        logger.info(f"\n✅ Migration completed successfully!")
        logger.info(f"   Total records migrated: {total_records}")
        
        # Verify migration
        logger.info("\nVerifying migration...")
        with target_engine.connect() as conn:
            for table in tables_to_migrate:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"  {table}: {count} records")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        source_engine.dispose()
        target_engine.dispose()


def main():
    """Main entry point."""
    print("=" * 60)
    print("SQLite to PostgreSQL Migration Tool")
    print("=" * 60)
    
    # Confirm migration
    sqlite_url = get_sqlite_url()
    postgres_url = get_postgres_url()
    
    print(f"\nThis will migrate data from:")
    print(f"  Source: {sqlite_url}")
    print(f"  Target: {postgres_url}")
    print("\n⚠️  WARNING: This will DELETE all existing data in the PostgreSQL database!")
    
    response = input("\nDo you want to continue? (yes/no): ").lower().strip()
    if response != 'yes':
        print("Migration cancelled.")
        return
    
    # Run migration
    migrate_database()


if __name__ == "__main__":
    main()