# Datasette Setup for Timelinize Enrichments

## Quick Fix for Plugin Error

The plugin had a compatibility issue with your version of Datasette. I've created a simplified version to get you started.

## Current Setup

1. **Simple Plugin Installed**: `/Users/nateaune/.datasette/plugins/datasette_enrichment_simple.py`
   - Basic test route at `/timeline/test`
   - Adds "Test Enrichment" action to items table

2. **Full Plugin Backed Up**: `datasette_enrichment_plugin.py.backup`

## Running Datasette

```bash
# Start datasette with the fixed plugin
datasette serve ~/Documents/timelinize-data/timeline.db --plugins-dir ~/.datasette/plugins

# Or without plugins for now
datasette serve ~/Documents/timelinize-data/timeline.db
```

## Viewing Enrichment Data Without Plugin

Until the full plugin is working, you can still query enrichment data:

### View Themes
```
http://127.0.0.1:8001/timeline/themes
```

### View Items with Themes
```
http://127.0.0.1:8001/timeline/items_with_themes
```

### Custom SQL Queries
```
http://127.0.0.1:8001/timeline?sql=SELECT+*+FROM+theme_hierarchy
```

## Alternative: Install as Proper Plugin

For a more robust setup, create a proper Datasette plugin package:

```bash
# Create plugin directory
mkdir -p datasette-timelinize-enrichments
cd datasette-timelinize-enrichments

# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup

setup(
    name="datasette-timelinize-enrichments",
    version="0.1",
    py_modules=["datasette_timelinize_enrichments"],
    install_requires=["datasette", "markupsafe"],
    entry_points={
        "datasette": ["timelinize_enrichments = datasette_timelinize_enrichments"]
    },
)
EOF

# Copy simplified plugin
cp ~/Documents/code/timelinize/datasette_enrichment_simple.py datasette_timelinize_enrichments.py

# Install
pip install -e .
```

## Next Steps

1. Test basic datasette functionality first
2. Gradually add plugin features
3. Use SQL queries for enrichment data until full UI is ready

## Useful Queries

### See enrichment status
```sql
SELECT 
    COUNT(*) as total_items,
    (SELECT COUNT(DISTINCT item_id) FROM item_enrichments) as enriched_items
FROM items;
```

### Browse themes
```sql
SELECT * FROM theme_hierarchy ORDER BY path;
```

### Find items by theme
```sql
SELECT i.id, i.data_text, t.name as theme, it.confidence_score
FROM items i
JOIN item_themes it ON i.id = it.item_id
JOIN themes t ON it.theme_id = t.id
WHERE t.name LIKE '%Work%'
ORDER BY it.confidence_score DESC;