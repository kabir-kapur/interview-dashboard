-- Store the deterministic score that was used for a submission's learning update.
ALTER TABLE submissions ADD COLUMN outcome_score REAL CHECK (
    outcome_score >= 0 AND outcome_score <= 1
);
