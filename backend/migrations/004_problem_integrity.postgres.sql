-- Enforce the single-user console's problem-state contract in PostgreSQL.
ALTER TABLE problems ALTER COLUMN status_updated_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE problems ADD CONSTRAINT problems_valid_status CHECK (status IN (
    'not_started', 'attempted', 'solved', 'reviewed_needs_retry', 'reviewed_complete'
));
ALTER TABLE submissions ADD CONSTRAINT submissions_problem_id_fkey
    FOREIGN KEY (problem_id) REFERENCES problems(id);
