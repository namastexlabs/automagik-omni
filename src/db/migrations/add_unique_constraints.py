#!/usr/bin/env python3
"""
Migration script to add unique constraints and handle duplicate users.
Run this script before deploying the updated code with unique constraints.
"""

import logging
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to import properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import config
from src.db.models import User

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def deduplicate_users(engine):
    """Find and resolve duplicate users by merging them."""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Find all phone numbers with multiple users
        result = session.execute(text("""
            SELECT phone_number, COUNT(*) as count, array_agg(id) as ids
            FROM users
            WHERE phone_number IS NOT NULL
            GROUP BY phone_number
            HAVING COUNT(*) > 1
        """))
        
        for row in result:
            phone_number = row[0]
            count = row[1]
            ids = row[2]
            
            logger.info(f"Found {count} duplicate users for phone {phone_number}: {ids}")
            
            # Keep the first ID as the primary user
            primary_id = ids[0]
            duplicate_ids = ids[1:]
            
            # For each duplicate user:
            for dup_id in duplicate_ids:
                # 1. Update sessions to point to primary user
                session.execute(text("""
                    UPDATE sessions SET user_id = :primary_id
                    WHERE user_id = :dup_id
                """), {"primary_id": primary_id, "dup_id": dup_id})
                
                # 2. Update messages to point to primary user
                session.execute(text("""
                    UPDATE chat_messages SET user_id = :primary_id
                    WHERE user_id = :dup_id
                """), {"primary_id": primary_id, "dup_id": dup_id})
                
                # 3. Update memories to point to primary user
                session.execute(text("""
                    UPDATE memories SET user_id = :primary_id
                    WHERE user_id = :dup_id
                """), {"primary_id": primary_id, "dup_id": dup_id})
                
                # 4. Delete the duplicate user
                session.execute(text("""
                    DELETE FROM users WHERE id = :dup_id
                """), {"dup_id": dup_id})
                
                logger.info(f"Merged duplicate user {dup_id} into primary user {primary_id}")
        
        # Commit all changes
        session.commit()
        logger.info("Successfully deduplicated users")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deduplicating users: {e}", exc_info=True)
        raise
    finally:
        session.close()

def add_unique_constraint(engine):
    """Add unique constraint to the users table."""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Add unique constraint if it doesn't exist
        session.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'users_phone_number_key'
                ) THEN
                    ALTER TABLE users ADD CONSTRAINT users_phone_number_key UNIQUE (phone_number);
                END IF;
            END$$;
        """))
        
        # Check if sessions.id is already UUID type
        result = session.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sessions' AND column_name = 'id'
        """))
        column_type = result.scalar()
        
        # If sessions.id is UUID type, update the model to match
        if column_type and column_type.lower() == 'uuid':
            logger.info("sessions.id is UUID type in database, updating models to match")
            
            # For existing installations, make sure chat_messages.session_id is also compatible
            session.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'chat_messages' AND column_name = 'session_id'
                    ) THEN
                        -- Drop the foreign key constraint if it exists
                        IF EXISTS (
                            SELECT 1 FROM pg_constraint 
                            WHERE conname = 'chat_messages_session_id_fkey'
                        ) THEN
                            ALTER TABLE chat_messages DROP CONSTRAINT chat_messages_session_id_fkey;
                        END IF;
                        
                        -- Alter the column type to UUID if it's not already
                        IF (SELECT data_type FROM information_schema.columns 
                            WHERE table_name = 'chat_messages' AND column_name = 'session_id') != 'uuid' THEN
                            ALTER TABLE chat_messages ALTER COLUMN session_id TYPE UUID USING session_id::uuid;
                        END IF;
                        
                        -- Re-add the foreign key constraint
                        ALTER TABLE chat_messages 
                        ADD CONSTRAINT chat_messages_session_id_fkey 
                        FOREIGN KEY (session_id) REFERENCES sessions(id);
                    END IF;
                END$$;
            """))
        
        session.commit()
        logger.info("Successfully added unique constraint to users.phone_number and fixed schema issues")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error in migration: {e}", exc_info=True)
        raise
    finally:
        session.close()

def ensure_uuid_compatibility(engine):
    """Ensure that session.id and chat_messages.session_id are UUID compatible."""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if sessions table exists
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sessions'
            )
        """))
        sessions_exist = result.scalar()
        
        if not sessions_exist:
            logger.info("Sessions table doesn't exist yet, no need for UUID compatibility check")
            return
            
        # Check if sessions.id is already UUID type
        result = session.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sessions' AND column_name = 'id'
        """))
        column_type = result.scalar()
        
        # If sessions.id is not UUID type, convert it
        if column_type and column_type.lower() != 'uuid':
            logger.info(f"sessions.id is {column_type} type, converting to UUID")
            
            # Create a temporary table with UUID type
            session.execute(text("""
                CREATE TABLE sessions_new (
                    id UUID PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    platform VARCHAR NOT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE,
                    updated_at TIMESTAMP WITHOUT TIME ZONE,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """))
            
            # Copy data with conversion
            session.execute(text("""
                INSERT INTO sessions_new
                SELECT 
                    CASE 
                        WHEN id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN id::uuid
                        ELSE uuid_generate_v4()
                    END as id,
                    user_id, platform, created_at, updated_at
                FROM sessions
            """))
            
            # Drop old table and rename new one
            session.execute(text("DROP TABLE sessions CASCADE"))
            session.execute(text("ALTER TABLE sessions_new RENAME TO sessions"))
            
            # Recreate indexes
            session.execute(text("CREATE INDEX idx_sessions_user_id ON sessions (user_id)"))
            
            logger.info("Successfully converted sessions.id to UUID type")
        
        # Check if chat_messages table exists
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'chat_messages'
            )
        """))
        messages_exist = result.scalar()
        
        if messages_exist:
            # Check if chat_messages.session_id is UUID type
            result = session.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'chat_messages' AND column_name = 'session_id'
            """))
            column_type = result.scalar()
            
            # If chat_messages.session_id is not UUID type, convert it
            if column_type and column_type.lower() != 'uuid':
                logger.info(f"chat_messages.session_id is {column_type} type, converting to UUID")
                
                # Create a mapping table for old IDs to new UUIDs
                session.execute(text("""
                    CREATE TEMPORARY TABLE session_id_mapping AS
                    SELECT 
                        id as old_id,
                        id::uuid as new_id
                    FROM sessions
                """))
                
                # Create a temporary table with UUID type
                session.execute(text("""
                    CREATE TABLE chat_messages_new (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        session_id UUID NOT NULL,
                        user_id INTEGER NOT NULL,
                        agent_id INTEGER,
                        role VARCHAR NOT NULL,
                        text_content TEXT,
                        media_url VARCHAR,
                        mime_type VARCHAR,
                        message_type VARCHAR,
                        flagged VARCHAR,
                        user_feedback VARCHAR,
                        tool_calls JSON,
                        tool_outputs JSON,
                        raw_payload JSON,
                        message_timestamp TIMESTAMP WITHOUT TIME ZONE,
                        FOREIGN KEY(session_id) REFERENCES sessions(id),
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(agent_id) REFERENCES agents(id)
                    )
                """))
                
                # Copy data with conversion
                session.execute(text("""
                    INSERT INTO chat_messages_new
                    SELECT 
                        cm.id,
                        CASE 
                            WHEN cm.session_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN cm.session_id::uuid
                            ELSE (SELECT new_id FROM session_id_mapping WHERE old_id = cm.session_id)
                        END as session_id,
                        cm.user_id, cm.agent_id, cm.role, cm.text_content, cm.media_url,
                        cm.mime_type, cm.message_type, cm.flagged, cm.user_feedback,
                        cm.tool_calls, cm.tool_outputs, cm.raw_payload, cm.message_timestamp
                    FROM chat_messages cm
                """))
                
                # Drop old table and rename new one
                session.execute(text("DROP TABLE chat_messages"))
                session.execute(text("ALTER TABLE chat_messages_new RENAME TO chat_messages"))
                
                # Recreate indexes
                session.execute(text("""
                    CREATE INDEX idx_chat_messages_session_id ON chat_messages (session_id);
                    CREATE INDEX idx_chat_messages_user_id ON chat_messages (user_id);
                    CREATE INDEX idx_chat_messages_agent_id ON chat_messages (agent_id);
                """))
                
                logger.info("Successfully converted chat_messages.session_id to UUID type")
        
        session.commit()
        logger.info("UUID compatibility check and conversion completed successfully")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error ensuring UUID compatibility: {e}", exc_info=True)
        raise
    finally:
        session.close()

def main():
    """Run the migration."""
    # Create engine with connection pooling
    logger.info(f"Connecting to database: {config.database.uri}")
    engine = create_engine(
        str(config.database.uri),
        pool_size=config.database.pool_size,
        max_overflow=config.database.max_overflow,
        pool_timeout=config.database.pool_timeout
    )
    
    logger.info("Starting migration...")
    
    # First ensure UUID compatibility
    logger.info("Ensuring UUID compatibility...")
    ensure_uuid_compatibility(engine)
    
    # Then deduplicate users
    logger.info("Deduplicating users...")
    deduplicate_users(engine)
    
    # Finally add unique constraint
    logger.info("Adding unique constraint...")
    add_unique_constraint(engine)
    
    logger.info("Migration completed successfully!")

if __name__ == "__main__":
    main() 