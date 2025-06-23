# Instructions for Updating Timeline Database with Enrichment Tables

## Prerequisites
- Backup your existing timeline.db before making changes
- Ensure SQLite3 is installed and accessible

## Step 1: Backup Your Database
```bash
cp ~/Documents/timelinize-data/timeline.db ~/Documents/timelinize-data/timeline.db.backup-$(date +%Y%m%d-%H%M%S)
```

## Step 2: Apply Schema Updates

### Option A: Using SQLite3 Command Line
```bash
# Apply the enrichment schema
sqlite3 ~/Documents/timelinize-data/timeline.db < enrichment_schema_design.sql

# Apply the prompt templates
sqlite3 ~/Documents/timelinize-data/timeline.db < enrichment_prompts.sql
```

### Option B: Using Python Script
Create and run this script to apply updates with error handling:

```python
#!/usr/bin/env python3
import sqlite3
import json
from pathlib import Path

def update_database():
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    
    print(f"Updating database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Read and apply schema updates
        with open('enrichment_schema_design.sql', 'r') as f:
            schema_sql = f.read()
            cursor.executescript(schema_sql)
        print("✓ Schema updates applied")
        
        # Read and apply prompt templates
        with open('enrichment_prompts.sql', 'r') as f:
            prompts_sql = f.read()
            cursor.executescript(prompts_sql)
        print("✓ Prompt templates inserted")
        
        # Load and insert theme taxonomy
        with open('theme_taxonomy.json', 'r') as f:
            taxonomy = json.load(f)
            insert_themes(cursor, taxonomy['theme_taxonomy']['themes'])
        print("✓ Theme taxonomy loaded")
        
        conn.commit()
        print("\n✅ Database updated successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error updating database: {e}")
        raise
    finally:
        conn.close()

def insert_themes(cursor, themes, parent_id=None, level=0):
    """Recursively insert themes into the database"""
    for theme in themes:
        cursor.execute("""
            INSERT INTO themes (id, parent_id, name, description, level, color, icon, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        
        # Insert child themes
        if 'children' in theme:
            insert_themes(cursor, theme['children'], theme['id'], level + 1)

if __name__ == "__main__":
    update_database()
```

Save as `update_enrichment_schema.py` and run:
```bash
python3 update_enrichment_schema.py
```

## Step 3: Verify the Updates

### Check New Tables
```bash
sqlite3 ~/Documents/timelinize-data/timeline.db ".tables" | grep -E "(enrichment|theme)"
```

Expected output:
```
enrichment_jobs       enrichment_status     item_enrichments
enrichment_prompts    item_relationships    item_themes
themes
```

### Verify Theme Hierarchy
```bash
sqlite3 ~/Documents/timelinize-data/timeline.db "SELECT COUNT(*) as theme_count FROM themes;"
sqlite3 ~/Documents/timelinize-data/timeline.db "SELECT id, name, level FROM themes WHERE parent_id IS NULL;"
```

### Check Views
```bash
sqlite3 ~/Documents/timelinize-data/timeline.db ".schema items_with_themes"
sqlite3 ~/Documents/timelinize-data/timeline.db ".schema theme_hierarchy"
```

## Step 4: Test the New Tables

### Insert Test Enrichment
```sql
-- Test enrichment for an existing item
INSERT INTO item_enrichments (item_id, enrichment_type, content, confidence_score, model_name)
VALUES (
    1, 
    'summary', 
    'Test enrichment content', 
    0.85, 
    'test-model'
);

-- Test theme assignment
INSERT INTO item_themes (item_id, theme_id, confidence_score, model_name)
VALUES (1, 101, 0.9, 'test-model');
```

### Query Test Data
```sql
-- Check enrichment
SELECT * FROM item_enrichments WHERE item_id = 1;

-- Check themed items view
SELECT * FROM items_with_themes WHERE id = 1;
```

## Step 5: Install Datasette Plugin (Optional)

If using Datasette for visualization:

```bash
# Copy plugin files to datasette plugins directory
mkdir -p ~/.datasette/plugins
cp datasette_enrichment_plugin.py ~/.datasette/plugins/

# Create static files directory
mkdir -p ~/.datasette/static-plugins/timelinize-enrichments
cp enrichment-styles.css ~/.datasette/static-plugins/timelinize-enrichments/

# Restart datasette
datasette serve ~/Documents/timelinize-data/timeline.db --plugins-dir ~/.datasette/plugins
```

## Troubleshooting

### If Tables Already Exist
The schema uses `CREATE TABLE IF NOT EXISTS`, so it's safe to run multiple times. However, if you need to recreate tables:

```sql
-- Drop and recreate specific tables (CAUTION: Data loss!)
DROP TABLE IF EXISTS item_enrichments;
DROP TABLE IF EXISTS item_themes;
-- Then rerun the schema creation
```

### Check for Errors
```bash
# Check SQLite error log
sqlite3 ~/Documents/timelinize-data/timeline.db ".log stderr"
```

### Rollback if Needed
```bash
# Restore from backup
cp ~/Documents/timelinize-data/timeline.db.backup-TIMESTAMP ~/Documents/timelinize-data/timeline.db
```

## Next Steps

After successful database update:

1. **Configure LLM Provider**: Set up API keys for your chosen LLM (Claude, GPT-4, etc.)
2. **Start Enrichment Pipeline**: Run the pipeline to begin enriching existing items
3. **Monitor Progress**: Use Datasette or queries to track enrichment progress
4. **Set Up Incremental Processing**: Configure automatic enrichment for new items

## Useful Queries

### Check Enrichment Progress
```sql
SELECT 
    COUNT(DISTINCT i.id) as total_items,
    COUNT(DISTINCT ie.item_id) as enriched_items,
    ROUND(COUNT(DISTINCT ie.item_id) * 100.0 / COUNT(DISTINCT i.id), 2) as percent_enriched
FROM items i
LEFT JOIN item_enrichments ie ON i.id = ie.item_id;
```

### View Theme Distribution
```sql
SELECT 
    t.name as theme,
    COUNT(it.item_id) as item_count,
    ROUND(AVG(it.confidence_score), 2) as avg_confidence
FROM themes t
LEFT JOIN item_themes it ON t.id = it.theme_id
GROUP BY t.id
ORDER BY item_count DESC;