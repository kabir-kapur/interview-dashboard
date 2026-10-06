"""One-shot importer for a static, locally managed LeetCode problem bank.

Fetches free LeetCode records with their full prompt and Python 3 starter code,
sanitizes and normalizes them, then atomically upserts the result without
resetting any existing problem status.
"""

import argparse
import json
import sys
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import DB
from app.services.database import connection, execute, run_migrations


LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
PAGE_SIZE = 100
ProblemFetcher = Callable[[int, int], list[dict]]
DetailFetcher = Callable[[str], dict]


class PromptSanitizer(HTMLParser):
    """Keep safe, readable prompt markup while dropping scripts and styling."""

    allowed_tags = {"a", "blockquote", "br", "code", "em", "h1", "h2", "h3", "li", "ol", "p", "pre", "strong", "sub", "sup", "table", "tbody", "td", "th", "thead", "tr", "ul"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.allowed_tags:
            return
        href = next((value for name, value in attrs if tag == "a" and name == "href" and value and value.startswith(("https://", "http://"))), None)
        self.parts.append(f'<a href="{escape(href, quote=True)}" target="_blank" rel="noreferrer">' if href else f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.allowed_tags and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(escape(data))


def sanitize_prompt(content: str | None, title: str) -> str:
    """Return safe stored HTML, including a readable fallback without content."""
    if not content:
        return f"<p>Solve {escape(title)}. Open the original problem for the full prompt.</p>"
    parser = PromptSanitizer()
    parser.feed(content)
    return "".join(parser.parts)


def fetch_leetcode_problems(limit: int, offset: int) -> list[dict]:
    """Fetch a page of public LeetCode problem metadata."""
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


def fetch_leetcode_detail(slug: str) -> dict:
    """Fetch the full prompt and Python 3 template for one public problem."""
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        content
        questionFrontendId
        codeSnippets { langSlug code }
      }
    }
    """
    request = Request(
        LEETCODE_GRAPHQL_URL,
        data=json.dumps({"query": query, "variables": {"titleSlug": slug}}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "interview-dashboard-bank-importer/1.0"},
    )
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed public HTTPS endpoint
        body = json.load(response)
    if body.get("errors"):
        raise RuntimeError(f"LeetCode detail query failed for {slug}: {body['errors']}")
    return body["data"]["question"]


def normalize_problem(question: dict, detail: dict | None = None) -> dict:
    """Map public LeetCode data into the console's persisted problem shape."""
    slug = question["titleSlug"]
    return {
        "id": slug,
        "title": question["title"],
        "prompt": sanitize_prompt(detail.get("content") if detail else None, question["title"]),
        "link": f"https://leetcode.com/problems/{slug}/",
        "source_id": (detail or {}).get("questionFrontendId") or question.get("questionFrontendId"),
        "starter_code": next((snippet["code"] for snippet in (detail or {}).get("codeSnippets", []) if snippet["langSlug"] == "python3"), None),
        "topics": [tag["name"] for tag in question.get("topicTags", [])],
        "difficulty": question.get("difficulty", "").title() or None,
        "companies": None,
    }


def collect_problems(limit: int, fetcher: ProblemFetcher = fetch_leetcode_problems, detail_fetcher: DetailFetcher = fetch_leetcode_detail) -> list[dict]:
    """Collect up to `limit` free problems, paging past paid-only records."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    collected: list[dict] = []
    offset = 0
    while len(collected) < limit:
        page = fetcher(PAGE_SIZE, offset)
        if not page:
            break
        collected.extend(normalize_problem(question, detail_fetcher(question["titleSlug"])) for question in page if not question.get("paidOnly", question.get("isPaidOnly")))
        offset += len(page)
    return collected[:limit]


def upsert_problems(database: Path, problems: list[dict]) -> int:
    """Atomically refresh source metadata without resetting existing statuses."""
    run_migrations(database)
    with connection(database) as con:
        for problem in problems:
            execute(
                con,
                """INSERT INTO problems(id, title, prompt, link, source_id, starter_code, topics, difficulty, companies, status, status_updated_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                   ON CONFLICT(id) DO UPDATE SET
                     title=excluded.title, prompt=excluded.prompt, link=excluded.link,
                     source_id=excluded.source_id, starter_code=excluded.starter_code,
                     topics=excluded.topics, difficulty=excluded.difficulty, companies=excluded.companies""",
                (
                    problem["id"], problem["title"], problem["prompt"], problem["link"], problem["source_id"], problem["starter_code"],
                    json.dumps(problem["topics"]), problem["difficulty"],
                    json.dumps(problem["companies"]) if problem["companies"] else None,
                ),
            )
    return len(problems)


def main() -> None:
    """Fetch, normalize, and atomically persist a static free problem bank."""
    parser = argparse.ArgumentParser(description="Import free public LeetCode problems into the bank.")
    parser.add_argument("--limit", type=int, default=150, help="Number of free problems to import (default: 150).")
    args = parser.parse_args()
    problems = collect_problems(args.limit)
    count = upsert_problems(DB, problems)
    print(f"Imported {count} problems into the configured database.")


if __name__ == "__main__":
    main()
