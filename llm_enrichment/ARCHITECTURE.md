# Timelinize LLM Enrichment Architecture

## Overview

This architecture enables enriching Timelinize timeline data with LLM-generated insights, summaries, and thematic classifications. The system is designed for scalability, quality control, and seamless integration with the existing Timelinize infrastructure.

## Architecture Components

### 1. Database Schema Extensions

The enrichment system extends the existing `timeline.db` with new tables:

- **`item_enrichments`**: Stores LLM-generated content (summaries, insights, etc.)
- **`themes`**: Hierarchical taxonomy for categorizing timeline items
- **`item_themes`**: Maps items to themes with confidence scores
- **`enrichment_prompts`**: Stores reusable prompt templates
- **`enrichment_jobs`**: Tracks batch processing jobs
- **`enrichment_status`**: Monitors processing status per item
- **`item_relationships`**: Stores discovered relationships between items

See `enrichment_schema_design.sql` for complete schema details.

### 2. Theme Taxonomy

A comprehensive hierarchical theme system with 10 top-level categories:
- Work & Career
- Personal & Family  
- Health & Wellness
- Travel & Transportation
- Finance & Shopping
- Education & Learning
- Entertainment & Media
- Technology & Digital
- Life Events & Milestones
- Community & Society

Each category has 4-5 subcategories for fine-grained classification. See `theme_taxonomy.json` for the complete structure.

### 3. LLM Processing Pipeline

The pipeline (`llm_pipeline_architecture.py`) provides:

- **Modular Processors**: Separate processors for each enrichment type
- **Batch Processing**: Efficient handling of multiple items
- **Rate Limiting**: Token bucket algorithm to respect API limits
- **Retry Logic**: Exponential backoff for transient failures
- **Caching**: Reduce redundant API calls
- **Async/Concurrent**: Maximize throughput with controlled concurrency

#### Pipeline Flow:
1. Items are fetched from the database in batches
2. Each batch is processed through registered enrichment processors
3. Results are validated and stored
4. Progress is tracked in the enrichment_status table

### 4. Quality Control System

The quality control system (`quality_control_system.py`) ensures output reliability:

- **Multi-validator Framework**: 
  - Length validation
  - Coherence checking
  - Factual consistency
  - Theme consistency
  - Format validation
  - Confidence calibration

- **Quality Levels**: HIGH, MEDIUM, LOW, FAILED
- **Human Review Queue**: Low-quality outputs flagged for review
- **Continuous Improvement**: Metrics collection for optimization

### 5. Incremental Processing

The incremental system (`incremental_processing_system.py`) handles new data:

- **Change Detection**: Monitors for new/modified items
- **Processing Strategies**:
  - IMMEDIATE: Critical items processed instantly
  - BATCHED: Efficient batch processing with timeouts
  - SCHEDULED: Off-peak processing for low-priority items
  - PRIORITY: Queue-based priority processing

- **Data Source Watchers**: Custom rules per data source
- **Retry Management**: Automatic retry with exponential backoff

### 6. UI Integration

Datasette plugin (`datasette_enrichment_plugin.py`) provides:

- **Enhanced Views**: 
  - Theme overview with hierarchy visualization
  - Enrichment dashboard with statistics
  - Item enrichment details

- **Custom Rendering**:
  - Theme badges with colors
  - Confidence score visualizations
  - Enrichment content formatting

- **Interactive Features**:
  - On-demand enrichment
  - Batch enrichment UI
  - Theme-based filtering

## Implementation Guide

### Phase 1: Database Setup
1. Apply schema extensions to timeline.db
2. Load theme taxonomy
3. Insert prompt templates

### Phase 2: Core Pipeline
1. Implement LLM provider adapters (Claude, GPT-4, etc.)
2. Deploy enrichment processors
3. Set up job management system

### Phase 3: Quality & Monitoring
1. Configure validators
2. Set up human review workflows
3. Implement metrics collection

### Phase 4: UI Integration
1. Install Datasette plugin
2. Deploy custom templates
3. Configure facets and filters

### Phase 5: Incremental Processing
1. Configure processing rules
2. Start change detection
3. Monitor queue health

## Configuration

### Environment Variables
```bash
# LLM Configuration
LLM_PROVIDER=claude  # or openai, anthropic
LLM_API_KEY=your_api_key
LLM_MODEL=claude-3-opus-20240229

# Processing Configuration
ENRICHMENT_BATCH_SIZE=100
MAX_CONCURRENT_REQUESTS=5
RATE_LIMIT_RPM=60

# Quality Thresholds
MIN_CONFIDENCE_SCORE=0.6
HUMAN_REVIEW_THRESHOLD=0.7
```

### Processing Rules Example
```python
ProcessingRule(
    name="urgent_messages",
    condition="data_type LIKE '%message%' AND starred = 1",
    strategy=ProcessingStrategy.IMMEDIATE,
    priority=9,
    enrichment_types=["summary", "sentiment"]
)
```

## API Endpoints

### Enrichment Management
- `POST /timeline/enrich`: Trigger enrichment for specific items
- `GET /timeline/enrichment-status`: Check processing status
- `POST /timeline/batch-enrich`: Start batch enrichment job

### Theme Management
- `GET /timeline/themes`: List theme hierarchy
- `GET /timeline/themes/{id}/items`: Items in a theme
- `POST /timeline/themes/{id}/merge`: Merge themes

### Quality Control
- `GET /timeline/quality-reports`: View quality metrics
- `POST /timeline/review/{id}`: Submit human review
- `GET /timeline/quality-insights`: Analytics dashboard

## Performance Considerations

### Scalability
- Horizontal scaling via multiple pipeline workers
- Database indexing on frequently queried columns
- Caching layer for repeated enrichments

### Optimization
- Batch similar items for efficient prompting
- Use embedding similarity for deduplication
- Implement progressive enrichment (basic → detailed)

### Resource Management
- Monitor LLM token usage
- Implement cost controls
- Track processing time per enrichment type

## Security & Privacy

### Data Protection
- Sanitize personal information before LLM processing
- Store API keys securely (environment variables)
- Implement access controls for enrichment features

### Audit Trail
- Log all enrichment operations
- Track human review decisions
- Monitor for sensitive data exposure

## Future Enhancements

### Short Term
1. Multi-language support for themes
2. Custom theme creation UI
3. Export enrichments to various formats

### Medium Term
1. ML-based theme suggestion refinement
2. Automatic prompt optimization
3. Cross-item pattern detection

### Long Term
1. Personal AI assistant integration
2. Predictive enrichment based on patterns
3. Integration with external knowledge bases

## Monitoring & Maintenance

### Key Metrics
- Enrichment coverage (% items enriched)
- Average confidence scores by type
- Processing time percentiles
- Error rates and retry statistics

### Maintenance Tasks
- Regular theme taxonomy updates
- Prompt template optimization
- Quality threshold tuning
- Cache cleanup

## Support & Documentation

- Architecture diagrams: `/docs/enrichment-architecture/`
- API documentation: `/docs/api/enrichment/`
- Troubleshooting guide: `/docs/enrichment-troubleshooting.md`
- Example notebooks: `/examples/enrichment/`