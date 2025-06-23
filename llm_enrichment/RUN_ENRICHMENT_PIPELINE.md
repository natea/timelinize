# Running the Timelinize LLM Enrichment Pipeline

## Overview

The Timelinize enrichment pipeline uses Large Language Models (LLMs) to automatically analyze and enrich your timeline items with:
- **Summaries** - Concise descriptions of each item
- **Theme Classification** - Categorization into hierarchical themes (Work, Personal, Health, etc.)
- **Sentiment Analysis** - Emotional tone detection
- **Entity Extraction** - People, places, organizations mentioned
- **Relationship Discovery** - Connections between items

## Prerequisites

### 1. Database Setup
First, ensure the enrichment schema is applied to your database:

```bash
# Backup your database first!
cp ~/Documents/timelinize-data/timeline.db ~/Documents/timelinize-data/timeline.db.backup-$(date +%Y%m%d-%H%M%S)

# Apply the enrichment schema
python3 apply_enrichment_schema.py

# Verify the schema was applied
python3 validate_enrichment_schema.py
```

### 2. LLM Provider Setup
Choose and configure your LLM provider:

#### OpenAI (GPT-4)
```bash
export OPENAI_API_KEY="your-api-key-here"
```

#### Anthropic (Claude)
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 3. Install Dependencies
```bash
pip install openai anthropic sqlite3 asyncio
```

## Running the Pipeline

### Basic Usage

The simplest way to run the enrichment pipeline:

```bash
python3 run_enrichment_pipeline.py
```

This will:
1. Show current enrichment statistics
2. Find items that need enrichment
3. Ask for confirmation
4. Process items in batches
5. Store results in the database

### Advanced Usage

#### 1. Process Specific Item Types

Edit `run_enrichment_pipeline.py` to add filters:

```python
# Only enrich messages
filter_query = "data_type LIKE '%message%'"

# Only items from last week
filter_query = "timestamp > strftime('%s', 'now', '-7 days')"

# Only items from specific data source
filter_query = "data_source_id = 1"

# Complex filters
filter_query = """
    data_type IN ('message/sms', 'message/imessage', 'email') 
    AND timestamp > strftime('%s', '2024-01-01')
"""
```

#### 2. Choose Enrichment Types

Select which enrichments to run:

```python
enrichment_types = [
    EnrichmentType.SUMMARY,                # Always recommended
    EnrichmentType.THEME_CLASSIFICATION,   # Categorize items
    # EnrichmentType.SENTIMENT_ANALYSIS,   # Emotional analysis
    # EnrichmentType.ENTITY_EXTRACTION,    # Extract people/places
]
```

#### 3. Adjust Processing Parameters

Configure the pipeline for your needs:

```python
self.config = PipelineConfig(
    batch_size=50,                    # Items per batch
    max_concurrent_requests=5,        # Parallel LLM requests
    retry_attempts=3,                 # Retries on failure
    rate_limit_requests_per_minute=60,# API rate limiting
    temperature=0.3,                  # LLM creativity (0-1)
    cache_enabled=True,              # Cache results
)
```

### Monitoring Progress

#### Check Statistics
```sql
-- In SQLite
SELECT 
    COUNT(DISTINCT i.id) as total_items,
    COUNT(DISTINCT ie.item_id) as enriched_items,
    ROUND(COUNT(DISTINCT ie.item_id) * 100.0 / COUNT(DISTINCT i.id), 2) as percent_complete
FROM items i
LEFT JOIN item_enrichments ie ON i.id = ie.item_id;
```

#### View Recent Enrichments
```sql
SELECT 
    i.data_text,
    ie.enrichment_type,
    ie.content as enrichment,
    ie.confidence_score,
    datetime(ie.generated, 'unixepoch') as enriched_at
FROM item_enrichments ie
JOIN items i ON ie.item_id = i.id
ORDER BY ie.generated DESC
LIMIT 10;
```

#### Theme Distribution
```sql
SELECT 
    t.name as theme,
    COUNT(it.item_id) as item_count,
    ROUND(AVG(it.confidence_score), 2) as avg_confidence
FROM themes t
JOIN item_themes it ON t.id = it.theme_id
GROUP BY t.id
ORDER BY item_count DESC;
```

## Incremental Processing

For continuous enrichment of new items:

### 1. Create Processing Script
```python
#!/usr/bin/env python3
# incremental_enrichment.py
import asyncio
from incremental_processing_system import IncrementalProcessor
from run_enrichment_pipeline import EnrichmentRunner

async def run_incremental():
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    
    # Initialize components
    runner = EnrichmentRunner(db_path, llm_provider="openai")
    processor = IncrementalProcessor(runner.conn, runner.pipeline)
    
    # Start continuous processing
    await processor.start()

if __name__ == "__main__":
    asyncio.run(run_incremental())
```

### 2. Run as Background Service
```bash
# Run in background with nohup
nohup python3 incremental_enrichment.py > enrichment.log 2>&1 &

# Or use systemd service (create /etc/systemd/system/timelinize-enrichment.service)
[Unit]
Description=Timelinize Enrichment Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/timelinize
Environment="OPENAI_API_KEY=your-key"
ExecStart=/usr/bin/python3 /path/to/incremental_enrichment.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Using Datasette UI

For a web interface to view enrichments:

```bash
# Install datasette plugin
cp datasette_enrichment_plugin.py ~/.datasette/plugins/
cp enrichment-styles.css ~/.datasette/static/

# Run datasette
datasette ~/Documents/timelinize-data/timeline.db \
    --plugins-dir ~/.datasette/plugins \
    --static static:$HOME/.datasette/static
```

Then visit:
- http://localhost:8001/timeline/items_with_themes - Items with theme badges
- http://localhost:8001/timeline/enrichment_dashboard - Statistics dashboard
- http://localhost:8001/timeline/themes - Browse theme hierarchy

## Troubleshooting

### Common Issues

1. **No API Key**
   ```
   Error: OPENAI_API_KEY environment variable not set
   ```
   Solution: Export the API key in your shell or add to `.bashrc`

2. **Rate Limiting**
   ```
   Error: Rate limit exceeded
   ```
   Solution: Reduce `max_concurrent_requests` or `rate_limit_requests_per_minute`

3. **Memory Issues**
   ```
   Error: Out of memory
   ```
   Solution: Reduce `batch_size` or process fewer items at once

4. **Database Locked**
   ```
   Error: database is locked
   ```
   Solution: Ensure no other process is accessing the database

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Error Items

```sql
-- Find items with enrichment errors
SELECT 
    es.item_id,
    i.data_text,
    es.error_count,
    es.last_error
FROM enrichment_status es
JOIN items i ON es.item_id = i.id
WHERE es.error_count > 0
ORDER BY es.last_enriched DESC;
```

## Cost Estimation

Approximate costs per 1000 items:

| Provider | Model | Summary | Themes | Total |
|----------|-------|---------|--------|-------|
| OpenAI | GPT-4 | $3-5 | $2-4 | $5-9 |
| OpenAI | GPT-3.5 | $0.50-1 | $0.30-0.60 | $0.80-1.60 |
| Anthropic | Claude 3 | $2-4 | $1.50-3 | $3.50-7 |

Factors affecting cost:
- Item content length
- Number of enrichment types
- Retry attempts
- Model choice

## Best Practices

1. **Start Small**: Test with 100-1000 items first
2. **Monitor Costs**: Track API usage and costs
3. **Use Caching**: Enable cache to avoid re-processing
4. **Batch Similar Items**: Group by data_type for efficiency
5. **Regular Backups**: Always backup before bulk operations
6. **Review Quality**: Spot-check enrichments for accuracy
7. **Iterate on Prompts**: Customize prompts for better results

## Next Steps

After enriching your items:

1. **Explore the Data**: Use Datasette or SQL queries to explore enrichments
2. **Build Visualizations**: Create charts of theme distribution over time
3. **Export Insights**: Generate reports of patterns and trends
4. **Refine Categories**: Adjust theme taxonomy based on your data
5. **Automate Workflows**: Set up scheduled enrichment jobs

## Example Queries

### Find Important Meetings
```sql
SELECT 
    i.data_text,
    ie.content as summary,
    GROUP_CONCAT(t.name) as themes
FROM items i
JOIN item_enrichments ie ON i.id = ie.item_id
JOIN item_themes it ON i.id = it.item_id
JOIN themes t ON it.theme_id = t.id
WHERE ie.enrichment_type = 'summary'
    AND t.name IN ('Work & Career', 'Meetings')
    AND ie.content LIKE '%important%'
GROUP BY i.id
ORDER BY i.timestamp DESC;
```

### Personal Growth Timeline
```sql
SELECT 
    date(i.timestamp, 'unixepoch') as date,
    COUNT(*) as growth_items,
    AVG(s.confidence_score) as avg_confidence
FROM items i
JOIN item_themes it ON i.id = it.item_id
JOIN themes t ON it.theme_id = t.id
WHERE t.name IN ('Learning & Education', 'Personal Development', 'Skills')
GROUP BY date(i.timestamp, 'unixepoch')
ORDER BY date;
```

### Communication Patterns
```sql
SELECT 
    strftime('%Y-%m', datetime(i.timestamp, 'unixepoch')) as month,
    i.data_type,
    COUNT(*) as message_count,
    AVG(CASE WHEN se.content LIKE '%positive%' THEN 1 ELSE 0 END) as positivity_rate
FROM items i
LEFT JOIN item_enrichments se ON i.id = se.item_id AND se.enrichment_type = 'sentiment'
WHERE i.data_type LIKE '%message%'
GROUP BY month, i.data_type
ORDER BY month DESC;
```