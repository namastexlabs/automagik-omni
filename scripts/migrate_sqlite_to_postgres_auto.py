#!/usr/bin/env python3
"""
Non-interactive version of the migration script.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from migrate_sqlite_to_postgres import migrate_database, get_sqlite_url, get_postgres_url

if __name__ == "__main__":
    print("=" * 60)
    print("SQLite to PostgreSQL Migration Tool (Auto)")
    print("=" * 60)
    
    sqlite_url = get_sqlite_url()
    postgres_url = get_postgres_url()
    
    print(f"\nMigrating data from:")
    print(f"  Source: {sqlite_url}")
    print(f"  Target: {postgres_url}")
    print("\nStarting migration...")
    
    migrate_database()