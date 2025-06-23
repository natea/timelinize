#!/usr/bin/env python3
"""
Run Timelinize LLM Enrichment Pipeline

This script demonstrates how to run the enrichment pipeline to process existing timeline items.
It can be used to enrich all items or specific subsets based on filters.
"""

import asyncio
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import the pipeline modules
from llm_pipeline_architecture import (
    PipelineConfig,
    EnrichmentPipeline,
    EnrichmentType,
    TimelineItem,
    SummaryProcessor,
    ThemeClassificationProcessor,
    LLMProvider
)

# Example LLM Provider Implementation
class OpenAIProvider(LLMProvider):
    """Example implementation using OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        # In production, initialize OpenAI client here
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text from the LLM"""
        # Placeholder - implement actual API call
        print(f"Generating with prompt length: {len(prompt)}")
        return "Generated content placeholder"
    
    async def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None) -> List[str]:
        """Generate text for multiple prompts efficiently"""
        # Placeholder - implement actual batch API calls
        return ["Generated content" for _ in prompts]

class ClaudeProvider(LLMProvider):
    """Example implementation using Claude API"""
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
        # In production, initialize Anthropic client here
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text from Claude"""
        # Placeholder - implement actual API call
        print(f"Generating with Claude, prompt length: {len(prompt)}")
        return "Claude generated content placeholder"
    
    async def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None) -> List[str]:
        """Generate text for multiple prompts efficiently"""
        return ["Claude generated content" for _ in prompts]

class EnrichmentRunner:
    """Main class to run the enrichment pipeline"""
    
    def __init__(self, db_path: Path, llm_provider: str = "openai"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Initialize LLM provider
        if llm_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.llm = OpenAIProvider(api_key)
        elif llm_provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self.llm = ClaudeProvider(api_key)
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")
        
        # Initialize pipeline with configuration
        self.config = PipelineConfig(
            batch_size=50,
            max_concurrent_requests=5,
            retry_attempts=3,
            rate_limit_requests_per_minute=60,
            temperature=0.3
        )
        self.pipeline = EnrichmentPipeline(self.config, self.llm)
        
        # Register processors
        self._register_processors()
    
    def _register_processors(self):
        """Register enrichment processors"""
        # Load theme taxonomy
        theme_taxonomy = self._load_theme_taxonomy()
        
        # Register processors
        self.pipeline.register_processor(
            EnrichmentType.SUMMARY,
            SummaryProcessor()
        )
        self.pipeline.register_processor(
            EnrichmentType.THEME_CLASSIFICATION,
            ThemeClassificationProcessor(theme_taxonomy)
        )
    
    def _load_theme_taxonomy(self) -> Dict[str, Any]:
        """Load theme taxonomy from database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, parent_id, name, description, keywords
            FROM themes
            ORDER BY level, name
        """)
        
        themes = {}
        for row in cursor.fetchall():
            themes[row['id']] = {
                'id': row['id'],
                'parent_id': row['parent_id'],
                'name': row['name'],
                'description': row['description'],
                'keywords': row['keywords'].split(',') if row['keywords'] else []
            }
        
        return themes
    
    def get_items_to_process(self, filter_query: Optional[str] = None, limit: int = 1000) -> List[TimelineItem]:
        """Get timeline items that need enrichment"""
        cursor = self.conn.cursor()
        
        # Base query to find items needing enrichment
        query = """
            SELECT DISTINCT
                i.id,
                i.data_text,
                i.data_type,
                i.timestamp,
                i.classification_id,
                i.longitude,
                i.latitude,
                i.metadata
            FROM items i
            LEFT JOIN item_enrichments ie ON i.id = ie.item_id
            WHERE i.deleted IS NULL
        """
        
        # Add custom filter if provided
        if filter_query:
            query += f" AND ({filter_query})"
        
        # Find items without enrichment or outdated enrichment
        query += """
            AND (
                ie.id IS NULL  -- No enrichment exists
                OR ie.generated < strftime('%s', 'now', '-30 days')  -- Enrichment is old
            )
            ORDER BY i.timestamp DESC
            LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        
        items = []
        for row in cursor.fetchall():
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
            
            # Add location to metadata if available
            if row['longitude'] and row['latitude']:
                metadata['location'] = {
                    'longitude': row['longitude'],
                    'latitude': row['latitude']
                }
            
            items.append(TimelineItem(
                id=row['id'],
                data_text=row['data_text'],
                data_type=row['data_type'],
                metadata=metadata,
                timestamp=row['timestamp'],
                classification_id=row['classification_id']
            ))
        
        return items
    
    async def enrich_items(self, items: List[TimelineItem], enrichment_types: List[EnrichmentType]):
        """Process items through the enrichment pipeline"""
        print(f"Starting enrichment of {len(items)} items...")
        
        # Process in batches
        for i in range(0, len(items), self.config.batch_size):
            batch = items[i:i + self.config.batch_size]
            print(f"Processing batch {i//self.config.batch_size + 1} ({len(batch)} items)...")
            
            # Run enrichment pipeline
            results = await self.pipeline.process_batch(batch, enrichment_types)
            
            # Store results in database
            self._store_results(results)
            
            print(f"Completed batch with {len(results)} successful enrichments")
    
    def _store_results(self, results):
        """Store enrichment results in the database"""
        cursor = self.conn.cursor()
        
        for result in results:
            if result.error:
                print(f"Error enriching item {result.item_id}: {result.error}")
                continue
            
            # Store enrichment content
            cursor.execute("""
                INSERT OR REPLACE INTO item_enrichments 
                (item_id, enrichment_type, content, confidence_score, model_name)
                VALUES (?, ?, ?, ?, ?)
            """, (
                result.item_id,
                result.enrichment_type.value,
                result.content,
                result.confidence_score,
                result.model_name
            ))
            
            # Store theme classifications
            if result.enrichment_type == EnrichmentType.THEME_CLASSIFICATION and result.themes:
                for theme_id, confidence in result.themes:
                    cursor.execute("""
                        INSERT OR REPLACE INTO item_themes
                        (item_id, theme_id, confidence_score, model_name)
                        VALUES (?, ?, ?, ?)
                    """, (result.item_id, theme_id, confidence, result.model_name))
            
            # Update enrichment status
            cursor.execute("""
                INSERT OR REPLACE INTO enrichment_status
                (item_id, last_enriched, enrichment_version, processing_time_ms)
                VALUES (?, ?, 1, ?)
            """, (result.item_id, int(datetime.now().timestamp()), result.processing_time_ms))
        
        self.conn.commit()
    
    def get_enrichment_stats(self) -> Dict[str, Any]:
        """Get statistics about enrichment progress"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total items
        cursor.execute("SELECT COUNT(*) FROM items WHERE deleted IS NULL")
        stats['total_items'] = cursor.fetchone()[0]
        
        # Enriched items
        cursor.execute("SELECT COUNT(DISTINCT item_id) FROM item_enrichments")
        stats['enriched_items'] = cursor.fetchone()[0]
        
        # By enrichment type
        cursor.execute("""
            SELECT enrichment_type, COUNT(DISTINCT item_id) as count
            FROM item_enrichments
            GROUP BY enrichment_type
        """)
        stats['by_type'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Theme distribution
        cursor.execute("""
            SELECT t.name, COUNT(it.item_id) as count
            FROM themes t
            JOIN item_themes it ON t.id = it.theme_id
            WHERE t.parent_id IS NULL
            GROUP BY t.id
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_themes'] = [(row[0], row[1]) for row in cursor.fetchall()]
        
        # Recent enrichments
        cursor.execute("""
            SELECT COUNT(*) 
            FROM enrichment_status
            WHERE last_enriched > strftime('%s', 'now', '-1 day')
        """)
        stats['enriched_last_24h'] = cursor.fetchone()[0]
        
        return stats

async def main():
    """Main function to run the enrichment pipeline"""
    
    # Configuration
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    
    # Check if database exists
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return
    
    # Initialize enrichment runner
    # Change to "claude" to use Claude instead of OpenAI
    runner = EnrichmentRunner(db_path, llm_provider="openai")
    
    # Show current statistics
    print("\n=== Current Enrichment Statistics ===")
    stats = runner.get_enrichment_stats()
    print(f"Total items: {stats['total_items']:,}")
    print(f"Enriched items: {stats['enriched_items']:,}")
    print(f"Progress: {stats['enriched_items']/stats['total_items']*100:.1f}%")
    print(f"\nEnrichments by type:")
    for etype, count in stats['by_type'].items():
        print(f"  - {etype}: {count:,}")
    print(f"\nTop themes:")
    for theme, count in stats['top_themes']:
        print(f"  - {theme}: {count:,}")
    
    # Get items to process
    print("\n=== Finding Items to Enrich ===")
    
    # Example filters (uncomment to use):
    # filter_query = "data_type LIKE '%message%'"  # Only messages
    # filter_query = "timestamp > strftime('%s', 'now', '-7 days')"  # Last week only
    # filter_query = "data_source_id = 1"  # Specific data source
    filter_query = None  # Process all items
    
    items = runner.get_items_to_process(filter_query, limit=100)
    print(f"Found {len(items)} items to enrich")
    
    if not items:
        print("No items need enrichment!")
        return
    
    # Choose enrichment types to run
    enrichment_types = [
        EnrichmentType.SUMMARY,
        EnrichmentType.THEME_CLASSIFICATION,
        # EnrichmentType.SENTIMENT_ANALYSIS,  # Add if processor is implemented
        # EnrichmentType.ENTITY_EXTRACTION,   # Add if processor is implemented
    ]
    
    # Confirm before processing
    response = input(f"\nProcess {len(items)} items with {len(enrichment_types)} enrichment types? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Run enrichment
    start_time = datetime.now()
    await runner.enrich_items(items, enrichment_types)
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"\n=== Enrichment Complete ===")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Rate: {len(items)/duration:.1f} items/second")
    
    # Show updated statistics
    print("\n=== Updated Statistics ===")
    new_stats = runner.get_enrichment_stats()
    print(f"Enriched items: {new_stats['enriched_items']:,} (+{new_stats['enriched_items'] - stats['enriched_items']})")
    print(f"Progress: {new_stats['enriched_items']/new_stats['total_items']*100:.1f}%")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())