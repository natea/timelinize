#!/usr/bin/env python3
"""
Validate Enrichment Schema Installation

Quick script to check if the enrichment schema was applied correctly
"""

import sqlite3
from pathlib import Path
import sys

def validate_schema():
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Expected tables
    expected_tables = [
        'item_enrichments',
        'themes', 
        'item_themes',
        'enrichment_prompts',
        'enrichment_jobs',
        'enrichment_status',
        'item_relationships'
    ]
    
    # Check tables
    print("Checking tables...")
    missing_tables = []
    for table in expected_tables:
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if cursor.fetchone()[0] == 0:
            missing_tables.append(table)
            print(f"  ❌ {table} - MISSING")
        else:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table} - OK ({count} rows)")
    
    # Check views
    print("\nChecking views...")
    expected_views = ['items_with_themes', 'theme_hierarchy']
    for view in expected_views:
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name=?",
            (view,)
        )
        if cursor.fetchone()[0] == 0:
            print(f"  ❌ {view} - MISSING")
        else:
            print(f"  ✓ {view} - OK")
    
    # Check indexes
    print("\nChecking indexes...")
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%enrichment%'"
    )
    indexes = cursor.fetchall()
    print(f"  Found {len(indexes)} enrichment indexes")
    
    conn.close()
    
    if missing_tables:
        print(f"\n❌ Schema validation FAILED - {len(missing_tables)} tables missing")
        return False
    else:
        print("\n✅ Schema validation PASSED - All tables present")
        return True

if __name__ == "__main__":
    success = validate_schema()
    sys.exit(0 if success else 1)