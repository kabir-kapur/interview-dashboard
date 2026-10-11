"""Deterministic learning updates and derived recommender inputs."""

from datetime import UTC, datetime
from math import sqrt

from app.services.const import (
    BASE_MASTERY_LEARNING_RATE,
    DIFFICULTY_FIT,
    OUTCOME_SCORES,
    RECENCY_BUCKETS,
    SLOW_SOLVE_MINUTES,
    STALE_RECENCY,
    UNSEEN_RECENCY,
)
from app.services.database import execute


def outcome_score(completion_state: str | None, time_taken_minutes: int | None) -> float | None:
    """Map the available deterministic attempt outcome to a normalized score."""
    if completion_state == "solved_independently":
        if time_taken_minutes is not None and time_taken_minutes >= SLOW_SOLVE_MINUTES:
            return OUTCOME_SCORES["solved_independently_slow"]
        return OUTCOME_SCORES[completion_state]
    return OUTCOME_SCORES.get(completion_state)


def update_concept_learning(con: object, problem_id: str, score: float | None, practiced_at: str) -> None:
    """Record one submission against every linked concept with equal attribution."""
    concepts = execute(
        con,
        """SELECT concepts.id, concepts.mastery, concepts.exposure_count
           FROM problem_concepts JOIN concepts ON concepts.id=problem_concepts.concept_id
           WHERE problem_concepts.problem_id=?""",
        (problem_id,),
    ).fetchall()
    if not concepts:
        return

    attribution = 1 / len(concepts)
    for concept in concepts:
        values = [concept["exposure_count"] + 1, practiced_at, concept["id"]]
        if score is not None:
            learning_rate = BASE_MASTERY_LEARNING_RATE / sqrt(concept["exposure_count"] + 1)
            mastery = concept["mastery"] + (learning_rate * attribution * (score - concept["mastery"]))
            values.insert(0, mastery)
            execute(
                con,
                "UPDATE concepts SET mastery=?, exposure_count=?, recency=? WHERE id=?",
                tuple(values),
            )
        else:
            execute(
                con,
                "UPDATE concepts SET exposure_count=?, recency=? WHERE id=?",
                tuple(values),
            )


def calculate_recency(last_practiced_at: datetime | str | None, now: datetime) -> float:
    """Return an overdue-practice value from one persisted practice timestamp."""
    if last_practiced_at is None:
        return UNSEEN_RECENCY
    practiced_at = _as_utc(last_practiced_at)
    hours_since_practice = max(0, (_as_utc(now) - practiced_at).total_seconds() / 3600)
    for max_hours, value in RECENCY_BUCKETS:
        if hours_since_practice < max_hours:
            return value
    return STALE_RECENCY


def calculate_problem_recency(concepts: list[dict], now: datetime) -> float | None:
    """Average concept recency for one problem without mutating persisted state."""
    if not concepts:
        return None
    return sum(calculate_recency(concept.get("recency"), now) for concept in concepts) / len(concepts)


def calculate_problem_mastery_gap(concepts: list[dict]) -> float | None:
    """Average the remaining mastery gap across a problem's concepts."""
    if not concepts:
        return None
    return sum(1 - concept["mastery"] for concept in concepts) / len(concepts)


def calculate_difficulty_fit(difficulty: str | None, average_mastery: float | None) -> float | None:
    """Return the configured difficulty fit for a problem's aggregate mastery."""
    if difficulty not in {"EASY", "MEDIUM", "HARD"} or average_mastery is None:
        return None
    band = "low" if average_mastery < 0.3 else "middle" if average_mastery < 0.7 else "high"
    return DIFFICULTY_FIT[band][difficulty]


def calculate_problem_features(problem: dict, now: datetime) -> dict[str, float] | None:
    """Derive the Phase 3 inputs for one problem; do not rank or persist them."""
    concepts = problem.get("concepts", [])
    recency = calculate_problem_recency(concepts, now)
    mastery_gap = calculate_problem_mastery_gap(concepts)
    difficulty_fit = calculate_difficulty_fit(problem.get("difficulty"), 1 - mastery_gap if mastery_gap is not None else None)
    if recency is None or mastery_gap is None or difficulty_fit is None:
        return None
    return {"recency": recency, "masteryGap": mastery_gap, "difficultyFit": difficulty_fit}


def _as_utc(value: datetime | str) -> datetime:
    """Parse stored timestamps and treat legacy naive values as UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
