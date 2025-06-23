#!/bin/bash
# Helper script to set and verify API key

echo "🔑 Timelinize Enrichment API Key Setup"
echo "====================================="
echo ""

# Check current status
if [[ -n "$OPENAI_API_KEY" ]]; then
    echo "✅ OpenAI API key is set: ${OPENAI_API_KEY:0:10}..."
elif [[ -n "$ANTHROPIC_API_KEY" ]]; then
    echo "✅ Anthropic API key is set: ${ANTHROPIC_API_KEY:0:10}..."
else
    echo "❌ No API key is currently set"
fi

echo ""
echo "Choose your provider:"
echo "1) OpenAI (GPT-3.5/GPT-4)"
echo "2) Anthropic (Claude)"
echo "3) Exit"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Get your OpenAI API key from: https://platform.openai.com/api-keys"
        echo "It should start with 'sk-'"
        echo ""
        read -p "Enter your OpenAI API key: " api_key
        if [[ -n "$api_key" ]]; then
            echo ""
            echo "Add this to your ~/.bashrc or ~/.zshrc file:"
            echo ""
            echo "export OPENAI_API_KEY='$api_key'"
            echo ""
            echo "Or run this command now (temporary - only for this session):"
            echo ""
            echo "export OPENAI_API_KEY='$api_key'"
            echo ""
            echo "Then run: ./run_enrichment.sh"
        fi
        ;;
    2)
        echo ""
        echo "Get your Anthropic API key from: https://console.anthropic.com/settings/keys"
        echo "It should start with 'sk-ant-'"
        echo ""
        read -p "Enter your Anthropic API key: " api_key
        if [[ -n "$api_key" ]]; then
            echo ""
            echo "Add this to your ~/.bashrc or ~/.zshrc file:"
            echo ""
            echo "export ANTHROPIC_API_KEY='$api_key'"
            echo ""
            echo "Or run this command now (temporary - only for this session):"
            echo ""
            echo "export ANTHROPIC_API_KEY='$api_key'"
            echo ""
            echo "Then run: ./run_enrichment.sh"
        fi
        ;;
    3)
        echo "Exiting..."
        ;;
    *)
        echo "Invalid choice"
        ;;
esac