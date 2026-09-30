from typing import Literal

from pydantic import BaseModel

Status = Literal[
    "not_started",
    "attempted",
    "solved",
    "reviewed_needs_retry",
    "reviewed_complete",
]

TRANSITIONS = {
    "not_started": {"attempted"},
    "attempted": {"attempted", "solved", "reviewed_needs_retry", "reviewed_complete"},
    "solved": {"attempted", "reviewed_needs_retry", "reviewed_complete"},
    "reviewed_needs_retry": {"attempted"},
    "reviewed_complete": {"attempted"},
}


class SubmissionInput(BaseModel):
    code: str
    timeComplexity: str | None = None
    spaceComplexity: str | None = None
    explanation: str | None = None


class Evaluation(BaseModel):
    retryRecommended: bool
    completeness: str | None = None
    correctness: str | None = None
    bugsAndEdgeCases: str | None = None
    complexityAnalysis: str | None = None
    reasoningQuality: str | None = None
    betterApproach: str | None = None
    conceptTags: list[str] | None = None
    notes: str | None = None


class StatusInput(BaseModel):
    status: Status
