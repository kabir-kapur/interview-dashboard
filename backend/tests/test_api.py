import sys
import tempfile
import unittest
from base64 import b64encode
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main
from app.models import Evaluation, TRANSITIONS
from app.services.sms import SmsNotConfigured, build_daily_digest, send_sms
from app.services.scheduler import current_day
from app.services.database import connection, execute, run_migrations, target


class ModelTests(unittest.TestCase):
    def test_evaluation_allows_unassessable_submission(self):
        evaluation = Evaluation(retryRecommended=True)

        self.assertTrue(evaluation.retryRecommended)
        self.assertIsNone(evaluation.correctness)
        self.assertIsNone(evaluation.betterApproach)

    def test_status_state_machine_requires_an_attempt_before_solving(self):
        self.assertEqual(TRANSITIONS["not_started"], {"attempted"})
        self.assertIn("reviewed_complete", TRANSITIONS["attempted"])

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

            self.assertEqual([row["version"] for row in versions], ["001_initial.sql", "002_persist_problem_bank.sql"])
            self.assertTrue(tables)

    def test_database_url_overrides_local_sqlite_path(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://example"}):
            self.assertEqual(target(Path("local.db")), "postgresql://example")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = main.DB
        main.DB = Path(self.temp_dir.name) / "test.db"
        self.auth_environment = patch.dict(
            "os.environ",
            {"BASIC_AUTH_USERNAME": "test-user", "BASIC_AUTH_PASSWORD": "test-password"},
        )
        self.auth_environment.start()
        self.client = TestClient(main.app)
        self.client.__enter__()
        token = b64encode(b"test-user:test-password").decode()
        self.client.headers.update({"Authorization": f"Basic {token}"})

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.auth_environment.stop()
        main.DB = self.original_db
        self.temp_dir.cleanup()

    def test_health_check_is_public(self):
        response = self.client.get("/api/health", headers={"Authorization": ""})

        self.assertEqual(response.status_code, 200)

    def test_cors_reads_the_configured_frontend_origins(self):
        with patch.dict("os.environ", {"CORS_ORIGINS": "https://dashboard.example"}):
            origins = main.cors_origins()

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

    def test_daily_endpoint_returns_three_topic_diverse_problems(self):
        response = self.client.get("/api/daily")

        self.assertEqual(response.status_code, 200)
        problems = response.json()["problems"]
        self.assertEqual(len(problems), 3)
        self.assertEqual(len({problem["id"] for problem in problems}), 3)

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

    def test_cannot_mark_unstarted_problem_as_solved(self):
        problem_id = self.client.get("/api/daily").json()["problems"][0]["id"]

        response = self.client.put(f"/api/problems/{problem_id}/status", json={"status": "solved"})

        self.assertEqual(response.status_code, 409)
