import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.database import connection, execute, run_migrations


class MigrationTests(unittest.TestCase):
    """Exercise the versioned schema against the supported local database."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "console.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_migration_creates_the_expected_tables_and_columns(self):
        run_migrations(self.database_path)

        expected = {
            "plans": {"day", "ids"},
            "progress": {"problem_id", "status", "updated_at"},
            "submissions": {
                "id",
                "problem_id",
                "created_at",
                "code",
                "time_complexity",
                "space_complexity",
                "explanation",
                "evaluation",
            },
            "digest_deliveries": {
                "day",
                "channel",
                "status",
                "provider_message_id",
                "attempted_at",
                "sent_at",
                "error_message",
            },
        }

        with connection(self.database_path) as con:
            for table, columns in expected.items():
                actual = {row["name"] for row in execute(con, f"PRAGMA table_info({table})").fetchall()}
                self.assertEqual(actual, columns)

    def test_rerunning_migrations_preserves_existing_data_and_records_one_version(self):
        run_migrations(self.database_path)
        with connection(self.database_path) as con:
            execute(
                con,
                "INSERT INTO progress(problem_id, status, updated_at) VALUES (?, ?, ?)",
                ("two-sum", "attempted", "2026-09-30T12:00:00+00:00"),
            )

        run_migrations(self.database_path)

        with connection(self.database_path) as con:
            progress = execute(con, "SELECT status FROM progress WHERE problem_id=?", ("two-sum",)).fetchone()
            versions = execute(con, "SELECT version FROM schema_migrations ORDER BY version").fetchall()

        self.assertEqual(progress["status"], "attempted")
        self.assertEqual([row["version"] for row in versions], ["001_initial.sql"])

    def test_migration_files_remain_portable_to_postgresql(self):
        migration = (Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql").read_text().lower()

        self.assertNotIn("autoincrement", migration)
        self.assertNotIn("pragma", migration)
        self.assertNotIn("sqlite_", migration)

