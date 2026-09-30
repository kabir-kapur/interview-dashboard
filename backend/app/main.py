import json, os, random, uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import Evaluation, StatusInput, SubmissionInput, TRANSITIONS
from app.services.review_agent import review_submission
from app.services.database import connection, execute, run_migrations
from app.services.auth import require_api_auth
from app.services.scheduler import current_day

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/interview_console.db"
app = FastAPI(title="Interview Console API")


def cors_origins() -> list[str]:
    """Read the browser origins permitted to call this API."""
    configured = os.getenv("CORS_ORIGINS")
    return [origin.strip() for origin in configured.split(",") if origin.strip()] if configured else ["http://localhost:3000"]


app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["*"], allow_headers=["*"])
api = APIRouter(prefix="/api", dependencies=[Depends(require_api_auth)])

def db():
    """Return a transaction for the configured PostgreSQL or local SQLite database."""
    return connection(DB)
def now(): return datetime.now(timezone.utc).isoformat()
def initialize():
    """Ensure the configured database has every known schema migration."""
    run_migrations(DB)


def serialize_problem(row):
    """Convert persisted problem fields into the dashboard response shape."""
    return {
        "id": row["id"], "title": row["title"], "prompt": row["prompt"], "link": row["link"],
        "topics": json.loads(row["topics"]), "difficulty": row["difficulty"], "companies": json.loads(row["companies"]),
        "status": row["status"],
    }


def problems(con):
    """Load the canonical problem bank from the configured database."""
    return [serialize_problem(row) for row in execute(con, "SELECT * FROM problems ORDER BY title").fetchall()]


def serialize_submission(row):
    return None if not row else {"id": row["id"], "problemId": row["problem_id"], "createdAt": row["created_at"], "code": row["code"], "timeComplexity": row["time_complexity"], "spaceComplexity": row["space_complexity"], "explanation": row["explanation"], "evaluation": json.loads(row["evaluation"]) if row["evaluation"] else None}
def choose(bank):
    buckets = {}
    for problem in bank:
        for topic in problem["topics"]: buckets.setdefault(topic, []).append(problem)
    picked = []
    for topic in random.sample(list(buckets), len(buckets)):
        choices = [problem for problem in buckets[topic] if problem not in picked]
        if choices: picked.append(random.choice(choices))
        if len(picked) == 3: break
    return [problem["id"] for problem in picked]
def daily(refresh=False):
    day = current_day()
    with db() as con:
        bank = problems(con); lookup = {item["id"]: item for item in bank}
        row = execute(con, "SELECT ids FROM daily_plans WHERE day=?", (day,)).fetchone(); ids = json.loads(row["ids"]) if row else []
        if refresh or not row or any(item not in lookup for item in ids):
            ids = choose(bank); execute(con, "INSERT INTO daily_plans(day, ids) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET ids=excluded.ids", (day, json.dumps(ids)))
        return {"date": day, "problems": [{**lookup[item], "latestSubmission": serialize_submission(execute(con, "SELECT * FROM submissions WHERE problem_id=? ORDER BY created_at DESC LIMIT 1", (item,)).fetchone())} for item in ids]}

@app.on_event("startup")
def startup(): initialize()
@app.get("/api/health")
def health(): return {"ok": True}
@api.get("/daily")
def get_daily(): return daily()
@api.post("/daily/refresh")
def refresh_daily(): return daily(True)
@api.put("/problems/{problem_id}/status")
def set_status(problem_id: str, body: StatusInput):
    with db() as con:
        row = execute(con, "SELECT status FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not row: raise HTTPException(404, "Problem not found")
        current = row["status"]
        if body.status != "not_started" and body.status not in TRANSITIONS[current]: raise HTTPException(409, "Invalid status transition")
        execute(con, "UPDATE problems SET status=?, status_updated_at=? WHERE id=?", (body.status, now(), problem_id))
    return {"status": body.status}
@api.post("/problems/{problem_id}/submissions")
def create_submission(problem_id: str, body: SubmissionInput):
    submission_id, created = str(uuid.uuid4()), now()
    with db() as con:
        if not execute(con, "SELECT id FROM problems WHERE id=?", (problem_id,)).fetchone(): raise HTTPException(404, "Problem not found")
        execute(con, "INSERT INTO submissions VALUES (?,?,?,?,?,?,?,NULL)", (submission_id, problem_id, created, body.code, body.timeComplexity, body.spaceComplexity, body.explanation))
        execute(con, "UPDATE problems SET status='attempted', status_updated_at=? WHERE id=?", (created, problem_id))
    return {"id": submission_id, "problemId": problem_id, "createdAt": created, **body.model_dump(), "evaluation": None}
@api.post("/submissions/{submission_id}/review")
def request_review(submission_id: str):
    with db() as con:
        row = execute(con, "SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        if not row: raise HTTPException(404, "Submission not found")
        evaluation = review_submission(serialize_submission(row))
        execute(con, "UPDATE submissions SET evaluation=? WHERE id=?", (evaluation.model_dump_json(exclude_none=True), submission_id))
        state = "reviewed_needs_retry" if evaluation.retryRecommended else "reviewed_complete"
        execute(con, "UPDATE problems SET status=?, status_updated_at=? WHERE id=?", (state, now(), row["problem_id"]))
        row = execute(con, "SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
    return serialize_submission(row)


app.include_router(api)
