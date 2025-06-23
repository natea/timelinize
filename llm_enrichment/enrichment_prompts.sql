-- Enrichment Prompt Templates for Timelinize LLM Processing

-- Summary Generation Prompt
INSERT INTO enrichment_prompts (name, type, template, system_prompt, parameters, active, version)
VALUES (
    'item_summary_v1',
    'summary',
    'Analyze this timeline item and provide a concise summary (1-2 sentences) that captures the essential information:

Content: {content}
Type: {data_type}
Date: {date}
Location: {location}

Focus on: WHO was involved, WHAT happened, WHEN it occurred, WHERE it took place, and WHY it matters.

Summary:',
    'You are a helpful assistant that creates clear, informative summaries of personal timeline data. Be concise but include key details.',
    '{"content": "required", "data_type": "optional", "date": "optional", "location": "optional"}',
    1,
    1
);

-- Theme Classification Prompt
INSERT INTO enrichment_prompts (name, type, template, system_prompt, parameters, active, version)
VALUES (
    'theme_classification_v1',
    'theme_classification',
    'Classify this timeline item into relevant themes from the provided taxonomy. Return a JSON array with theme IDs and confidence scores (0.0-1.0).

Content: {content}
Type: {data_type}
Date: {date}
Metadata: {metadata}

Available Themes:
{theme_taxonomy}

Instructions:
1. Analyze the content and context
2. Match to 1-5 most relevant themes
3. Assign confidence scores based on relevance
4. Consider both parent and child themes
5. Use keywords as hints but focus on semantic meaning

Return format:
[{"theme_id": <id>, "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}]

Classification:',
    'You are an expert at categorizing personal timeline data into meaningful themes. Be accurate and consider context.',
    '{"content": "required", "data_type": "optional", "date": "optional", "metadata": "optional", "theme_taxonomy": "required"}',
    1,
    1
);

-- Sentiment Analysis Prompt
INSERT INTO enrichment_prompts (name, type, template, system_prompt, parameters, active, version)
VALUES (
    'sentiment_analysis_v1',
    'sentiment',
    'Analyze the sentiment and emotional tone of this timeline item:

Content: {content}
Context: {context}

Provide:
1. Overall sentiment: positive/negative/neutral/mixed
2. Emotional intensity: 0.0-1.0
3. Detected emotions (e.g., joy, sadness, excitement, stress)
4. Brief explanation

Format as JSON:
{"sentiment": "", "intensity": 0.0, "emotions": [], "explanation": ""}

Analysis:',
    'You are skilled at detecting emotional tone and sentiment in personal data while being sensitive to context.',
    '{"content": "required", "context": "optional"}',
    1,
    1
);

-- Entity Extraction Prompt
INSERT INTO enrichment_prompts (name, type, template, system_prompt, parameters, active, version)
VALUES (
    'entity_extraction_v1',
    'entity_extraction',
    'Extract key entities from this timeline item:

Content: {content}
Type: {data_type}

Extract:
1. People (names, relationships)
2. Organizations (companies, institutions)
3. Locations (cities, venues, addresses)
4. Events (meetings, activities)
5. Topics/Concepts (main subjects discussed)

Format as JSON:
{
  "people": [{"name": "", "relationship": ""}],
  "organizations": [{"name": "", "type": ""}],
  "locations": [{"name": "", "type": ""}],
  "events": [{"name": "", "type": ""}],
  "topics": [""]
}

Entities:',
    'You excel at identifying and extracting meaningful entities from text while understanding context and relationships.',
    '{"content": "required", "data_type": "optional"}',
    1,
    1
);

-- Relationship Discovery Prompt
INSERT INTO enrichment_prompts (name, type, template, system_prompt, parameters, active, version)
VALUES (
    'relationship_discovery_v1',
    'relationship_discovery',
    'Analyze these timeline items and identify relationships between them:

Items:
{items_json}

Identify relationships such as:
- Sequential events (one leads to another)
- Similar topics or themes
- Same people/places involved
- Cause and effect
- Contradictions or conflicts
- Part of larger pattern/project

Format as JSON array:
[{
  "item_id_1": <id>,
  "item_id_2": <id>,
  "relationship_type": "similar|follows|references|contradicts|related",
  "strength": <0.0-1.0>,
  "reasoning": "<explanation>"
}]

Relationships:',
    'You are skilled at finding meaningful connections between different events and data points in personal timelines.',
    '{"items_json": "required"}',
    1,
    1
);

-- Contextual Insights Prompt
INSERT INTO enrichment_prompts (name, type, template, system_prompt, parameters, active, version)
VALUES (
    'contextual_insights_v1',
    'context',
    'Provide contextual insights about this timeline item that might not be immediately obvious:

Content: {content}
Date: {date}
Related Items: {related_items}

Consider:
1. What this might indicate about the person''s life at this time
2. Potential patterns or trends
3. Significance in broader context
4. Interesting observations or anomalies

Insights (2-3 bullet points):',
    'You provide thoughtful, meaningful insights about personal timeline data that help people understand their life patterns better.',
    '{"content": "required", "date": "optional", "related_items": "optional"}',
    1,
    1
);

-- Batch Theme Classification Prompt (for efficiency)
INSERT INTO enrichment_prompts (name, type, template, system_prompt, parameters, active, version)
VALUES (
    'batch_theme_classification_v1',
    'theme_classification',
    'Classify multiple timeline items into themes efficiently. Return a JSON object mapping item IDs to their theme classifications.

Items:
{items_batch_json}

Theme Taxonomy:
{theme_taxonomy}

For each item, assign 1-5 relevant themes with confidence scores.

Return format:
{
  "<item_id>": [{"theme_id": <id>, "confidence": <0.0-1.0>}],
  ...
}

Classifications:',
    'You efficiently classify multiple items while maintaining accuracy and considering relationships between items.',
    '{"items_batch_json": "required", "theme_taxonomy": "required"}',
    1,
    1
);