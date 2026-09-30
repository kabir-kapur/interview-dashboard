from app.models import Evaluation


def review_submission(_: dict) -> Evaluation:
    """Return a safe placeholder until an LLM-backed reviewer is configured."""
    return Evaluation(
        retryRecommended=True,
        completeness="incomplete",
        notes="Automated review is not configured yet. Try again when the review agent is available.",
    )
