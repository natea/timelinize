#!/bin/bash
# Convenience script to run enrichment with the correct Python version

PYTHON_BIN="/Users/nateaune/.pyenv/versions/3.12.8/bin/python"

# Check for API keys
if [[ -z "$OPENAI_API_KEY" && -z "$ANTHROPIC_API_KEY" ]]; then
    echo "❌ Error: No API key found!"
    echo ""
    echo "To fix this issue:"
    echo ""
    echo "1. Run the setup helper:"
    echo "   ./set_api_key.sh"
    echo ""
    echo "2. Or set manually:"
    echo "   export OPENAI_API_KEY='your-openai-key'"
    echo "   export ANTHROPIC_API_KEY='your-anthropic-key'"
    echo ""
    echo "3. Get your API key from:"
    echo "   OpenAI: https://platform.openai.com/api-keys"
    echo "   Anthropic: https://console.anthropic.com/settings/keys"
    echo ""
    echo "Note: The key must be exported in the SAME terminal session"
    echo "where you run this script!"
    exit 1
fi

# Run the enrichment pipeline
echo "🚀 Starting enrichment pipeline..."
$PYTHON_BIN run_enrichment_pipeline_working.py