#!/Users/nateaune/.pyenv/versions/3.12.8/bin/python
"""
Run Timelinize LLM Enrichment Pipeline - Working Implementation

This script includes actual LLM API implementations for OpenAI and Anthropic.
"""

import asyncio
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys

# Import the pipeline modules
from llm_pipeline_architecture import (
    PipelineConfig,
    EnrichmentPipeline,
    EnrichmentType,
    TimelineItem,
    EnrichmentResult,
    EnrichmentProcessor,
    LLMProvider
)

# Check for required packages
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Working LLM Provider Implementations
class OpenAIProvider(LLMProvider):
    """Working implementation using OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        if not HAS_OPENAI:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text from the LLM"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            raise
    
    async def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None) -> List[str]:
        """Generate text for multiple prompts efficiently"""
        # For simplicity, process sequentially (could be optimized with concurrent requests)
        results = []
        for prompt in prompts:
            result = await self.generate(prompt, system_prompt)
            results.append(result)
        return results

class ClaudeProvider(LLMProvider):
    """Working implementation using Claude API"""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text from Claude"""
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                system=system_prompt if system_prompt else "You are a helpful assistant.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Claude API error: {e}")
            raise
    
    async def batch_generate(self, prompts: List[str], system_prompt: Optional[str] = None) -> List[str]:
        """Generate text for multiple prompts efficiently"""
        results = []
        for prompt in prompts:
            result = await self.generate(prompt, system_prompt)
            results.append(result)
        return results

# Working Processor Implementations
class SummaryProcessor(EnrichmentProcessor):
    """Generates concise summaries of timeline items"""
    
    def get_prompt_template(self) -> str:
        return """Summarize the following timeline item in 1-2 sentences, focusing on the key information:

Content: {content}
Type: {data_type}
Date: {date}

Summary:"""
    
    async def process(self, item: TimelineItem, llm: LLMProvider) -> EnrichmentResult:
        """Process a single item"""
        from datetime import datetime
        
        # Prepare the prompt
        date_str = datetime.fromtimestamp(item.timestamp).strftime("%Y-%m-%d %H:%M") if item.timestamp else "Unknown"
        prompt = self.get_prompt_template().format(
            content=item.data_text[:1000] if item.data_text else "No content",
            data_type=item.data_type or "Unknown",
            date=date_str
        )
        
        # Generate summary
        start_time = datetime.now()
        try:
            summary = await llm.generate(
                prompt,
                "You are a helpful assistant that creates clear, informative summaries. Be concise but include key details."
            )
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return EnrichmentResult(
                item_id=item.id,
                enrichment_type=EnrichmentType.SUMMARY,
                content=summary.strip(),
                confidence_score=0.9,
                themes=[],
                processing_time_ms=processing_time,
                model_name=llm.__class__.__name__
            )
        except Exception as e:
            return EnrichmentResult(
                item_id=item.id,
                enrichment_type=EnrichmentType.SUMMARY,
                content="",
                confidence_score=0.0,
                themes=[],
                processing_time_ms=0,
                model_name=llm.__class__.__name__,
                error=str(e)
            )

class ThemeClassificationProcessor(EnrichmentProcessor):
    """Classifies items into hierarchical themes"""
    
    def __init__(self, theme_taxonomy: Dict[str, Any]):
        self.theme_taxonomy = theme_taxonomy
    
    def get_prompt_template(self) -> str:
        return """Classify the following timeline item into relevant themes. Return ONLY a JSON array with theme IDs and confidence scores.

Content: {content}
Type: {data_type}

Available Themes:
{theme_list}

Return format: [{"theme_id": <id>, "confidence": <0.0-1.0>}]

Classification:"""
    
    def _format_theme_list(self) -> str:
        """Format themes for the prompt"""
        lines = []
        for theme_id, theme in self.theme_taxonomy.items():
            keywords = ", ".join(theme.get('keywords', [])) if theme.get('keywords') else ""
            lines.append(f"- ID {theme_id}: {theme['name']} ({keywords})")
        return "\n".join(lines[:20])  # Limit to avoid token overflow
    
    async def process(self, item: TimelineItem, llm: LLMProvider) -> EnrichmentResult:
        """Process a single item"""
        from datetime import datetime
        import json
        
        # Prepare the prompt
        prompt = self.get_prompt_template().format(
            content=item.data_text[:1000] if item.data_text else "No content",
            data_type=item.data_type or "Unknown",
            theme_list=self._format_theme_list()
        )
        
        # Generate classification
        start_time = datetime.now()
        try:
            response = await llm.generate(
                prompt,
                "You are an expert at categorizing content into themes. Return only valid JSON."
            )
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Parse the response
            themes = []
            try:
                # Extract JSON from response (in case LLM added extra text)
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    classifications = json.loads(json_str)
                    
                    for cls in classifications:
                        if 'theme_id' in cls and 'confidence' in cls:
                            themes.append((int(cls['theme_id']), float(cls['confidence'])))
            except:
                pass  # If parsing fails, return empty themes
            
            return EnrichmentResult(
                item_id=item.id,
                enrichment_type=EnrichmentType.THEME_CLASSIFICATION,
                content=response,
                confidence_score=0.8 if themes else 0.0,
                themes=themes,
                processing_time_ms=processing_time,
                model_name=llm.__class__.__name__
            )
        except Exception as e:
            return EnrichmentResult(
                item_id=item.id,
                enrichment_type=EnrichmentType.THEME_CLASSIFICATION,
                content="",
                confidence_score=0.0,
                themes=[],
                processing_time_ms=0,
                model_name=llm.__class__.__name__,
                error=str(e)
            )

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
            max_concurrent_requests=3,  # Reduced for rate limiting
            retry_attempts=3,
            rate_limit_requests_per_minute=30,  # Conservative rate limit
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
            WHERE active = 1
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
            AND i.data_text IS NOT NULL
            AND length(i.data_text) > 10
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
            
            successful = [r for r in results if not r.error]
            failed = [r for r in results if r.error]
            
            print(f"Completed batch: {len(successful)} successful, {len(failed)} failed")
            
            if failed:
                for r in failed[:3]:  # Show first 3 errors
                    print(f"  Error on item {r.item_id}: {r.error}")
    
    def _store_results(self, results):
        """Store enrichment results in the database"""
        cursor = self.conn.cursor()
        
        for result in results:
            if result.error:
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
    
    # Check for API packages
    print("\n=== Checking Dependencies ===")
    if not HAS_OPENAI and not HAS_ANTHROPIC:
        print("❌ No LLM packages installed!")
        print("\nInstall one of:")
        print("  pip install openai      # For OpenAI")
        print("  pip install anthropic   # For Claude")
        return
    
    print(f"OpenAI support: {'✅' if HAS_OPENAI else '❌'}")
    print(f"Anthropic support: {'✅' if HAS_ANTHROPIC else '❌'}")
    
    # Determine which provider to use
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if openai_key and HAS_OPENAI:
        provider = "openai"
        print(f"\nUsing OpenAI API")
    elif anthropic_key and HAS_ANTHROPIC:
        provider = "claude"
        print(f"\nUsing Anthropic Claude API")
    else:
        print("\n❌ No API key found!")
        print("Set one of these environment variables:")
        print("  export OPENAI_API_KEY='your-key'")
        print("  export ANTHROPIC_API_KEY='your-key'")
        return
    
    # Initialize enrichment runner
    try:
        runner = EnrichmentRunner(db_path, llm_provider=provider)
    except Exception as e:
        print(f"\n❌ Error initializing: {e}")
        return
    
    # Show current statistics
    print("\n=== Current Enrichment Statistics ===")
    stats = runner.get_enrichment_stats()
    print(f"Total items: {stats['total_items']:,}")
    print(f"Enriched items: {stats['enriched_items']:,}")
    print(f"Progress: {stats['enriched_items']/stats['total_items']*100:.1f}%" if stats['total_items'] > 0 else "No items")
    print(f"\nEnrichments by type:")
    for etype, count in stats['by_type'].items():
        print(f"  - {etype}: {count:,}")
    if stats['top_themes']:
        print(f"\nTop themes:")
        for theme, count in stats['top_themes']:
            print(f"  - {theme}: {count:,}")
    
    # Get items to process
    print("\n=== Finding Items to Enrich ===")
    
    # Start with a small batch for testing
    items = runner.get_items_to_process(limit=10)  # Start small
    print(f"Found {len(items)} items to enrich")
    
    if not items:
        print("No items need enrichment!")
        return
    
    # Show sample item
    print("\nSample item:")
    sample = items[0]
    print(f"  Type: {sample.data_type}")
    print(f"  Text: {sample.data_text[:100]}..." if sample.data_text else "  No text")
    
    # Choose enrichment types to run
    enrichment_types = [
        EnrichmentType.SUMMARY,
        EnrichmentType.THEME_CLASSIFICATION,
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
    print(f"Rate: {len(items)/duration:.1f} items/second" if duration > 0 else "N/A")
    
    # Show updated statistics
    print("\n=== Updated Statistics ===")
    new_stats = runner.get_enrichment_stats()
    print(f"Enriched items: {new_stats['enriched_items']:,} (+{new_stats['enriched_items'] - stats['enriched_items']})")
    print(f"Progress: {new_stats['enriched_items']/new_stats['total_items']*100:.1f}%" if new_stats['total_items'] > 0 else "No items")
    
    # Show sample enrichments
    if new_stats['enriched_items'] > stats['enriched_items']:
        print("\n=== Sample Enrichments ===")
        cursor = runner.conn.cursor()
        cursor.execute("""
            SELECT i.data_text, ie.enrichment_type, ie.content
            FROM item_enrichments ie
            JOIN items i ON ie.item_id = i.id
            ORDER BY ie.generated DESC
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"\nOriginal: {row[0][:100]}...")
            print(f"Type: {row[1]}")
            print(f"Enrichment: {row[2][:200]}...")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())