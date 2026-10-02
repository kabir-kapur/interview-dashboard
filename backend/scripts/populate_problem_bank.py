"""One-shot CLI for importing a static LeetCode-backed problem bank."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import DB
from app.services.problem_bank import collect_problems, upsert_problems


def main() -> None:
    """Fetch public metadata once and persist it in the configured database."""
    parser = argparse.ArgumentParser(description="Import free public LeetCode problems into the bank.")
    parser.add_argument("--limit", type=int, default=150, help="Number of free problems to import (default: 150).")
    args = parser.parse_args()
    problems = collect_problems(args.limit)
    count = upsert_problems(DB, problems)
    print(f"Imported {count} problems into the configured database.")


if __name__ == "__main__":
    main()
