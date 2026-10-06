import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.database import connection, execute
from scripts.populate_problem_bank import collect_problems, normalize_problem, upsert_problems


class ProblemBankTests(unittest.TestCase):
    """Keep the one-shot bank importer deterministic without network access."""

    def test_normalize_problem_keeps_source_metadata(self):
        problem = normalize_problem({"title": "Two Sum", "titleSlug": "two-sum", "difficulty": "Easy", "topicTags": [{"name": "Array"}]})

        self.assertEqual(problem["id"], "two-sum")
        self.assertEqual(problem["topics"], ["Array"])
        self.assertEqual(problem["link"], "https://leetcode.com/problems/two-sum/")

    def test_collect_problems_skips_paid_questions_and_pages_until_full(self):
        calls: list[int] = []

        def fetcher(_limit: int, offset: int) -> list[dict]:
            calls.append(offset)
            return {
                0: [
                    {"title": "Paid", "titleSlug": "paid", "paidOnly": True, "topicTags": []},
                    {"title": "Free one", "titleSlug": "free-one", "paidOnly": False, "topicTags": []},
                ],
                2: [{"title": "Free two", "titleSlug": "free-two", "paidOnly": False, "topicTags": []}],
            }.get(offset, [])

        details = lambda slug: {"questionFrontendId": slug, "content": f"<p>{slug}</p>", "codeSnippets": [{"langSlug": "python3", "code": "class Solution:"}]}
        problems = collect_problems(2, fetcher, details)

        self.assertEqual([problem["id"] for problem in problems], ["free-one", "free-two"])
        self.assertEqual(calls, [0, 2])

    def test_upsert_preserves_status_while_refreshing_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "bank.db"
            original = {"id": "two-sum", "title": "Two Sum", "prompt": "Old", "link": "https://old", "source_id": "1", "starter_code": "class Solution:", "topics": ["Array"], "difficulty": "Easy", "companies": None}
            upsert_problems(database, [original])
            with connection(database) as con:
                execute(con, "UPDATE problems SET status='attempted' WHERE id=?", (original["id"],))
            updated = {**original, "prompt": "New", "topics": ["Hash Table"]}
            upsert_problems(database, [updated])
            with connection(database) as con:
                row = execute(con, "SELECT prompt, topics, status FROM problems WHERE id=?", (original["id"],)).fetchone()

        self.assertEqual(row["prompt"], "New")
        self.assertEqual(row["topics"], '["Hash Table"]')
        self.assertEqual(row["status"], "attempted")

    def test_normalize_problem_sanitizes_html_and_reads_the_python_template(self):
        problem = normalize_problem(
            {"title": "Two Sum", "titleSlug": "two-sum", "difficulty": "EASY", "topicTags": []},
            {"questionFrontendId": "1", "content": "<p>Find <code>two</code> values.</p><script>alert(1)</script>", "codeSnippets": [{"langSlug": "python", "code": "skip"}, {"langSlug": "python3", "code": "class Solution:"}]},
        )

        self.assertEqual(problem["source_id"], "1")
        self.assertEqual(problem["starter_code"], "class Solution:")
        self.assertEqual(problem["difficulty"], "Easy")
        self.assertIn("<code>two</code>", problem["prompt"])
        self.assertNotIn("<script>", problem["prompt"])
