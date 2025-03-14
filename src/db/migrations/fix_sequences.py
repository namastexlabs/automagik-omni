#!/usr/bin/env python3
"""
Migration script to fix sequences in the database.
"""

import logging
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to import properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_sequences(engine):
    """Fix the sequences in the database."""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get the name of the users table sequence
        result = session.execute(text("""
            SELECT pg_get_serial_sequence('users', 'id') as seq_name
        """))
        sequence_name = result.scalar()
        
        if not sequence_name:
            logger.error("Could not find sequence for users.id column")
            return
            
        logger.info(f"Found sequence name: {sequence_name}")
        
        # Get the current maximum ID from the users table
        result = session.execute(text("""
            SELECT COALESCE(MAX(id), 0) FROM users
        """))
        max_id = result.scalar() or 0
        
        logger.info(f"Current maximum user id: {max_id}")
        
        # Set the sequence to start after the maximum ID
        session.execute(text(f"""
            SELECT setval('{sequence_name}', {max_id}, true)
        """))
        
        # Verify that the sequence is set correctly
        result = session.execute(text(f"""
            SELECT last_value FROM {sequence_name}
        """))
        current_value = result.scalar()
        
        logger.info(f"Sequence {sequence_name} set to {current_value}")
        
        # Commit the changes
        session.commit()
        logger.info("Successfully fixed sequences")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error fixing sequences: {e}", exc_info=True)
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
    
    # Fix sequences
    logger.info("Fixing sequences...")
    fix_sequences(engine)
    
    logger.info("Migration completed successfully!")

if __name__ == "__main__":
    main() 