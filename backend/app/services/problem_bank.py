"""Import public problem metadata into the persisted problem bank."""

import json
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

from app.services.database import connection, execute, run_migrations


LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
PAGE_SIZE = 100
ProblemFetcher = Callable[[int, int], list[dict]]


def fetch_leetcode_problems(limit: int, offset: int) -> list[dict]:
    """Fetch one page of public LeetCode problem metadata."""
    query = f"""
    query {{
      problemsetQuestionListV2(limit: {limit}, skip: {offset}) {{
        questions {{
          title
          titleSlug
          difficulty
          paidOnly
          topicTags {{ name }}
        }}
      }}
    }}
    """
    request = Request(
        LEETCODE_GRAPHQL_URL,
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "interview-dashboard-bank-importer/1.0"},
    )
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed public HTTPS endpoint
        body = json.load(response)
    if body.get("errors"):
        raise RuntimeError(f"LeetCode query failed: {body['errors']}")
    return body["data"]["problemsetQuestionListV2"]["questions"]


def normalize_problem(question: dict) -> dict:
    """Map one public question into the console's stable problem shape."""
    slug = question["titleSlug"]
    return {
        "id": slug,
        "title": question["title"],
        "prompt": f"Solve {question['title']}. Open the linked LeetCode problem for the full prompt.",
        "link": f"https://leetcode.com/problems/{slug}/",
        "topics": [tag["name"] for tag in question.get("topicTags", [])],
        "difficulty": question.get("difficulty", "").title() or None,
        "companies": None,
    }


def collect_problems(limit: int, fetcher: ProblemFetcher = fetch_leetcode_problems) -> list[dict]:
    """Collect up to `limit` free questions, paging through paid questions."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    collected: list[dict] = []
    offset = 0
    while len(collected) < limit:
        page = fetcher(PAGE_SIZE, offset)
        if not page:
            break
        collected.extend(normalize_problem(question) for question in page if not question.get("paidOnly", question.get("isPaidOnly")))
        offset += len(page)
    return collected[:limit]


def upsert_problems(sqlite_path: Path, problems: list[dict]) -> int:
    """Save imported metadata without resetting a user's existing problem status."""
    run_migrations(sqlite_path)
    with connection(sqlite_path) as con:
        for problem in problems:
            execute(
                con,
                """INSERT INTO problems(id, title, prompt, link, topics, difficulty, companies, status, status_updated_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                   ON CONFLICT(id) DO UPDATE SET
                     title=excluded.title, prompt=excluded.prompt, link=excluded.link,
                     topics=excluded.topics, difficulty=excluded.difficulty, companies=excluded.companies""",
                (
                    problem["id"], problem["title"], problem["prompt"], problem["link"],
                    json.dumps(problem["topics"]), problem["difficulty"],
                    json.dumps(problem["companies"]) if problem["companies"] else None,
                ),
            )
    return len(problems)
