"""Deterministic concept-learning updates derived from submissions."""

from math import sqrt

from app import config
from app.services.database import execute


def outcome_score(completion_state: str | None, time_taken_minutes: int | None) -> float | None:
    """Map the available deterministic attempt outcome to a normalized score."""
    if completion_state == "solved_independently":
        if time_taken_minutes is not None and time_taken_minutes >= config.SLOW_SOLVE_MINUTES:
            return config.OUTCOME_SCORES["solved_independently_slow"]
        return config.OUTCOME_SCORES[completion_state]
    return config.OUTCOME_SCORES.get(completion_state)


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
            learning_rate = config.BASE_MASTERY_LEARNING_RATE / sqrt(concept["exposure_count"] + 1)
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
