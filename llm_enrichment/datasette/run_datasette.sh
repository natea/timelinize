#!/bin/bash
# Run datasette with enrichment plugins

# Create directories if they don't exist
mkdir -p ~/.datasette/plugins
mkdir -p ~/.datasette/static

# Copy enrichment CSS if available
if [ -f "enrichment-styles.css" ]; then
    cp enrichment-styles.css ~/.datasette/static/
    echo "✅ Copied enrichment styles"
fi

# Copy plugin - use simple version to avoid facet errors
if [ -f "datasette_enrichment_simple.py" ]; then
    cp datasette_enrichment_simple.py ~/.datasette/plugins/
    echo "✅ Copied enrichment plugin (simple version)"
elif [ -f "datasette_enrichment_plugin.py" ]; then
    cp datasette_enrichment_plugin.py ~/.datasette/plugins/
    echo "✅ Copied enrichment plugin"
fi

# Find an available port
PORT=8001
while lsof -i:$PORT >/dev/null 2>&1; do
    echo "Port $PORT is in use, trying next..."
    ((PORT++))
done

echo "🚀 Starting datasette on port $PORT"
echo "   URL: http://localhost:$PORT"
echo ""

# Run datasette with proper paths (expanding ~)
datasette ~/Documents/timelinize-data/timeline.db \
    --port $PORT \
    --plugins-dir $HOME/.datasette/plugins \
    --static static:$HOME/.datasette/static