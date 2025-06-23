# 🚀 Timelinize Enrichment Quick Start

## Step 1: Set Your API Key

Choose one provider and set the API key:

### Option A: OpenAI (Recommended for beginners)
```bash
export OPENAI_API_KEY='sk-...'
```
Get your key at: https://platform.openai.com/api-keys

### Option B: Anthropic Claude
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```
Get your key at: https://console.anthropic.com/settings/keys

## Step 2: Run the Enrichment

```bash
# Easy way - use the convenience script
./run_enrichment.sh

# Or run directly with the correct Python
/Users/nateaune/.pyenv/versions/3.12.8/bin/python run_enrichment_pipeline_working.py
```

## Troubleshooting

### "Package not installed" Error
You have multiple Python versions. Use the full path:
```bash
/Users/nateaune/.pyenv/versions/3.12.8/bin/python <script.py>
```

### Test Your Setup
```bash
# Test API connectivity
/Users/nateaune/.pyenv/versions/3.12.8/bin/python test_llm_api.py

# Check enrichment status
./enrich_quick_start.py
```

### View Results
```bash
# With datasette
datasette ~/Documents/timelinize-data/timeline.db

# Or with SQL
sqlite3 ~/Documents/timelinize-data/timeline.db "SELECT COUNT(*) FROM item_enrichments"
```

## Cost Estimates

- **OpenAI GPT-3.5**: ~$0.001 per item
- **OpenAI GPT-4**: ~$0.01 per item  
- **Claude Sonnet**: ~$0.003 per item

Start with 10-100 items to test!

## Next Steps

1. Start small (10 items)
2. Check quality of enrichments
3. Adjust prompts if needed
4. Process more items in batches
5. Set up automated processing