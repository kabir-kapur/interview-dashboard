"""Submission-review routes."""

from fastapi import APIRouter, HTTPException

from app.routes._shared import db, now, serialize_submission
from app.services.database import execute
from app.services.review_agent import review_submission


router = APIRouter()


@router.post("/submissions/{submission_id}/review")
def request_review(submission_id: str):
    """Run the current review stub and persist its structured result."""
    with db() as con:
        row = execute(con, "SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Submission not found")
        evaluation = review_submission(serialize_submission(row))
        execute(con, "UPDATE submissions SET evaluation=? WHERE id=?", (evaluation.model_dump_json(exclude_none=True), submission_id))
        state = "reviewed_needs_retry" if evaluation.retryRecommended else "reviewed_complete"
        execute(con, "UPDATE problems SET status=?, status_updated_at=? WHERE id=?", (state, now(), row["problem_id"]))
        row = execute(con, "SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
    return serialize_submission(row)
