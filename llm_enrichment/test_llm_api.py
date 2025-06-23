#!/Users/nateaune/.pyenv/versions/3.12.8/bin/python
"""
Test LLM API connectivity
"""

import os
import asyncio

async def test_openai():
    """Test OpenAI API"""
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OpenAI: No API key found")
            return False
        
        client = openai.AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello' in one word"}],
            max_tokens=10
        )
        print(f"✅ OpenAI: Connected! Response: {response.choices[0].message.content}")
        return True
    except ImportError:
        print("❌ OpenAI: Package not installed (pip install openai)")
        return False
    except Exception as e:
        print(f"❌ OpenAI: API error: {e}")
        return False

async def test_anthropic():
    """Test Anthropic API"""
    try:
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ Anthropic: No API key found")
            return False
        
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'Hello' in one word"}]
        )
        print(f"✅ Anthropic: Connected! Response: {message.content[0].text}")
        return True
    except ImportError:
        print("❌ Anthropic: Package not installed (pip install anthropic)")
        return False
    except Exception as e:
        print(f"❌ Anthropic: API error: {e}")
        return False

async def main():
    print("🧪 Testing LLM API Connectivity")
    print("=" * 40)
    
    openai_ok = await test_openai()
    anthropic_ok = await test_anthropic()
    
    print("\n" + "=" * 40)
    if openai_ok or anthropic_ok:
        print("✅ At least one API is working!")
        print("\nYou can now run:")
        print("  python3 run_enrichment_pipeline_working.py")
    else:
        print("❌ No working APIs found")
        print("\nTo fix:")
        print("1. Install packages:")
        print("   pip install openai anthropic")
        print("2. Set API key:")
        print("   export OPENAI_API_KEY='your-key'")
        print("   # OR")
        print("   export ANTHROPIC_API_KEY='your-key'")

if __name__ == "__main__":
    asyncio.run(main())