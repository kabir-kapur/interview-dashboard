"""Database and serialization helpers used by API route modules."""

import json
from datetime import datetime, timezone

from fastapi import HTTPException

from app import config
from app.models import normalize_difficulty
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


def serialize_concept(row) -> dict:
    """Convert a persisted concept into the API response shape."""
    return {
        "id": row["id"], "name": row["name"], "mastery": row["mastery"],
        "recency": row["recency"], "exposureCount": row["exposure_count"],
    }


def problem_concepts(con, problem_id: str) -> list[dict]:
    """Load the normalized concepts associated with one problem."""
    rows = execute(
        con,
        """SELECT concepts.id, concepts.name, concepts.mastery, concepts.recency, concepts.exposure_count
           FROM problem_concepts JOIN concepts ON concepts.id=problem_concepts.concept_id
           WHERE problem_concepts.problem_id=? ORDER BY concepts.name""",
        (problem_id,),
    ).fetchall()
    return [serialize_concept(row) for row in rows]


def serialize_problem(row, concepts: list[dict] | None = None) -> dict:
    """Convert persisted problem fields into the API response shape."""
    return {
        "id": row["id"], "title": row["title"], "prompt": row["prompt"], "link": row["link"],
        "sourceId": row["source_id"], "starterCode": row["starter_code"],
        "topics": string_list(row["topics"]), "concepts": concepts or [],
        "difficulty": normalize_difficulty(row["difficulty"]),
        "companies": string_list(row["companies"]), "status": row["status"],
    }


def serialize_submission(row) -> dict | None:
    """Convert an optional persisted submission into the API response shape."""
    return None if not row else {
        "id": row["id"], "problemId": row["problem_id"], "createdAt": row["created_at"],
        "code": row["code"], "timeComplexity": row["time_complexity"],
        "spaceComplexity": row["space_complexity"], "explanation": row["explanation"],
        "completionState": row["completion_state"], "timeTakenMinutes": row["time_taken_minutes"],
        "outcomeScore": row["outcome_score"],
        "evaluation": json.loads(row["evaluation"]) if row["evaluation"] else None,
    }


def problem_detail(con, problem_id: str) -> dict:
    """Load one persisted problem with its most recent submission."""
    row = execute(con, "SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Problem not found")
    latest_submission = execute(con, "SELECT * FROM submissions WHERE problem_id=? ORDER BY created_at DESC LIMIT 1", (problem_id,)).fetchone()
    return {
        **serialize_problem(row, problem_concepts(con, problem_id)),
        "latestSubmission": serialize_submission(latest_submission),
    }
