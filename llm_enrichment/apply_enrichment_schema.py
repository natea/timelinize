#!/usr/bin/env python3
"""
Apply Timelinize Enrichment Schema Updates

This script safely applies the enrichment schema updates to your timeline.db
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import sys

def create_backup(db_path):
    """Create a backup of the database"""
    backup_path = db_path.with_suffix(f'.backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}.db')
    print(f"Creating backup: {backup_path}")
    
    # Use SQLite backup API
    source = sqlite3.connect(db_path)
    dest = sqlite3.connect(backup_path)
    source.backup(dest)
    source.close()
    dest.close()
    
    return backup_path

def apply_schema_updates(conn):
    """Apply the enrichment schema"""
    cursor = conn.cursor()
    
    # Read schema file
    schema_file = Path(__file__).parent / 'enrichment_schema_design.sql'
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Execute schema
    cursor.executescript(schema_sql)
    print("✓ Schema tables created")

def apply_prompt_templates(conn):
    """Insert prompt templates"""
    cursor = conn.cursor()
    
    # Read prompts file
    prompts_file = Path(__file__).parent / 'enrichment_prompts.sql'
    with open(prompts_file, 'r') as f:
        prompts_sql = f.read()
    
    # Execute prompts
    cursor.executescript(prompts_sql)
    print("✓ Prompt templates inserted")

def insert_theme_taxonomy(conn):
    """Load and insert theme taxonomy"""
    cursor = conn.cursor()
    
    # Read taxonomy file
    taxonomy_file = Path(__file__).parent / 'theme_taxonomy.json'
    with open(taxonomy_file, 'r') as f:
        taxonomy = json.load(f)
    
    def insert_themes(themes, parent_id=None, level=0):
        for theme in themes:
            cursor.execute("""
                INSERT OR IGNORE INTO themes 
                (id, parent_id, name, description, level, color, icon, keywords, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                theme['id'],
                parent_id,
                theme['name'],
                theme.get('description', ''),
                level,
                theme.get('color', ''),
                theme.get('icon', ''),
                ','.join(theme.get('keywords', []))
            ))
            
            if 'children' in theme:
                insert_themes(theme['children'], theme['id'], level + 1)
    
    insert_themes(taxonomy['theme_taxonomy']['themes'])
    print("✓ Theme taxonomy loaded")

def verify_updates(conn):
    """Verify the updates were successful"""
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE '%enrichment%' OR name LIKE '%theme%'
        ORDER BY name
    """)
    tables = cursor.fetchall()
    print("\nNew tables created:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check theme count
    cursor.execute("SELECT COUNT(*) FROM themes")
    theme_count = cursor.fetchone()[0]
    print(f"\nThemes loaded: {theme_count}")
    
    # Check prompt count
    cursor.execute("SELECT COUNT(*) FROM enrichment_prompts")
    prompt_count = cursor.fetchone()[0]
    print(f"Prompt templates: {prompt_count}")

def main():
    # Database path
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    print(f"Updating database: {db_path}")
    
    try:
        # Create backup
        backup_path = create_backup(db_path)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        
        # Apply updates
        apply_schema_updates(conn)
        apply_prompt_templates(conn)
        insert_theme_taxonomy(conn)
        
        # Commit changes
        conn.commit()
        
        # Verify
        verify_updates(conn)
        
        conn.close()
        
        print("\n✅ Database updated successfully!")
        print(f"Backup saved at: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ Error updating database: {e}")
        print("Database has been rolled back. No changes were made.")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    main()