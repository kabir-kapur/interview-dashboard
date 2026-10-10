"""Problem-detail, status, and submission routes."""

import uuid

from fastapi import APIRouter, HTTPException

from app.models import StatusInput, SubmissionInput, TRANSITIONS
from app.routes._shared import db, now, problem_detail
from app.services.database import execute
from app.services.learning import outcome_score, update_concept_learning


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
    """Store an attempt, then update learning state for its linked concepts."""
    submission_id, created = str(uuid.uuid4()), now()
    score = outcome_score(body.completionState, body.timeTakenMinutes)
    with db() as con:
        if not execute(con, "SELECT id FROM problems WHERE id=?", (problem_id,)).fetchone():
            raise HTTPException(404, "Problem not found")
        execute(
            con,
            """INSERT INTO submissions (id, problem_id, created_at, code, time_complexity, space_complexity, explanation, completion_state, time_taken_minutes, outcome_score, evaluation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
            (submission_id, problem_id, created, body.code, body.timeComplexity, body.spaceComplexity, body.explanation, body.completionState, body.timeTakenMinutes, score),
        )
        update_concept_learning(con, problem_id, score, created)
        execute(con, "UPDATE problems SET status='attempted', status_updated_at=? WHERE id=?", (created, problem_id))
    return {"id": submission_id, "problemId": problem_id, "createdAt": created, **body.model_dump(), "outcomeScore": score, "evaluation": None}
