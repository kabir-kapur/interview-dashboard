-- Supabase stores daily selections as a simple, ordered array of problem IDs.
ALTER TABLE daily_plans ADD COLUMN problem_ids TEXT[] NOT NULL DEFAULT '{}';
UPDATE daily_plans SET problem_ids = ARRAY(SELECT jsonb_array_elements_text(ids::jsonb));
ALTER TABLE daily_plans DROP COLUMN ids;
