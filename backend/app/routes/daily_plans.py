"""Daily-plan selection, persistence, and HTTP routes."""

import json
import random

from fastapi import APIRouter

from app import config
from app.routes._shared import db, serialize_problem, serialize_submission
from app.services.database import execute, uses_postgres
from app.services.scheduler import current_day


router = APIRouter()


def problems(con) -> list[dict]:
    """Load the canonical problem bank from the configured database."""
    return [serialize_problem(row) for row in execute(con, "SELECT * FROM problems ORDER BY title").fetchall()]


def choose(bank: list[dict]) -> list[str]:
    """Pick up to three problems while preferring distinct topic buckets."""
    buckets: dict[str, list[dict]] = {}
    for problem in bank:
        for topic in problem["topics"]:
            buckets.setdefault(topic, []).append(problem)
    picked: list[dict] = []
    for topic in random.sample(list(buckets), len(buckets)):
        choices = [problem for problem in buckets[topic] if problem not in picked]
        if choices:
            picked.append(random.choice(choices))
        if len(picked) == 3:
            break
    remaining = [problem for problem in bank if problem not in picked]
    picked.extend(random.sample(remaining, min(3 - len(picked), len(remaining))))
    return [problem["id"] for problem in picked]


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
        bank = problems(con)
        lookup = {item["id"]: item for item in bank}
        row = execute(con, "SELECT * FROM daily_plans WHERE day=?", (day,)).fetchone()
        ids = saved_plan_ids(row) if row else []
        if refresh or not row or any(item not in lookup for item in ids):
            ids = choose(bank)
            save_plan(con, day, ids)
        selected = []
        for problem_id in ids:
            submission = execute(con, "SELECT * FROM submissions WHERE problem_id=? ORDER BY created_at DESC LIMIT 1", (problem_id,)).fetchone()
            selected.append({**lookup[problem_id], "latestSubmission": serialize_submission(submission)})
        return {"date": day, "problems": selected}


@router.get("/daily")
def get_daily():
    """Return today's selected problems."""
    return daily()


@router.post("/daily/refresh")
def refresh_daily():
    """Replace today's persisted daily plan."""
    return daily(True)
