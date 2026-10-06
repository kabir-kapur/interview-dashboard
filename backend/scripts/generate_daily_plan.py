import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.routes.daily_plans import daily
from app.services.database import run_migrations


def main() -> None:
    """Create today's plan if it does not already exist."""
    run_migrations(config.DB)
    plan = daily()
    print(f"Generated {plan['date']} plan with {len(plan['problems'])} problems.")


if __name__ == "__main__":
    main()
