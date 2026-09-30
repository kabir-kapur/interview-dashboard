"""Small database compatibility layer for local SQLite and hosted PostgreSQL."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DatabaseTarget = Path | str


def target(sqlite_path: Path) -> DatabaseTarget:
    """Use DATABASE_URL when supplied; otherwise keep the local SQLite database."""
    return os.getenv("DATABASE_URL") or sqlite_path


def uses_postgres(sqlite_path: Path) -> bool:
    """Report whether the configured target is a PostgreSQL connection URL."""
    return str(target(sqlite_path)).startswith(("postgres://", "postgresql://"))


@contextmanager
def connection(sqlite_path: Path) -> Iterator[object]:
    """Open, commit, and close the configured SQL connection."""
    database = target(sqlite_path)
    if not isinstance(database, Path) and database.startswith(("postgres://", "postgresql://")):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as error:  # pragma: no cover - exercised only with production configuration
            raise RuntimeError("PostgreSQL requires the psycopg package. Install backend/requirements.txt.") from error
        con = psycopg.connect(database, row_factory=dict_row)
    else:
        con = sqlite3.connect(database)
        con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def execute(con: object, sql: str, params: tuple = ()) -> object:
    """Run portable parameterized SQL against either supported database."""
    if isinstance(con, sqlite3.Connection):
        return con.execute(sql, params)
    return con.execute(sql.replace("?", "%s"), params)


def execute_script(con: object, script: str) -> None:
    """Run a simple migration script; migrations intentionally contain plain statements only."""
    if isinstance(con, sqlite3.Connection):
        con.executescript(script)
        return
    for statement in script.split(";"):
        if statement.strip():
            con.execute(statement)


def run_migrations(sqlite_path: Path) -> None:
    """Apply each numbered SQL migration once and record it in the target database."""
    migration_dir = Path(__file__).resolve().parents[2] / "migrations"
    with connection(sqlite_path) as con:
        execute(con, "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        applied = {row["version"] for row in execute(con, "SELECT version FROM schema_migrations").fetchall()}
        for migration in sorted(migration_dir.glob("*.sql")):
            if migration.name.endswith(".postgres.sql") and not uses_postgres(sqlite_path):
                continue
            if migration.name in applied:
                continue
            execute_script(con, migration.read_text())
            execute(con, "INSERT INTO schema_migrations(version, applied_at) VALUES (?, CURRENT_TIMESTAMP)", (migration.name,))
