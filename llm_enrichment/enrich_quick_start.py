#!/Users/nateaune/.pyenv/versions/3.12.8/bin/python
"""
Quick Start Script for Timelinize Enrichment

This is a simplified script to get started with enrichment quickly.
For advanced usage, see run_enrichment_pipeline.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def check_database():
    """Check if database exists and has enrichment schema"""
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    
    if not db_path.exists():
        print("❌ Error: Timeline database not found!")
        print(f"   Expected at: {db_path}")
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if enrichment tables exist
    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master 
        WHERE type='table' AND name='item_enrichments'
    """)
    
    if cursor.fetchone()[0] == 0:
        print("❌ Error: Enrichment schema not found!")
        print("   Please run: python3 apply_enrichment_schema.py")
        conn.close()
        return None
    
    return conn

def show_stats(conn):
    """Show current enrichment statistics"""
    cursor = conn.cursor()
    
    # Total items
    cursor.execute("SELECT COUNT(*) FROM items WHERE deleted IS NULL")
    total = cursor.fetchone()[0]
    
    # Enriched items
    cursor.execute("SELECT COUNT(DISTINCT item_id) FROM item_enrichments")
    enriched = cursor.fetchone()[0]
    
    # Items needing enrichment
    cursor.execute("""
        SELECT COUNT(*) FROM items i
        LEFT JOIN item_enrichments ie ON i.id = ie.item_id
        WHERE i.deleted IS NULL AND ie.id IS NULL
    """)
    need_enrichment = cursor.fetchone()[0]
    
    print("\n📊 Enrichment Statistics")
    print(f"   Total items: {total:,}")
    print(f"   Already enriched: {enriched:,} ({enriched/total*100:.1f}%)")
    print(f"   Need enrichment: {need_enrichment:,}")
    
    return need_enrichment > 0

def main():
    print("🚀 Timelinize Enrichment Quick Start")
    print("=" * 40)
    
    # Step 1: Check database
    conn = check_database()
    if not conn:
        return 1
    
    # Step 2: Show statistics
    has_items = show_stats(conn)
    
    if not has_items:
        print("\n✅ All items are already enriched!")
        conn.close()
        return 0
    
    # Step 3: Check for API keys
    import os
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    print("\n🔑 API Keys")
    print(f"   OpenAI: {'✅ Found' if has_openai else '❌ Not found'}")
    print(f"   Anthropic: {'✅ Found' if has_anthropic else '❌ Not found'}")
    
    if not has_openai and not has_anthropic:
        print("\n❌ Error: No API keys found!")
        print("   Set one of these environment variables:")
        print("   - export OPENAI_API_KEY='your-key'")
        print("   - export ANTHROPIC_API_KEY='your-key'")
        conn.close()
        return 1
    
    # Step 4: Ready to run
    print("\n✅ Ready to run enrichment!")
    print("\nNext steps:")
    print("1. Run the full pipeline:")
    print("   python3 run_enrichment_pipeline.py")
    print("\n2. Or start incremental processing:")
    print("   python3 incremental_enrichment.py")
    print("\n3. View results with datasette:")
    print("   datasette ~/Documents/timelinize-data/timeline.db")
    
    # Optional: Show sample items
    response = input("\nShow sample items that need enrichment? (y/N): ")
    if response.lower() == 'y':
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.id, i.data_type, substr(i.data_text, 1, 100) as preview
            FROM items i
            LEFT JOIN item_enrichments ie ON i.id = ie.item_id
            WHERE i.deleted IS NULL AND ie.id IS NULL
            AND i.data_text IS NOT NULL
            LIMIT 5
        """)
        
        print("\n📝 Sample items needing enrichment:")
        for row in cursor.fetchall():
            print(f"\nID: {row[0]}")
            print(f"Type: {row[1]}")
            print(f"Preview: {row[2]}...")
    
    conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())