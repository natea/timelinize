#!/Users/nateaune/.pyenv/versions/3.12.8/bin/python
"""
Debug enrichment pipeline issues
"""

import sqlite3
import os
from pathlib import Path
import asyncio

async def test_simple_enrichment():
    """Test basic enrichment functionality"""
    print("🔍 Debugging Enrichment Pipeline")
    print("=" * 40)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OPENAI_API_KEY found")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Test simple API call
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)
        
        print("\n📡 Testing API call...")
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'test' in one word"}],
            max_tokens=10
        )
        print(f"✅ API Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ API Error: {type(e).__name__}: {e}")
        return
    
    # Check database
    db_path = Path.home() / "Documents" / "timelinize-data" / "timeline.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get a sample item
    print("\n📊 Getting sample item...")
    cursor.execute("""
        SELECT i.id, i.data_text, i.data_type, i.timestamp
        FROM items i
        LEFT JOIN item_enrichments ie ON i.id = ie.item_id
        WHERE i.deleted IS NULL 
        AND i.data_text IS NOT NULL
        AND length(i.data_text) > 10
        AND ie.id IS NULL
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if not row:
        print("❌ No items found needing enrichment")
        return
    
    print(f"✅ Found item ID {row['id']}")
    print(f"   Type: {row['data_type']}")
    print(f"   Text: {row['data_text'][:100]}...")
    
    # Try to enrich manually
    print("\n🤖 Attempting manual enrichment...")
    
    try:
        # Create summary prompt
        prompt = f"Summarize this in 1-2 sentences: {row['data_text'][:500]}"
        
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        print(f"✅ Generated summary: {summary}")
        
        # Try to save it
        cursor.execute("""
            INSERT INTO item_enrichments 
            (item_id, enrichment_type, content, confidence_score, model_name)
            VALUES (?, ?, ?, ?, ?)
        """, (row['id'], 'summary', summary, 0.9, 'gpt-3.5-turbo'))
        
        conn.commit()
        print("✅ Saved enrichment to database!")
        
        # Verify it was saved
        cursor.execute("SELECT COUNT(*) FROM item_enrichments WHERE item_id = ?", (row['id'],))
        count = cursor.fetchone()[0]
        print(f"✅ Verified: {count} enrichment(s) for item {row['id']}")
        
    except Exception as e:
        print(f"❌ Error during enrichment: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    conn.close()

# Also test the pipeline components
async def test_pipeline_components():
    """Test individual pipeline components"""
    print("\n\n🔧 Testing Pipeline Components")
    print("=" * 40)
    
    from llm_pipeline_architecture import EnrichmentType
    
    # Test imports
    try:
        from run_enrichment_pipeline_working import (
            OpenAIProvider, 
            SummaryProcessor,
            TimelineItem
        )
        print("✅ Successfully imported pipeline components")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return
    
    # Test LLM provider
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        llm = OpenAIProvider(api_key)
        test_response = await llm.generate("Say hello", "You are helpful")
        print(f"✅ LLM Provider works: {test_response[:50]}")
    except Exception as e:
        print(f"❌ LLM Provider error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test processor
    try:
        processor = SummaryProcessor()
        
        # Create test item
        test_item = TimelineItem(
            id=1,
            data_text="This is a test message for debugging the enrichment pipeline.",
            data_type="text/plain",
            metadata={},
            timestamp=1700000000,
            classification_id=None
        )
        
        # Process it
        result = await processor.process(test_item, llm)
        
        if result.error:
            print(f"❌ Processor error: {result.error}")
        else:
            print(f"✅ Processor result: {result.content[:100]}")
            print(f"   Confidence: {result.confidence_score}")
    except Exception as e:
        print(f"❌ Processor error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_simple_enrichment()
    await test_pipeline_components()

if __name__ == "__main__":
    asyncio.run(main())