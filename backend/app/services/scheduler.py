import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.const import DEFAULT_APP_TIMEZONE, DEFAULT_DAILY_PLAN_SIZE, RETRY_PROBLEMS_PER_PLAN


def current_day() -> str:
    """Return the local calendar date used for daily-plan generation."""
    timezone_name = os.getenv("APP_TIMEZONE", DEFAULT_APP_TIMEZONE)
    return datetime.now(ZoneInfo(timezone_name)).date().isoformat()


def generate_plan_ids(candidates: list[dict], size: int = DEFAULT_DAILY_PLAN_SIZE) -> list[str]:
    """Choose a small daily set: one retry first, then unseen, topic-diverse work."""
    retries = [item for item in candidates if item.get("status") == "reviewed_needs_retry"]
    unseen = [item for item in candidates if item.get("status", "not_started") == "not_started"]
    fallback = [item for item in candidates if item not in retries and item not in unseen]

    picked = _pick_topic_diverse(retries, min(RETRY_PROBLEMS_PER_PLAN, size))
    picked.extend(_pick_topic_diverse(unseen, size - len(picked), picked))
    picked.extend(_pick_topic_diverse(fallback, size - len(picked), picked))
    return [item["id"] for item in picked]


def _pick_topic_diverse(candidates: list[dict], count: int, picked: list[dict] | None = None) -> list[dict]:
    """Favor a new topic without excluding untagged or duplicate-topic problems."""
    selected = list(picked or [])
    available = list(candidates)
    while available and len(selected) - len(picked or []) < count:
        used_topics = {topic for item in selected for topic in item["topics"]}
        preferred = [item for item in available if not set(item["topics"]) & used_topics]
        choice = random.choice(preferred or available)
        selected.append(choice)
        available.remove(choice)
    return selected[len(picked or []):]
