#!/Users/nateaune/.pyenv/versions/3.12.8/bin/python
"""
Test enrichment with API key provided as argument
"""

import sys
import os
import asyncio

async def test_with_key(api_key):
    """Test enrichment with provided API key"""
    # Set the environment variable
    os.environ['OPENAI_API_KEY'] = api_key
    
    print(f"✅ Set API key: {api_key[:10]}...")
    
    # Import and run the debug script
    from debug_enrichment import test_simple_enrichment, test_pipeline_components
    
    await test_simple_enrichment()
    await test_pipeline_components()

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_enrichment_with_key.py YOUR_API_KEY")
        print("\nExample:")
        print("  python test_enrichment_with_key.py sk-...")
        return
    
    api_key = sys.argv[1]
    
    if not api_key.startswith(('sk-', 'sk-ant-')):
        print("⚠️  Warning: API key doesn't start with expected prefix")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    asyncio.run(test_with_key(api_key))

if __name__ == "__main__":
    main()