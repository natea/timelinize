#!/usr/bin/env python3
"""
Load Theme Taxonomy into Existing Schema

Use this if your schema is already created but themes are missing
"""

import sqlite3
import json
from pathlib import Path

def load_themes():
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    taxonomy_file = Path(__file__).parent / 'theme_taxonomy.json'
    
    print(f"Loading themes into: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current theme count
    cursor.execute("SELECT COUNT(*) FROM themes")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"⚠️  Database already has {existing_count} themes")
        response = input("Do you want to reload themes? This will clear existing themes. (y/N): ")
        if response.lower() != 'y':
            print("Cancelled")
            return
        
        # Clear existing themes (cascades to item_themes)
        cursor.execute("DELETE FROM themes")
        print("Cleared existing themes")
    
    # Load taxonomy
    with open(taxonomy_file, 'r') as f:
        taxonomy = json.load(f)
    
    def insert_themes(themes, parent_id=None, level=0):
        for theme in themes:
            cursor.execute("""
                INSERT INTO themes 
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
    
    try:
        insert_themes(taxonomy['theme_taxonomy']['themes'])
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM themes")
        new_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, name FROM themes WHERE parent_id IS NULL ORDER BY id")
        top_themes = cursor.fetchall()
        
        print(f"\n✅ Successfully loaded {new_count} themes!")
        print("\nTop-level themes:")
        for theme_id, name in top_themes:
            print(f"  {theme_id}: {name}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error loading themes: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    load_themes()