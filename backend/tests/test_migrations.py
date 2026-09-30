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
            "daily_plans": {"day", "ids"},
            "problems": {
                "id",
                "title",
                "prompt",
                "link",
                "topics",
                "difficulty",
                "companies",
                "status",
                "status_updated_at",
                "created_at",
            },
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
        }

        with connection(self.database_path) as con:
            for table, columns in expected.items():
                actual = {row["name"] for row in execute(con, f"PRAGMA table_info({table})").fetchall()}
                self.assertEqual(actual, columns)
            seeded = execute(con, "SELECT COUNT(*) AS count FROM problems").fetchone()
            tables = {row["name"] for row in execute(con, "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        self.assertEqual(seeded["count"], 8)
        self.assertNotIn("progress", tables)
        self.assertNotIn("digest_deliveries", tables)
    def test_rerunning_migrations_preserves_existing_data_and_records_one_version(self):
        run_migrations(self.database_path)
        with connection(self.database_path) as con:
            execute(
                con,
                "UPDATE problems SET status=? WHERE id=?",
                ("attempted", "two-sum"),
            )

        run_migrations(self.database_path)

        with connection(self.database_path) as con:
            progress = execute(con, "SELECT status FROM problems WHERE id=?", ("two-sum",)).fetchone()
            versions = execute(con, "SELECT version FROM schema_migrations ORDER BY version").fetchall()

        self.assertEqual(progress["status"], "attempted")
        self.assertEqual([row["version"] for row in versions], ["001_initial.sql", "002_persist_problem_bank.sql"])

    def test_problem_metadata_is_optional(self):
        run_migrations(self.database_path)
        with connection(self.database_path) as con:
            execute(
                con,
                "INSERT INTO problems(id, title, prompt, topics, difficulty, companies, status, status_updated_at, created_at) VALUES (?, ?, ?, NULL, NULL, NULL, ?, ?, ?)",
                ("custom", "Custom", "Prompt", "not_started", "now", "now"),
            )

        with connection(self.database_path) as con:
            row = execute(con, "SELECT topics, difficulty, companies FROM problems WHERE id=?", ("custom",)).fetchone()
        self.assertEqual(tuple(row), (None, None, None))

    def test_migration_files_remain_portable_to_postgresql(self):
        migration_dir = Path(__file__).resolve().parents[1] / "migrations"
        migration = "\n".join(file.read_text() for file in migration_dir.glob("*.sql") if not file.name.endswith(".postgres.sql")).lower()

        self.assertNotIn("autoincrement", migration)
        self.assertNotIn("pragma", migration)
        self.assertNotIn("sqlite_", migration)

    def test_postgres_plan_migration_uses_a_native_id_array(self):
        migration = (Path(__file__).resolve().parents[1] / "migrations" / "003_postgres_plan_arrays.postgres.sql").read_text()

        self.assertIn("problem_ids TEXT[]", migration)

    def test_postgres_integrity_migration_sets_problem_defaults_and_constraints(self):
        migration = (Path(__file__).resolve().parents[1] / "migrations" / "004_problem_integrity.postgres.sql").read_text()

        self.assertIn("SET DEFAULT CURRENT_TIMESTAMP", migration)
        self.assertIn("problems_valid_status", migration)
        self.assertIn("FOREIGN KEY (problem_id) REFERENCES problems(id)", migration)
