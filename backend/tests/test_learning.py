import sys
import tempfile
import unittest
from math import sqrt
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.database import connection, execute, run_migrations
from app.services.recommender import outcome_score, update_concept_learning


class LearningTests(unittest.TestCase):
    """Exercise deterministic Phase 2 concept updates without API dependencies."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "console.db"
        run_migrations(self.database_path)
        with connection(self.database_path) as con:
            execute(con, "INSERT INTO problem_concepts(problem_id, concept_id) VALUES (?, ?)", ("two-sum", "array"))
            execute(con, "INSERT INTO problem_concepts(problem_id, concept_id) VALUES (?, ?)", ("two-sum", "hash-table"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_outcome_score_uses_only_deterministic_submission_fields(self):
        self.assertEqual(outcome_score("solved_independently", 20), 1.0)
        self.assertEqual(outcome_score("solved_independently", 45), 0.7)
        self.assertEqual(outcome_score("hint_used", None), 0.4)
        self.assertEqual(outcome_score("gave_up", None), 0.0)
        self.assertIsNone(outcome_score(None, None))

    def test_learning_update_shares_mastery_change_across_linked_concepts(self):
        with connection(self.database_path) as con:
            update_concept_learning(con, "two-sum", 1.0, "2026-10-10T12:00:00+00:00")
            concepts = execute(
                con,
                "SELECT id, mastery, exposure_count, recency FROM concepts WHERE id IN (?, ?) ORDER BY id",
                ("array", "hash-table"),
            ).fetchall()

        self.assertEqual([(concept["id"], concept["exposure_count"]) for concept in concepts], [("array", 1), ("hash-table", 1)])
        self.assertEqual([concept["recency"] for concept in concepts], ["2026-10-10T12:00:00+00:00"] * 2)
        self.assertEqual([concept["mastery"] for concept in concepts], [0.3, 0.3])

    def test_second_scored_update_uses_prior_exposure_for_a_smaller_step(self):
        with connection(self.database_path) as con:
            update_concept_learning(con, "two-sum", 1.0, "2026-10-10T12:00:00+00:00")
            update_concept_learning(con, "two-sum", 0.0, "2026-10-11T12:00:00+00:00")
            concept = execute(
                con,
                "SELECT mastery, exposure_count, recency FROM concepts WHERE id=?",
                ("array",),
            ).fetchone()

        expected_mastery = 0.3 + (0.6 / sqrt(2) * 0.5) * (0.0 - 0.3)
        self.assertAlmostEqual(concept["mastery"], expected_mastery)
        self.assertEqual(concept["exposure_count"], 2)
        self.assertEqual(concept["recency"], "2026-10-11T12:00:00+00:00")

    def test_unscored_submission_records_exposure_without_changing_mastery(self):
        with connection(self.database_path) as con:
            execute(con, "UPDATE concepts SET mastery=? WHERE id=?", (0.5, "array"))
            update_concept_learning(con, "two-sum", None, "2026-10-10T12:00:00+00:00")
            concept = execute(
                con,
                "SELECT mastery, exposure_count, recency FROM concepts WHERE id=?",
                ("array",),
            ).fetchone()

        self.assertEqual(tuple(concept), (0.5, 1, "2026-10-10T12:00:00+00:00"))
