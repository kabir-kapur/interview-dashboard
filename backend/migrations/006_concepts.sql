-- Persist reusable concept signals; recency stores an ISO-8601 timestamp portably as text.
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mastery REAL NOT NULL DEFAULT 0 CHECK (mastery >= 0 AND mastery <= 1),
    recency TEXT,
    exposure_count INTEGER NOT NULL DEFAULT 0 CHECK (exposure_count >= 0)
);
