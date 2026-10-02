-- Preserve source-specific details that make imported problems easier to solve in-app.
ALTER TABLE problems ADD COLUMN source_id TEXT;
ALTER TABLE problems ADD COLUMN starter_code TEXT;
