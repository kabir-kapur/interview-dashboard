"""Problem-detail, status, and submission routes."""

import uuid

from fastapi import APIRouter, HTTPException

from app.models import StatusInput, SubmissionInput, TRANSITIONS
from app.routes._shared import db, now, problem_detail
from app.services.database import execute


router = APIRouter()


@router.get("/problems/{problem_id}")
def get_problem(problem_id: str):
    """Return a problem and its most recent submission."""
    with db() as con:
        return problem_detail(con, problem_id)


@router.put("/problems/{problem_id}/status")
def set_status(problem_id: str, body: StatusInput):
    """Set a problem status when the state-machine transition is valid."""
    with db() as con:
        row = execute(con, "SELECT status FROM problems WHERE id=?", (problem_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Problem not found")
        current = row["status"]
        if body.status != "not_started" and body.status not in TRANSITIONS[current]:
            raise HTTPException(409, "Invalid status transition")
        execute(con, "UPDATE problems SET status=?, status_updated_at=? WHERE id=?", (body.status, now(), problem_id))
    return {"status": body.status}


@router.post("/problems/{problem_id}/submissions")
def create_submission(problem_id: str, body: SubmissionInput):
    """Store an attempt and mark its problem as attempted."""
    submission_id, created = str(uuid.uuid4()), now()
    with db() as con:
        if not execute(con, "SELECT id FROM problems WHERE id=?", (problem_id,)).fetchone():
            raise HTTPException(404, "Problem not found")
        execute(con, "INSERT INTO submissions VALUES (?,?,?,?,?,?,?,NULL)", (submission_id, problem_id, created, body.code, body.timeComplexity, body.spaceComplexity, body.explanation))
        execute(con, "UPDATE problems SET status='attempted', status_updated_at=? WHERE id=?", (created, problem_id))
    return {"id": submission_id, "problemId": problem_id, "createdAt": created, **body.model_dump(), "evaluation": None}
