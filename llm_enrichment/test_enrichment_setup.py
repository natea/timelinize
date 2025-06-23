#!/usr/bin/env python3
"""
Test Enrichment Setup
Run this to verify the enrichment pipeline is properly configured
"""

import sqlite3
from pathlib import Path
import sys

def test_setup():
    """Test that enrichment setup is complete"""
    print("🧪 Testing Enrichment Setup")
    print("=" * 40)
    
    # 1. Check database
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    if not db_path.exists():
        print("❌ Database not found at:", db_path)
        return False
    print("✅ Database found")
    
    # 2. Connect and check schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check required tables
    required_tables = [
        'item_enrichments',
        'themes',
        'item_themes',
        'enrichment_prompts',
        'enrichment_jobs',
        'enrichment_status'
    ]
    
    for table in required_tables:
        cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone()[0] == 0:
            print(f"❌ Missing table: {table}")
            return False
    print("✅ All enrichment tables found")
    
    # 3. Check themes are loaded
    cursor.execute("SELECT COUNT(*) FROM themes")
    theme_count = cursor.fetchone()[0]
    if theme_count == 0:
        print("❌ No themes loaded")
        return False
    print(f"✅ {theme_count} themes loaded")
    
    # 4. Check prompts are loaded
    cursor.execute("SELECT COUNT(*) FROM enrichment_prompts")
    prompt_count = cursor.fetchone()[0]
    if prompt_count == 0:
        print("❌ No prompt templates loaded")
        return False
    print(f"✅ {prompt_count} prompt templates loaded")
    
    # 5. Check sample items
    cursor.execute("""
        SELECT COUNT(*) FROM items 
        WHERE deleted IS NULL 
        AND data_text IS NOT NULL
        LIMIT 1
    """)
    if cursor.fetchone()[0] == 0:
        print("❌ No items with text content found")
        return False
    print("✅ Items ready for enrichment")
    
    # 6. Show sample prompt
    print("\n📝 Sample Prompt Template:")
    cursor.execute("SELECT name, template FROM enrichment_prompts WHERE type='summary' LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"Name: {row[0]}")
        print(f"Template preview: {row[1][:200]}...")
    
    conn.close()
    return True

if __name__ == "__main__":
    if test_setup():
        print("\n✅ Setup complete! Ready to run enrichment.")
        print("\nNext step: Set your API key and run:")
        print("  export OPENAI_API_KEY='your-key'")
        print("  python3 run_enrichment_pipeline.py")
    else:
        print("\n❌ Setup incomplete. Please run:")
        print("  python3 apply_enrichment_schema.py")
        sys.exit(1)