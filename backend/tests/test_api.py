import sys
import tempfile
import unittest
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, main
from app.models import Concept, Evaluation, TRANSITIONS, normalize_difficulty
from app.routes import daily_plans
from app.routes._shared import problem_concepts, string_list
from app.services.sms import SmsNotConfigured, build_daily_digest, send_sms
from app.services.scheduler import current_day
from app.services.database import connection, execute, run_migrations, target


class ModelTests(unittest.TestCase):
    def test_concept_defaults_to_an_unseen_unmastered_signal(self):
        concept = Concept(id="graphs", name="Graphs")

        self.assertEqual(concept.mastery, 0.0)
        self.assertIsNone(concept.recency)
        self.assertEqual(concept.exposureCount, 0)

    def test_concept_parses_recency_as_a_timestamp(self):
        concept = Concept(id="graphs", name="Graphs", recency="2026-10-07T12:00:00Z")

        self.assertEqual(concept.recency, datetime(2026, 10, 7, 12, tzinfo=timezone.utc))

    def test_difficulty_normalization_accepts_only_the_discrete_domain(self):
        self.assertEqual(normalize_difficulty("Medium"), "MEDIUM")
        self.assertEqual(normalize_difficulty(" hard "), "HARD")
        self.assertIsNone(normalize_difficulty("Expert"))

    def test_evaluation_allows_unassessable_submission(self):
        evaluation = Evaluation(retryRecommended=True)

        self.assertTrue(evaluation.retryRecommended)
        self.assertIsNone(evaluation.correctness)
        self.assertIsNone(evaluation.betterApproach)

    def test_status_state_machine_requires_an_attempt_before_solving(self):
        self.assertEqual(TRANSITIONS["not_started"], {"attempted"})
        self.assertIn("reviewed_complete", TRANSITIONS["attempted"])

    def test_plan_generator_can_include_problems_without_topics(self):
        selected = daily_plans.generate_plan_ids([
            {"id": "untagged", "topics": []},
            {"id": "arrays", "topics": ["arrays"]},
            {"id": "graphs", "topics": ["graphs"]},
        ])

        self.assertEqual(set(selected), {"untagged", "arrays", "graphs"})

    def test_plan_generator_includes_a_retry_before_new_work(self):
        selected = daily_plans.generate_plan_ids([
            {"id": "retry", "topics": ["graphs"], "status": "reviewed_needs_retry"},
            {"id": "new-one", "topics": ["arrays"], "status": "not_started"},
            {"id": "new-two", "topics": ["trees"], "status": "not_started"},
        ])

        self.assertEqual(selected[0], "retry")

    def test_optional_problem_metadata_ignores_malformed_json(self):
        self.assertEqual(string_list("[\"arrays\",\n"), [])

    def test_daily_digest_contains_each_problem_and_dashboard_link(self):
        message = build_daily_digest({"problems": [{"title": "Two Sum"}, {"title": "Coin Change"}]}, "https://console.example")

        self.assertIn("Two Sum · Coin Change", message)
        self.assertIn("https://console.example", message)

    def test_sms_requires_configuration_before_a_network_request(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SmsNotConfigured):
                send_sms("test")

    def test_scheduler_uses_an_iso_local_day(self):
        with patch.dict("os.environ", {"APP_TIMEZONE": "America/Los_Angeles"}):
            self.assertRegex(current_day(), r"^\d{4}-\d{2}-\d{2}$")

    def test_migrations_create_schema_and_are_idempotent_for_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "console.db"
            run_migrations(database_path)
            run_migrations(database_path)
            with connection(database_path) as con:
                versions = execute(con, "SELECT version FROM schema_migrations").fetchall()
                tables = execute(con, "SELECT name FROM sqlite_master WHERE type='table' AND name='submissions'").fetchall()

            self.assertEqual(
                [row["version"] for row in versions],
                ["001_initial.sql", "002_persist_problem_bank.sql", "005_problem_source_fields.sql", "006_concepts.sql", "007_seed_leetcode_concepts.sql", "008_submission_outcomes.sql", "009_problem_concepts.sql", "010_submission_outcome_scores.sql"],
            )
            self.assertTrue(tables)

    def test_database_url_overrides_local_sqlite_path(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://example"}):
            self.assertEqual(target(Path("local.db")), "postgresql://example")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = config.DB
        config.DB = Path(self.temp_dir.name) / "test.db"
        self.auth_environment = patch.dict(
            "os.environ",
            {
                "BASIC_AUTH_USERNAME": "test-user",
                "BASIC_AUTH_PASSWORD": "test-password",
                "CRON_SECRET": "test-cron-secret",
            },
        )
        self.auth_environment.start()
        self.client = TestClient(main.app)
        self.client.__enter__()
        token = b64encode(b"test-user:test-password").decode()
        self.client.headers.update({"Authorization": f"Basic {token}"})

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.auth_environment.stop()
        config.DB = self.original_db
        self.temp_dir.cleanup()

    def test_health_check_is_public(self):
        response = self.client.get("/api/health", headers={"Authorization": ""})

        self.assertEqual(response.status_code, 200)

    def test_session_check_requires_and_accepts_authentication(self):
        response = self.client.get("/api/session")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_cors_reads_the_configured_frontend_origins(self):
        with patch.dict("os.environ", {"CORS_ORIGINS": "https://dashboard.example"}):
            origins = config.cors_origins()

        self.assertEqual(origins, ["https://dashboard.example"])

    def test_api_rejects_missing_or_invalid_credentials(self):
        missing = self.client.get("/api/daily", headers={"Authorization": ""})
        invalid_token = b64encode(b"test-user:wrong-password").decode()
        invalid = self.client.get("/api/daily", headers={"Authorization": f"Basic {invalid_token}"})

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.headers["www-authenticate"], "Basic")
        self.assertEqual(invalid.status_code, 401)

    def test_api_fails_closed_when_authentication_is_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            response = self.client.get("/api/daily")

        self.assertEqual(response.status_code, 503)

    def test_cron_requires_its_own_bearer_secret(self):
        basic_auth = self.client.get("/api/cron/generate-daily-plan")
        missing = self.client.get("/api/cron/generate-daily-plan", headers={"Authorization": ""})
        invalid = self.client.get(
            "/api/cron/generate-daily-plan",
            headers={"Authorization": "Bearer wrong-secret"},
        )

        self.assertEqual(basic_auth.status_code, 401)
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(invalid.status_code, 401)

    def test_cron_fails_closed_without_a_configured_secret(self):
        with patch.dict("os.environ", {"BASIC_AUTH_USERNAME": "test-user"}, clear=True):
            response = self.client.get(
                "/api/cron/generate-daily-plan",
                headers={"Authorization": "Bearer test-cron-secret"},
            )

        self.assertEqual(response.status_code, 503)

    def test_cron_generates_one_idempotent_daily_plan(self):
        headers = {"Authorization": "Bearer test-cron-secret"}
        first = self.client.get("/api/cron/generate-daily-plan", headers=headers)
        second = self.client.get("/api/cron/generate-daily-plan", headers=headers)
        with connection(config.DB) as con:
            count = execute(con, "SELECT COUNT(*) AS count FROM daily_plans").fetchone()["count"]

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(first.json()["problemIds"]), 3)
        self.assertEqual(count, 1)

    def test_daily_endpoint_returns_three_topic_diverse_problems(self):
        response = self.client.get("/api/daily")

        self.assertEqual(response.status_code, 200)
        problems = response.json()["problems"]
        self.assertEqual(len(problems), 3)
        self.assertEqual(len({problem["id"] for problem in problems}), 3)

    def test_problem_endpoint_returns_a_persisted_problem(self):
        problem_id = self.client.get("/api/daily").json()["problems"][0]["id"]

        response = self.client.get(f"/api/problems/{problem_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], problem_id)
        self.assertEqual(response.json()["concepts"], [])

    def test_problem_concepts_are_serialized_with_learning_state(self):
        with connection(config.DB) as con:
            execute(con, "INSERT INTO problem_concepts(problem_id, concept_id) VALUES (?, ?)", ("two-sum", "array"))
            concepts = problem_concepts(con, "two-sum")

        self.assertEqual(concepts[0]["id"], "array")
        self.assertEqual(concepts[0]["mastery"], 0.0)
        self.assertIsNone(concepts[0]["recency"])

    def test_submission_then_review_updates_problem_status(self):
        problem_id = self.client.get("/api/daily").json()["problems"][0]["id"]
        submission = self.client.post(
            f"/api/problems/{problem_id}/submissions",
            json={"code": "return answer", "timeComplexity": "O(n)"},
        )

        self.assertEqual(submission.status_code, 200)
        reviewed = self.client.post(f"/api/submissions/{submission.json()['id']}/review")

        self.assertEqual(reviewed.status_code, 200)
        daily_problem = next(problem for problem in self.client.get("/api/daily").json()["problems"] if problem["id"] == problem_id)
        self.assertEqual(daily_problem["status"], "reviewed_needs_retry")
        self.assertTrue(daily_problem["latestSubmission"]["evaluation"]["retryRecommended"])

    def test_submission_can_record_optional_outcome_signals(self):
        problem_id = self.client.get("/api/daily").json()["problems"][0]["id"]

        response = self.client.post(
            f"/api/problems/{problem_id}/submissions",
            json={"code": "return answer", "completionState": "hint_used", "timeTakenMinutes": 23},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["completionState"], "hint_used")
        self.assertEqual(response.json()["timeTakenMinutes"], 23)
        self.assertEqual(response.json()["outcomeScore"], 0.4)

    def test_submission_updates_linked_concept_learning_state(self):
        with connection(config.DB) as con:
            execute(con, "INSERT INTO problem_concepts(problem_id, concept_id) VALUES (?, ?)", ("two-sum", "array"))

        response = self.client.post(
            "/api/problems/two-sum/submissions",
            json={"code": "return answer", "completionState": "solved_independently", "timeTakenMinutes": 20},
        )

        with connection(config.DB) as con:
            concept = execute(
                con,
                "SELECT mastery, exposure_count, recency FROM concepts WHERE id=?",
                ("array",),
            ).fetchone()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcomeScore"], 1.0)
        self.assertEqual(self.client.get("/api/problems/two-sum").json()["latestSubmission"]["outcomeScore"], 1.0)
        self.assertEqual(concept["mastery"], 0.6)
        self.assertEqual(concept["exposure_count"], 1)
        self.assertIsNotNone(concept["recency"])

    def test_submission_splits_learning_update_equally_across_two_concepts(self):
        with connection(config.DB) as con:
            execute(con, "INSERT INTO problem_concepts(problem_id, concept_id) VALUES (?, ?)", ("two-sum", "array"))
            execute(con, "INSERT INTO problem_concepts(problem_id, concept_id) VALUES (?, ?)", ("two-sum", "hash-table"))

        response = self.client.post(
            "/api/problems/two-sum/submissions",
            json={"code": "return answer", "completionState": "solved_independently"},
        )

        with connection(config.DB) as con:
            concepts = execute(
                con,
                "SELECT id, mastery, exposure_count FROM concepts WHERE id IN (?, ?) ORDER BY id",
                ("array", "hash-table"),
            ).fetchall()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([(row["id"], row["mastery"], row["exposure_count"]) for row in concepts], [("array", 0.3, 1), ("hash-table", 0.3, 1)])

    def test_submission_without_concepts_persists_without_changing_concept_state(self):
        with connection(config.DB) as con:
            before = execute(con, "SELECT SUM(exposure_count) AS total FROM concepts").fetchone()["total"]

        response = self.client.post(
            "/api/problems/two-sum/submissions",
            json={"code": "return answer", "completionState": "solved_independently"},
        )

        with connection(config.DB) as con:
            after = execute(con, "SELECT SUM(exposure_count) AS total FROM concepts").fetchone()["total"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(before, after)
        self.assertEqual(self.client.get("/api/problems/two-sum").json()["latestSubmission"]["id"], response.json()["id"])

    def test_cannot_mark_unstarted_problem_as_solved(self):
        problem_id = self.client.get("/api/daily").json()["problems"][0]["id"]

        response = self.client.put(f"/api/problems/{problem_id}/status", json={"status": "solved"})

        self.assertEqual(response.status_code, 409)
