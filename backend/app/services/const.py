"""Tunable values shared by backend services."""

DEFAULT_APP_TIMEZONE = "America/Los_Angeles"
DEFAULT_DAILY_PLAN_SIZE = 3
RETRY_PROBLEMS_PER_PLAN = 1
TWILIO_REQUEST_TIMEOUT_SECONDS = 15

# Recommender Constants
BASE_MASTERY_LEARNING_RATE = 0.6
SLOW_SOLVE_MINUTES = 45
OUTCOME_SCORES = {
    "solved_independently": 1.0,
    "solved_independently_slow": 0.7,
    "hint_used": 0.4,
    "gave_up": 0.0,
}

UNSEEN_RECENCY = 1.0
RECENCY_BUCKETS = (
    (6, 0.0),
    (24, 0.1),
    (48, 0.3),
    (72, 0.5),
    (120, 0.7),
)
STALE_RECENCY = 0.9
DIFFICULTY_FIT = {
    "low": {"EASY": 1.0, "MEDIUM": 0.4, "HARD": 0.0},
    "middle": {"EASY": 0.6, "MEDIUM": 1.0, "HARD": 0.3},
    "high": {"EASY": 0.2, "MEDIUM": 0.9, "HARD": 1.0},
}
