import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import daily, initialize


def main() -> None:
    """Create today's plan if it does not already exist."""
    initialize()
    plan = daily()
    print(f"Generated {plan['date']} plan with {len(plan['problems'])} problems.")


if __name__ == "__main__":
    main()
