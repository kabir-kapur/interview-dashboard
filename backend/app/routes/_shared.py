"""Database and serialization helpers used by API route modules."""

import json
from datetime import datetime, timezone

from fastapi import HTTPException

from app import config
from app.services.database import connection, execute


def db():
    """Return a transaction for the configured PostgreSQL or local SQLite database."""
    return connection(config.DB)


def now() -> str:
    """Return the current timestamp in a portable ISO format."""
    return datetime.now(timezone.utc).isoformat()


def string_list(value) -> list[str]:
    """Return optional JSON metadata as a safe list for API consumers."""
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed) else []


def serialize_problem(row) -> dict:
    """Convert persisted problem fields into the API response shape."""
    return {
        "id": row["id"], "title": row["title"], "prompt": row["prompt"], "link": row["link"],
        "sourceId": row["source_id"], "starterCode": row["starter_code"],
        "topics": string_list(row["topics"]), "difficulty": row["difficulty"],
        "companies": string_list(row["companies"]), "status": row["status"],
    }


def serialize_submission(row) -> dict | None:
    """Convert an optional persisted submission into the API response shape."""
    return None if not row else {
        "id": row["id"], "problemId": row["problem_id"], "createdAt": row["created_at"],
        "code": row["code"], "timeComplexity": row["time_complexity"],
        "spaceComplexity": row["space_complexity"], "explanation": row["explanation"],
        "evaluation": json.loads(row["evaluation"]) if row["evaluation"] else None,
    }


def problem_detail(con, problem_id: str) -> dict:
    """Load one persisted problem with its most recent submission."""
    row = execute(con, "SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Problem not found")
    latest_submission = execute(con, "SELECT * FROM submissions WHERE problem_id=? ORDER BY created_at DESC LIMIT 1", (problem_id,)).fetchone()
    return {**serialize_problem(row), "latestSubmission": serialize_submission(latest_submission)}
