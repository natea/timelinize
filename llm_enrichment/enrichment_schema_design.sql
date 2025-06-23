-- Timelinize LLM Enrichment Schema Design
-- This schema extends the existing timeline.db with LLM-generated enrichments

-- Table for storing LLM-generated enrichments for items
CREATE TABLE IF NOT EXISTS "item_enrichments" (
    "id" INTEGER PRIMARY KEY,
    "item_id" INTEGER NOT NULL,
    "enrichment_type" TEXT NOT NULL, -- 'summary', 'insight', 'context', 'sentiment', 'entity_extraction'
    "content" TEXT NOT NULL, -- The actual enrichment content
    "confidence_score" REAL, -- 0.0 to 1.0 confidence in the enrichment
    "model_name" TEXT NOT NULL, -- e.g., 'claude-3-opus', 'gpt-4', etc.
    "model_version" TEXT,
    "prompt_template_id" INTEGER, -- Reference to the prompt used
    "processing_time_ms" INTEGER, -- Time taken to generate this enrichment
    "generated" INTEGER NOT NULL DEFAULT (unixepoch()),
    "metadata" TEXT, -- JSON for additional metadata
    FOREIGN KEY ("item_id") REFERENCES "items"("id") ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY ("prompt_template_id") REFERENCES "enrichment_prompts"("id") ON UPDATE CASCADE
) STRICT;

-- Table for hierarchical theme taxonomy
CREATE TABLE IF NOT EXISTS "themes" (
    "id" INTEGER PRIMARY KEY,
    "parent_id" INTEGER, -- For hierarchical themes
    "name" TEXT NOT NULL,
    "description" TEXT,
    "level" INTEGER NOT NULL DEFAULT 0, -- 0=root, 1=category, 2=subcategory, etc.
    "color" TEXT, -- For UI display
    "icon" TEXT, -- Icon identifier for UI
    "keywords" TEXT, -- Comma-separated keywords to help with classification
    "active" INTEGER NOT NULL DEFAULT 1,
    "created" INTEGER NOT NULL DEFAULT (unixepoch()),
    FOREIGN KEY ("parent_id") REFERENCES "themes"("id") ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE("parent_id", "name")
) STRICT;

-- Table for LLM-generated theme assignments
CREATE TABLE IF NOT EXISTS "item_themes" (
    "id" INTEGER PRIMARY KEY,
    "item_id" INTEGER NOT NULL,
    "theme_id" INTEGER NOT NULL,
    "confidence_score" REAL NOT NULL, -- 0.0 to 1.0
    "relevance_score" REAL, -- How relevant this theme is to the item
    "model_name" TEXT NOT NULL,
    "reasoning" TEXT, -- LLM's explanation for this classification
    "generated" INTEGER NOT NULL DEFAULT (unixepoch()),
    "verified" INTEGER DEFAULT 0, -- Human verification flag
    "verified_by" TEXT, -- User who verified
    "verified_at" INTEGER, -- Timestamp of verification
    FOREIGN KEY ("item_id") REFERENCES "items"("id") ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY ("theme_id") REFERENCES "themes"("id") ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE("item_id", "theme_id")
) STRICT;

-- Table for storing prompt templates
CREATE TABLE IF NOT EXISTS "enrichment_prompts" (
    "id" INTEGER PRIMARY KEY,
    "name" TEXT NOT NULL UNIQUE,
    "type" TEXT NOT NULL, -- 'summary', 'theme_classification', 'entity_extraction', etc.
    "template" TEXT NOT NULL, -- The actual prompt template with placeholders
    "system_prompt" TEXT, -- System message for the LLM
    "parameters" TEXT, -- JSON defining required parameters
    "active" INTEGER NOT NULL DEFAULT 1,
    "version" INTEGER NOT NULL DEFAULT 1,
    "created" INTEGER NOT NULL DEFAULT (unixepoch()),
    "modified" INTEGER
) STRICT;

-- Table for batch processing jobs
CREATE TABLE IF NOT EXISTS "enrichment_jobs" (
    "id" INTEGER PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL, -- 'full_scan', 'incremental', 'specific_items'
    "status" TEXT NOT NULL, -- 'pending', 'running', 'completed', 'failed', 'cancelled'
    "query_filter" TEXT, -- SQL WHERE clause for selecting items
    "prompt_template_id" INTEGER,
    "model_name" TEXT NOT NULL,
    "batch_size" INTEGER DEFAULT 100,
    "items_processed" INTEGER DEFAULT 0,
    "items_total" INTEGER,
    "started" INTEGER,
    "completed" INTEGER,
    "error_log" TEXT,
    "created" INTEGER NOT NULL DEFAULT (unixepoch()),
    FOREIGN KEY ("prompt_template_id") REFERENCES "enrichment_prompts"("id") ON UPDATE CASCADE
) STRICT;

-- Table for tracking processing status per item
CREATE TABLE IF NOT EXISTS "enrichment_status" (
    "id" INTEGER PRIMARY KEY,
    "item_id" INTEGER NOT NULL,
    "job_id" INTEGER,
    "last_enriched" INTEGER, -- Last successful enrichment timestamp
    "enrichment_version" INTEGER DEFAULT 1, -- Track re-processing
    "skip_reason" TEXT, -- Why this item was skipped (too short, no content, etc.)
    "error_count" INTEGER DEFAULT 0,
    "last_error" TEXT,
    "processing_flags" INTEGER DEFAULT 0, -- Bitwise flags for various states
    FOREIGN KEY ("item_id") REFERENCES "items"("id") ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY ("job_id") REFERENCES "enrichment_jobs"("id") ON UPDATE CASCADE,
    UNIQUE("item_id")
) STRICT;

-- Table for discovered relationships between items
CREATE TABLE IF NOT EXISTS "item_relationships" (
    "id" INTEGER PRIMARY KEY,
    "item_id_1" INTEGER NOT NULL,
    "item_id_2" INTEGER NOT NULL,
    "relationship_type" TEXT NOT NULL, -- 'similar', 'follows', 'references', 'contradicts', etc.
    "strength" REAL, -- 0.0 to 1.0
    "reasoning" TEXT, -- LLM's explanation
    "model_name" TEXT NOT NULL,
    "discovered" INTEGER NOT NULL DEFAULT (unixepoch()),
    "verified" INTEGER DEFAULT 0,
    FOREIGN KEY ("item_id_1") REFERENCES "items"("id") ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY ("item_id_2") REFERENCES "items"("id") ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (item_id_1 < item_id_2), -- Ensure consistent ordering
    UNIQUE("item_id_1", "item_id_2", "relationship_type")
) STRICT;

-- Create indexes for performance
CREATE INDEX "idx_item_enrichments_item_type" ON "item_enrichments"("item_id", "enrichment_type");
CREATE INDEX "idx_item_themes_item" ON "item_themes"("item_id");
CREATE INDEX "idx_item_themes_theme" ON "item_themes"("theme_id");
CREATE INDEX "idx_item_themes_confidence" ON "item_themes"("confidence_score");
CREATE INDEX "idx_themes_parent" ON "themes"("parent_id");
CREATE INDEX "idx_enrichment_status_job" ON "enrichment_status"("job_id");
CREATE INDEX "idx_item_relationships_items" ON "item_relationships"("item_id_1", "item_id_2");

-- Views for easier querying
CREATE VIEW "items_with_themes" AS
SELECT 
    i.*,
    GROUP_CONCAT(t.name, ', ') as theme_names,
    AVG(it.confidence_score) as avg_theme_confidence
FROM items i
LEFT JOIN item_themes it ON i.id = it.item_id
LEFT JOIN themes t ON it.theme_id = t.id
GROUP BY i.id;

CREATE VIEW "theme_hierarchy" AS
WITH RECURSIVE theme_tree AS (
    SELECT id, parent_id, name, level, name as path
    FROM themes
    WHERE parent_id IS NULL
    
    UNION ALL
    
    SELECT t.id, t.parent_id, t.name, t.level, 
           tt.path || ' > ' || t.name as path
    FROM themes t
    JOIN theme_tree tt ON t.parent_id = tt.id
)
SELECT * FROM theme_tree;