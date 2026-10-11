import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from math import sqrt
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.database import connection, execute, run_migrations
from app.services.recommender import (
    calculate_difficulty_fit,
    calculate_problem_features,
    calculate_problem_mastery_gap,
    calculate_problem_recency,
    calculate_recency,
    outcome_score,
    update_concept_learning,
)


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

    def test_recency_uses_the_configured_buckets_and_unseen_sentinel(self):
        now = datetime(2026, 10, 10, 12, tzinfo=UTC)

        self.assertEqual(calculate_recency(None, now), 1.0)
        self.assertEqual(calculate_recency(now - timedelta(hours=5, minutes=59), now), 0.0)
        self.assertEqual(calculate_recency(now - timedelta(hours=6), now), 0.1)
        self.assertEqual(calculate_recency(now - timedelta(days=1), now), 0.3)
        self.assertEqual(calculate_recency(now - timedelta(days=2), now), 0.5)
        self.assertEqual(calculate_recency(now - timedelta(days=3), now), 0.7)
        self.assertEqual(calculate_recency(now - timedelta(days=5), now), 0.9)
        self.assertEqual(calculate_recency("2026-10-09T12:00:00+00:00", now), 0.3)

    def test_problem_features_average_concepts_without_ranking(self):
        now = datetime(2026, 10, 10, 12, tzinfo=UTC)
        problem = {
            "difficulty": "MEDIUM",
            "concepts": [
                {"mastery": 0.2, "recency": now - timedelta(days=4)},
                {"mastery": 0.6, "recency": None},
            ],
        }

        self.assertEqual(calculate_problem_recency(problem["concepts"], now), 0.85)
        self.assertAlmostEqual(calculate_problem_mastery_gap(problem["concepts"]), 0.6)
        features = calculate_problem_features(problem, now)
        self.assertIsNotNone(features)
        self.assertEqual(features["recency"], 0.85)
        self.assertAlmostEqual(features["masteryGap"], 0.6)
        self.assertEqual(features["difficultyFit"], 1.0)

    def test_difficulty_fit_covers_each_configured_mastery_band(self):
        expected = {
            0.2: {"EASY": 1.0, "MEDIUM": 0.4, "HARD": 0.0},
            0.5: {"EASY": 0.6, "MEDIUM": 1.0, "HARD": 0.3},
            0.8: {"EASY": 0.2, "MEDIUM": 0.9, "HARD": 1.0},
        }

        for mastery, scores in expected.items():
            for difficulty, score in scores.items():
                self.assertEqual(calculate_difficulty_fit(difficulty, mastery), score)

    def test_problem_features_require_concepts_and_supported_difficulty(self):
        now = datetime(2026, 10, 10, 12, tzinfo=UTC)

        self.assertIsNone(calculate_problem_features({"difficulty": "MEDIUM", "concepts": []}, now))
        self.assertIsNone(calculate_problem_features({"difficulty": "UNKNOWN", "concepts": [{"mastery": 0.5, "recency": None}]}, now))
