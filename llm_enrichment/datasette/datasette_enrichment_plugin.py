"""
Datasette Plugin for Timelinize LLM Enrichments

This plugin extends Datasette to provide enhanced UI for viewing and filtering
timeline items with LLM-generated enrichments and themes.
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
def extra_js_urls(datasette):
    """Add custom JavaScript for interactive features"""
    return [
        "/-/static-plugins/timelinize-enrichments/enrichment-ui.js"
    ]


@hookimpl
def register_routes():
    """Register custom routes for enrichment features"""
    return [
        (r"^/timeline/themes/?$", themes_overview),
        (r"^/timeline/enrichment-dashboard/?$", enrichment_dashboard),
        (r"^/timeline/item/(?P<item_id>\d+)/enrich/?$", enrich_item),
        (r"^/timeline/batch-enrich/?$", batch_enrich_ui),
    ]


@hookimpl
def table_actions(datasette, actor, database, table):
    """Add enrichment actions to table views"""
    if database == "timeline" and table == "items":
        return [
            {
                "href": datasette.urls.path("/-/timeline/batch-enrich"),
                "label": "Enrich with LLM",
                "description": "Generate summaries and themes for selected items",
            }
        ]


@hookimpl
def render_cell(value, column, table, database, datasette):
    """Custom rendering for enrichment-related columns"""
    if database != "timeline":
        return None
    
    if table == "items_with_themes" and column == "theme_names":
        # Render themes as colored badges
        if value:
            themes = value.split(", ")
            badges = []
            for theme in themes:
                badge = f'<span class="theme-badge">{escape(theme)}</span>'
                badges.append(badge)
            return Markup(" ".join(badges))
    
    elif table == "item_enrichments" and column == "content":
        # Render enrichment content with formatting
        return Markup(f'<div class="enrichment-content">{escape(value)}</div>')
    
    elif column == "confidence_score":
        # Render confidence as a visual indicator
        if value is not None:
            percentage = int(value * 100)
            color = "green" if value > 0.8 else "orange" if value > 0.6 else "red"
            return Markup(
                f'<div class="confidence-bar" style="background: linear-gradient(to right, {color} {percentage}%, #eee {percentage}%);">'
                f'{percentage}%</div>'
            )
    
    return None


@hookimpl
def extra_template_vars(template, database, table, view_name, datasette):
    """Add enrichment statistics to template context"""
    if database == "timeline":
        return {
            "enrichment_stats": get_enrichment_stats(datasette),
            "available_themes": get_theme_hierarchy(datasette),
        }
    return {}


# Route handlers
async def themes_overview(request, datasette):
    """Display hierarchical theme overview with statistics"""
    db = datasette.get_database("timeline")
    
    # Get theme hierarchy with counts
    themes_query = """
    WITH theme_counts AS (
        SELECT theme_id, COUNT(*) as item_count, AVG(confidence_score) as avg_confidence
        FROM item_themes
        GROUP BY theme_id
    )
    SELECT 
        t.*,
        COALESCE(tc.item_count, 0) as item_count,
        COALESCE(tc.avg_confidence, 0) as avg_confidence,
        (
            SELECT GROUP_CONCAT(t2.name, ' > ')
            FROM themes t2
            WHERE t2.id IN (
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id FROM themes WHERE id = t.id
                    UNION ALL
                    SELECT t3.id, t3.parent_id FROM themes t3
                    JOIN ancestors a ON t3.id = a.parent_id
                )
                SELECT id FROM ancestors WHERE id != t.id
            )
        ) as breadcrumb
    FROM themes t
    LEFT JOIN theme_counts tc ON t.id = tc.theme_id
    ORDER BY t.level, t.parent_id, t.name
    """
    
    themes = await db.execute(themes_query)
    
    return await datasette.render_template(
        "timeline_themes.html",
        {
            "themes": themes.rows,
            "database": "timeline",
        }
    )


async def enrichment_dashboard(request, datasette):
    """Dashboard showing enrichment progress and statistics"""
    db = datasette.get_database("timeline")
    
    stats = {
        "total_items": await db.execute_returning_dicts(
            "SELECT COUNT(*) as count FROM items"
        ),
        "enriched_items": await db.execute_returning_dicts(
            "SELECT COUNT(DISTINCT item_id) as count FROM item_enrichments"
        ),
        "total_themes": await db.execute_returning_dicts(
            "SELECT COUNT(*) as count FROM themes"
        ),
        "recent_jobs": await db.execute_returning_dicts(
            """
            SELECT * FROM enrichment_jobs 
            ORDER BY created DESC 
            LIMIT 10
            """
        ),
        "enrichment_coverage": await db.execute_returning_dicts(
            """
            SELECT 
                enrichment_type,
                COUNT(DISTINCT item_id) as items_enriched,
                AVG(confidence_score) as avg_confidence,
                AVG(processing_time_ms) as avg_processing_time
            FROM item_enrichments
            GROUP BY enrichment_type
            """
        ),
    }
    
    return await datasette.render_template(
        "enrichment_dashboard.html",
        {
            "stats": stats,
            "database": "timeline",
        }
    )


async def enrich_item(request, datasette, item_id):
    """Enrich a single item on demand"""
    if request.method == "POST":
        # Trigger enrichment for this item
        # This would integrate with the LLM pipeline
        pass
    
    # Show enrichment form/status
    db = datasette.get_database("timeline")
    item = await db.execute_returning_dicts(
        "SELECT * FROM items WHERE id = ?", [item_id]
    )
    enrichments = await db.execute_returning_dicts(
        "SELECT * FROM item_enrichments WHERE item_id = ?", [item_id]
    )
    
    return await datasette.render_template(
        "enrich_item.html",
        {
            "item": item[0] if item else None,
            "enrichments": enrichments,
            "database": "timeline",
        }
    )


async def batch_enrich_ui(request, datasette):
    """UI for batch enrichment jobs"""
    if request.method == "POST":
        # Create new enrichment job
        form_data = await request.post_vars()
        # Validate and create job...
        pass
    
    # Show batch enrichment interface
    return await datasette.render_template(
        "batch_enrich.html",
        {
            "database": "timeline",
            "enrichment_types": [
                "summary", "theme_classification", "sentiment",
                "entity_extraction", "relationship_discovery"
            ],
        }
    )


# Helper functions
def get_enrichment_stats(datasette):
    """Get summary statistics for enrichments"""
    # Implementation would query the database
    return {
        "total_enrichments": 0,
        "enrichment_types": {},
        "processing_time_avg": 0,
    }


def get_theme_hierarchy(datasette):
    """Get theme hierarchy for display"""
    # Implementation would build tree structure
    return []


# Custom SQL functions for Datasette
@hookimpl
def prepare_connection(conn):
    """Add custom SQL functions for enrichment queries"""
    
    def theme_path(theme_id):
        """Get full path for a theme"""
        # Would implement recursive query
        return f"path/to/theme/{theme_id}"
    
    def enrichment_score(item_id):
        """Calculate overall enrichment score for an item"""
        # Would calculate based on enrichments present
        return 0.0
    
    conn.create_function("theme_path", 1, theme_path)
    conn.create_function("enrichment_score", 1, enrichment_score)


# Facet customization
@hookimpl
def register_facet_classes():
    """Register custom facets for enrichment data"""
    return [ThemeFacet, ConfidenceFacet, EnrichmentTypeFacet]


class ThemeFacet:
    """Facet for filtering by themes"""
    
    def __init__(self, datasette):
        self.datasette = datasette
    
    async def facet_results(self, database, table, sql, params):
        # Implementation for theme-based faceting
        pass


class ConfidenceFacet:
    """Facet for filtering by confidence levels"""
    
    def __init__(self, datasette):
        self.datasette = datasette
    
    async def facet_results(self, database, table, sql, params):
        # Implementation for confidence-based faceting
        pass


class EnrichmentTypeFacet:
    """Facet for filtering by enrichment types"""
    
    def __init__(self, datasette):
        self.datasette = datasette
    
    async def facet_results(self, database, table, sql, params):
        # Implementation for enrichment type faceting
        pass