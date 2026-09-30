import csv, json, random, uuid
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
DB, BANK = ROOT / "data/interview_console.db", ROOT / "data/problem-bank.csv"
app = FastAPI(title="Interview Console API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
api = APIRouter(prefix="/api", dependencies=[Depends(require_api_auth)])

def db():
    """Return a transaction for the configured PostgreSQL or local SQLite database."""
    return connection(DB)
def now(): return datetime.now(timezone.utc).isoformat()
def values(text): return [item.strip() for item in text.split(";") if item.strip()]
def problems():
    with BANK.open(newline="") as file:
        return [{**row, "link": row["link"] or None, "topics": values(row["topics"]), "companies": values(row["companies"])} for row in csv.DictReader(file)]
def initialize():
    """Ensure the configured database has every known schema migration."""
    run_migrations(DB)
def status(con, problem_id):
    row = execute(con, "SELECT status FROM progress WHERE problem_id=?", (problem_id,)).fetchone(); return row["status"] if row else "not_started"
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
    bank = problems(); lookup = {item["id"]: item for item in bank}; day = current_day()
    with db() as con:
        row = execute(con, "SELECT ids FROM plans WHERE day=?", (day,)).fetchone(); ids = json.loads(row["ids"]) if row else []
        if refresh or not row or any(item not in lookup for item in ids):
            ids = choose(bank); execute(con, "INSERT INTO plans(day, ids) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET ids=excluded.ids", (day, json.dumps(ids)))
        return {"date": day, "problems": [{**lookup[item], "status": status(con, item), "latestSubmission": serialize_submission(execute(con, "SELECT * FROM submissions WHERE problem_id=? ORDER BY created_at DESC LIMIT 1", (item,)).fetchone())} for item in ids]}

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
    if problem_id not in {item["id"] for item in problems()}: raise HTTPException(404, "Problem not found")
    with db() as con:
        current = status(con, problem_id)
        if body.status != "not_started" and body.status not in TRANSITIONS[current]: raise HTTPException(409, "Invalid status transition")
        execute(con, "INSERT INTO progress(problem_id, status, updated_at) VALUES (?, ?, ?) ON CONFLICT(problem_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at", (problem_id, body.status, now()))
    return {"status": body.status}
@api.post("/problems/{problem_id}/submissions")
def create_submission(problem_id: str, body: SubmissionInput):
    if problem_id not in {item["id"] for item in problems()}: raise HTTPException(404, "Problem not found")
    submission_id, created = str(uuid.uuid4()), now()
    with db() as con:
        execute(con, "INSERT INTO submissions VALUES (?,?,?,?,?,?,?,NULL)", (submission_id, problem_id, created, body.code, body.timeComplexity, body.spaceComplexity, body.explanation))
        execute(con, "INSERT INTO progress(problem_id, status, updated_at) VALUES (?, 'attempted', ?) ON CONFLICT(problem_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at", (problem_id, created))
    return {"id": submission_id, "problemId": problem_id, "createdAt": created, **body.model_dump(), "evaluation": None}
@api.post("/submissions/{submission_id}/review")
def request_review(submission_id: str):
    with db() as con:
        row = execute(con, "SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        if not row: raise HTTPException(404, "Submission not found")
        evaluation = review_submission(serialize_submission(row))
        execute(con, "UPDATE submissions SET evaluation=? WHERE id=?", (evaluation.model_dump_json(exclude_none=True), submission_id))
        state = "reviewed_needs_retry" if evaluation.retryRecommended else "reviewed_complete"
        execute(con, "INSERT INTO progress(problem_id, status, updated_at) VALUES (?, ?, ?) ON CONFLICT(problem_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at", (row["problem_id"], state, now()))
        row = execute(con, "SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
    return serialize_submission(row)


app.include_router(api)
