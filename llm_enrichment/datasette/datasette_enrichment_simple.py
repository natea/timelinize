"""
Simple Datasette Plugin for Timelinize Enrichments

This is a simplified version that avoids complex facets to prevent compatibility issues.
"""

from datasette import hookimpl
import json
from markupsafe import Markup, escape


@hookimpl
def extra_css_urls(datasette):
    """Add custom CSS for enrichment UI"""
    return [
        "/-/static-plugins/timelinize-enrichments/enrichment-styles.css"
    ]


@hookimpl
def render_cell(value, column, table, database, datasette):
    """Custom rendering for enrichment-related columns"""
    if database != "timeline":
        return None
    
    # Render theme badges
    if column == "themes" and value:
        try:
            themes = json.loads(value) if isinstance(value, str) else value
            if isinstance(themes, list):
                badges = []
                for theme in themes:
                    if isinstance(theme, dict):
                        name = theme.get('name', 'Unknown')
                        confidence = theme.get('confidence', 0)
                        color = theme.get('color', '#6B7280')
                        badge = f'<span class="theme-badge" style="background-color: {color}">{escape(name)} ({confidence:.0%})</span>'
                        badges.append(badge)
                return Markup(' '.join(badges))
        except:
            pass
    
    # Render enrichment content with formatting
    if column in ["summary", "enrichment_content"] and value:
        return Markup(f'<div class="enrichment-content">{escape(value)}</div>')
    
    # Render confidence scores as progress bars
    if column == "confidence_score" and value is not None:
        try:
            score = float(value)
            color = "#10B981" if score > 0.8 else "#F59E0B" if score > 0.6 else "#EF4444"
            return Markup(
                f'<div class="confidence-bar" style="background: linear-gradient(to right, {color} {score*100}%, #E5E7EB {score*100}%);">'
                f'{score:.0%}</div>'
            )
        except:
            pass
    
    return None


@hookimpl
def table_actions(datasette, actor, database, table):
    """Add enrichment actions to table views"""
    if database == "timeline" and table == "items":
        return [
            {
                "href": "/timeline/enrichment_dashboard",
                "label": "📊 Enrichment Dashboard",
                "description": "View enrichment statistics and progress",
            }
        ]
    return []


@hookimpl
def register_routes():
    """Register simple dashboard route"""
    return [
        (r"^/timeline/enrichment_dashboard/?$", enrichment_dashboard),
    ]


async def enrichment_dashboard(request):
    """Simple enrichment dashboard"""
    datasette = request.app.ds
    db = datasette.get_database("timeline")
    
    # Get statistics
    stats = {}
    
    # Total items
    result = await db.execute("SELECT COUNT(*) FROM items WHERE deleted IS NULL")
    stats['total_items'] = result.rows[0][0]
    
    # Enriched items
    result = await db.execute("SELECT COUNT(DISTINCT item_id) FROM item_enrichments")
    stats['enriched_items'] = result.rows[0][0]
    
    # By type
    result = await db.execute("""
        SELECT enrichment_type, COUNT(DISTINCT item_id) as count
        FROM item_enrichments
        GROUP BY enrichment_type
        ORDER BY count DESC
    """)
    stats['by_type'] = [{'type': row[0], 'count': row[1]} for row in result.rows]
    
    # Top themes
    result = await db.execute("""
        SELECT t.name, t.color, COUNT(it.item_id) as count
        FROM themes t
        JOIN item_themes it ON t.id = it.theme_id
        GROUP BY t.id
        ORDER BY count DESC
        LIMIT 20
    """)
    stats['top_themes'] = [{'name': row[0], 'color': row[1], 'count': row[2]} for row in result.rows]
    
    # Recent enrichments
    result = await db.execute("""
        SELECT 
            i.id,
            substr(i.data_text, 1, 100) as preview,
            ie.enrichment_type,
            substr(ie.content, 1, 200) as enrichment,
            datetime(ie.generated, 'unixepoch') as enriched_at
        FROM item_enrichments ie
        JOIN items i ON ie.item_id = i.id
        ORDER BY ie.generated DESC
        LIMIT 10
    """)
    stats['recent'] = []
    for row in result.rows:
        stats['recent'].append({
            'id': row[0],
            'preview': row[1],
            'type': row[2],
            'enrichment': row[3],
            'enriched_at': row[4]
        })
    
    # Progress
    if stats['total_items'] > 0:
        stats['progress'] = round(stats['enriched_items'] / stats['total_items'] * 100, 1)
    else:
        stats['progress'] = 0
    
    # HTML response
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enrichment Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .stat-card {{ background: #f3f4f6; padding: 20px; border-radius: 8px; }}
            .stat-value {{ font-size: 2em; font-weight: bold; color: #1f2937; }}
            .stat-label {{ color: #6b7280; margin-top: 5px; }}
            .progress-bar {{ background: #e5e7eb; height: 30px; border-radius: 15px; overflow: hidden; margin: 20px 0; }}
            .progress-fill {{ background: #10b981; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }}
            .theme-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; color: white; font-size: 0.875em; margin: 2px; }}
            .section {{ margin: 30px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #e5e7eb; }}
            th {{ background: #f9fafb; font-weight: 600; }}
            .recent-item {{ background: #f9fafb; padding: 15px; margin: 10px 0; border-radius: 8px; }}
            .preview {{ color: #6b7280; font-size: 0.9em; }}
            .enrichment {{ color: #1f2937; margin-top: 8px; }}
            .meta {{ color: #9ca3af; font-size: 0.8em; margin-top: 5px; }}
        </style>
    </head>
    <body>
        <h1>📊 Enrichment Dashboard</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total_items']:,}</div>
                <div class="stat-label">Total Items</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['enriched_items']:,}</div>
                <div class="stat-label">Enriched Items</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['progress']}%</div>
                <div class="stat-label">Progress</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {stats['progress']}%">{stats['progress']}%</div>
        </div>
        
        <div class="section">
            <h2>Enrichments by Type</h2>
            <table>
                <tr><th>Type</th><th>Count</th></tr>
                {''.join(f'<tr><td>{t["type"]}</td><td>{t["count"]:,}</td></tr>' for t in stats['by_type'])}
            </table>
        </div>
        
        <div class="section">
            <h2>Top Themes</h2>
            <div>
                {''.join(f'<span class="theme-badge" style="background-color: {t["color"] or "#6b7280"}">{escape(t["name"])} ({t["count"]})</span>' for t in stats['top_themes'])}
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Enrichments</h2>
            {''.join(f'''
                <div class="recent-item">
                    <div class="preview">{escape(item["preview"] or "")}...</div>
                    <div class="enrichment"><strong>{item["type"]}:</strong> {escape(item["enrichment"] or "")}</div>
                    <div class="meta">Item #{item["id"]} • {item["enriched_at"]}</div>
                </div>
            ''' for item in stats['recent'])}
        </div>
        
        <div class="section">
            <p><a href="/timeline/items">← Back to Items</a></p>
        </div>
    </body>
    </html>
    """
    
    return request.scope["asgi"]["response"](
        200,
        {"content-type": "text/html; charset=utf-8"},
        html
    )