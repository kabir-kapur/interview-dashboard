"""Small runtime configuration shared by the API routes."""

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/interview_console.db"

# Learning updates favor early evidence and reduce the impact of broad problems.
BASE_MASTERY_LEARNING_RATE = 0.6
SLOW_SOLVE_MINUTES = 45
OUTCOME_SCORES = {
    "solved_independently": 1.0,
    "solved_independently_slow": 0.7,
    "hint_used": 0.4,
    "gave_up": 0.0,
}


def cors_origins() -> list[str]:
    """Read the browser origins permitted to call this API."""
    configured = os.getenv("CORS_ORIGINS")
    return [origin.strip() for origin in configured.split(",") if origin.strip()] if configured else ["http://localhost:3000"]
