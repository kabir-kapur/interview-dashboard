-- Normalize source tags into reusable concept associations for recommendation work.
CREATE TABLE IF NOT EXISTS problem_concepts (
    problem_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    PRIMARY KEY (problem_id, concept_id),
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS problem_concepts_concept_id_idx ON problem_concepts(concept_id);

-- Normalize historical source values without retaining unsupported difficulty labels.
UPDATE problems
SET difficulty = UPPER(difficulty)
WHERE UPPER(difficulty) IN ('EASY', 'MEDIUM', 'HARD');

UPDATE problems
SET difficulty = NULL
WHERE difficulty IS NOT NULL AND difficulty NOT IN ('EASY', 'MEDIUM', 'HARD');
