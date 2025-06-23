# ❗ SOLUTION: API Key Not Set

## The Problem
The enrichment pipeline wasn't working because the `OPENAI_API_KEY` environment variable wasn't set in your terminal session.

## Quick Fix

### Step 1: Set Your API Key
Run this command in your terminal (replace with your actual key):

```bash
export OPENAI_API_KEY='sk-...'
```

**Important**: This must be done in the SAME terminal where you run the enrichment!

### Step 2: Test It's Working
```bash
./debug_enrichment.py
```

You should see:
- ✅ API Key found
- ✅ API Response: test
- ✅ Generated summary

### Step 3: Run Enrichment
```bash
./run_enrichment.sh
```

## Permanent Fix

Add the export command to your shell config file:

```bash
# For zsh (default on macOS):
echo "export OPENAI_API_KEY='sk-...'" >> ~/.zshrc
source ~/.zshrc

# For bash:
echo "export OPENAI_API_KEY='sk-...'" >> ~/.bashrc
source ~/.bashrc
```

## Alternative: Use the Setup Helper

```bash
./set_api_key.sh
```

This will guide you through setting up your API key.

## Why This Happened

1. Environment variables are session-specific
2. If you set `export OPENAI_API_KEY` in one terminal, it won't be available in another
3. The pipeline was running but couldn't make API calls without the key

## Verify Everything Works

```bash
# Check key is set
echo $OPENAI_API_KEY

# Test API connection
./test_llm_api.py

# Debug enrichment
./debug_enrichment.py

# Run enrichment
./run_enrichment.sh
```

## View Results

After enrichment works:

```bash
# Check enrichment count
sqlite3 ~/Documents/timelinize-data/timeline.db "SELECT COUNT(*) FROM item_enrichments"

# View with Datasette
datasette ~/Documents/timelinize-data/timeline.db
```