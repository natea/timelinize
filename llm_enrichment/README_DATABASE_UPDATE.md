# Database Update Instructions

## Quick Start

To update your Timelinize database with the enrichment schema:

```bash
# 1. Apply the schema updates (creates automatic backup)
python3 apply_enrichment_schema.py

# 2. Validate the updates
python3 validate_enrichment_schema.py
```

## What Gets Added

The update adds these new capabilities to your timeline.db:

### New Tables
- **item_enrichments** - Stores LLM-generated summaries and insights
- **themes** - Hierarchical categorization system (Work, Personal, Health, etc.)
- **item_themes** - Maps timeline items to themes
- **enrichment_prompts** - Reusable LLM prompt templates
- **enrichment_jobs** - Tracks batch processing progress
- **enrichment_status** - Processing status for each item
- **item_relationships** - Discovered connections between items

### Pre-loaded Data
- 10 main theme categories with 40+ subcategories
- 7 enrichment prompt templates for different analysis types

## Safety Features

- **Automatic Backup**: Creates timestamped backup before changes
- **Safe Updates**: Uses "IF NOT EXISTS" to prevent data loss
- **Transaction Safety**: All changes in a single transaction
- **Validation Script**: Verify successful installation

## Manual Commands

If you prefer manual control:

```bash
# Backup first
cp ~/Documents/timelinize-data/timeline.db ~/Documents/timelinize-data/timeline.db.backup

# Apply schema
sqlite3 ~/Documents/timelinize-data/timeline.db < enrichment_schema_design.sql

# Apply prompts
sqlite3 ~/Documents/timelinize-data/timeline.db < enrichment_prompts.sql

# Validate
./validate_enrichment_schema.py
```

## Next Steps

After updating the database:

1. Configure your LLM provider (Claude, GPT-4, etc.)
2. Start enriching items with the processing pipeline
3. View enriched data using Datasette

## Troubleshooting

If something goes wrong:

1. Check the error message
2. Restore from the automatic backup
3. Run the validation script to see what's missing

The scripts are safe to run multiple times - they won't duplicate data.