"""
Datasette Plugin for Timelinize Enrichments - Compatible with v0.65.1
"""

from datasette import hookimpl
import json
from markupsafe import Markup, escape


@hookimpl
def extra_css_urls(datasette):
    """Add custom CSS for enrichment UI"""
    return []


@hookimpl
def prepare_connection(conn):
    """Add custom SQL functions"""
    
    def theme_count(item_id):
        """Count themes for an item"""
        cursor = conn.execute(
            "SELECT COUNT(*) FROM item_themes WHERE item_id = ?", 
            (item_id,)
        )
        return cursor.fetchone()[0]
    
    conn.create_function("theme_count", 1, theme_count)


@hookimpl
def render_cell(value, column, table, database, datasette):
    """Custom rendering for enrichment columns"""
    if database != "timeline":
        return None
    
    # Simple theme display
    if column == "theme_names" and value:
        themes = value.split(", ")
        badges = []
        for theme in themes:
            badge = f'<span style="background:#e0e0e0;padding:2px 8px;margin:2px;border-radius:4px;display:inline-block">{escape(theme)}</span>'
            badges.append(badge)
        return Markup(" ".join(badges))
    
    # Confidence score as percentage
    elif column == "confidence_score" and value is not None:
        percentage = int(value * 100)
        color = "green" if value > 0.8 else "orange" if value > 0.6 else "red"
        return Markup(
            f'<div style="background:#eee;border-radius:4px;padding:2px 8px;color:{color}">{percentage}%</div>'
        )
    
    return None


@hookimpl
def table_actions(datasette, actor, database, table):
    """Add enrichment actions to tables"""
    actions = []
    
    if database == "timeline" and table == "items":
        actions.append({
            "href": datasette.urls.database(database) + "/themes",
            "label": "View Themes",
            "description": "Browse theme hierarchy"
        })
    
    return actions


@hookimpl
def register_routes():
    """Register simple routes"""
    return [
        (r"^/-/enrichment-info$", enrichment_info),
    ]


async def enrichment_info(datasette, request):
    """Show enrichment information"""
    db = datasette.get_database("timeline")
    
    # Get basic stats
    total_items = (await db.execute("SELECT COUNT(*) as c FROM items")).rows[0]["c"]
    enriched_items = (await db.execute("SELECT COUNT(DISTINCT item_id) as c FROM item_enrichments")).rows[0]["c"] 
    total_themes = (await db.execute("SELECT COUNT(*) as c FROM themes")).rows[0]["c"]
    
    html = f"""
    <html>
    <head><title>Enrichment Info</title></head>
    <body style="font-family:sans-serif;padding:20px">
        <h1>Timelinize Enrichment Status</h1>
        <ul>
            <li>Total items: {total_items:,}</li>
            <li>Enriched items: {enriched_items:,}</li>
            <li>Total themes: {total_themes}</li>
            <li>Coverage: {enriched_items/total_items*100:.1f}%</li>
        </ul>
        <h2>Quick Links</h2>
        <ul>
            <li><a href="/timeline/themes">Browse Themes</a></li>
            <li><a href="/timeline/items_with_themes">Items with Themes</a></li>
            <li><a href="/timeline/enrichment_prompts">Prompt Templates</a></li>
        </ul>
    </body>
    </html>
    """
    
    return Response(html, content_type="text/html")


# Simple Response class for compatibility
class Response:
    def __init__(self, body, content_type="text/html", status=200):
        self.body = body
        self.content_type = content_type 
        self.status = status