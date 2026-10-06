"""Authenticated scheduled-job routes."""

from fastapi import APIRouter, Depends

from app.routes.daily_plans import daily
from app.services.cron_auth import require_cron_secret


router = APIRouter()


@router.get("/api/cron/generate-daily-plan", dependencies=[Depends(require_cron_secret)])
def generate_daily_plan():
    """Create today's plan once and return the selected problem IDs."""
    plan = daily()
    return {"date": plan["date"], "problemIds": [problem["id"] for problem in plan["problems"]]}
