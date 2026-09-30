import os
from datetime import datetime
from zoneinfo import ZoneInfo


def current_day() -> str:
    """Return the local calendar date used for daily-plan generation."""
    timezone_name = os.getenv("APP_TIMEZONE", "America/Los_Angeles")
    return datetime.now(ZoneInfo(timezone_name)).date().isoformat()
