-- Portable initial schema. Applied by app.services.database.run_migrations.
CREATE TABLE IF NOT EXISTS plans (
    day TEXT PRIMARY KEY,
    ids TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    problem_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    problem_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    code TEXT NOT NULL,
    time_complexity TEXT,
    space_complexity TEXT,
    explanation TEXT,
    evaluation TEXT
);

CREATE TABLE IF NOT EXISTS digest_deliveries (
    day TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    provider_message_id TEXT,
    attempted_at TEXT NOT NULL,
    sent_at TEXT,
    error_message TEXT,
    PRIMARY KEY(day, channel)
);
