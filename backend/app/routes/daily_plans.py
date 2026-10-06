"""Daily-plan selection, persistence, and HTTP routes."""

import json

from fastapi import APIRouter

from app import config
from app.routes._shared import db, serialize_problem, serialize_submission, string_list
from app.services.database import execute, uses_postgres
from app.services.scheduler import current_day, generate_plan_ids


router = APIRouter()


def planning_candidates(con) -> list[dict]:
    """Load only the metadata required to generate a daily plan."""
    rows = execute(con, "SELECT id, topics, status FROM problems").fetchall()
    return [
        {"id": row["id"], "topics": string_list(row["topics"]), "status": row["status"]}
        for row in rows
    ]


def saved_plan_ids(row) -> list[str]:
    """Read the database-specific plan array into a regular Python list."""
    return row["problem_ids"] if uses_postgres(config.DB) else json.loads(row["ids"])


def save_plan(con, day: str, problem_ids: list[str]) -> None:
    """Persist selected IDs while retaining a lightweight SQLite fallback."""
    if uses_postgres(config.DB):
        execute(con, "INSERT INTO daily_plans(day, problem_ids) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET problem_ids=excluded.problem_ids", (day, problem_ids))
    else:
        execute(con, "INSERT INTO daily_plans(day, ids) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET ids=excluded.ids", (day, json.dumps(problem_ids)))


def daily(refresh: bool = False) -> dict:
    """Return today's persisted plan, generating it only when required."""
    day = current_day()
    with db() as con:
        row = execute(con, "SELECT * FROM daily_plans WHERE day=?", (day,)).fetchone()
        ids = saved_plan_ids(row) if row else []
        existing = set(row["id"] for row in execute(con, "SELECT id FROM problems WHERE id IN ({})".format(",".join("?" for _ in ids)), tuple(ids)).fetchall()) if ids else set()
        if refresh or not row or any(problem_id not in existing for problem_id in ids):
            ids = generate_plan_ids(planning_candidates(con))
            save_plan(con, day, ids)
        selected = []
        for problem_id in ids:
            problem = execute(con, "SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
            submission = execute(con, "SELECT * FROM submissions WHERE problem_id=? ORDER BY created_at DESC LIMIT 1", (problem_id,)).fetchone()
            selected.append({**serialize_problem(problem), "latestSubmission": serialize_submission(submission)})
        return {"date": day, "problems": selected}


@router.get("/daily")
def get_daily():
    """Return today's selected problems."""
    return daily()


@router.post("/daily/refresh")
def refresh_daily():
    """Replace today's persisted daily plan."""
    return daily(True)
