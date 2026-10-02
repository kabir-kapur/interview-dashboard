# Backend scripts

Run scripts from the repository root. They use `DATABASE_URL` when supplied; otherwise they write to the local SQLite database.

## Populate the problem bank

This one-shot importer fetches free LeetCode problem metadata, full sanitized HTML prompts, numeric IDs, and Python 3 starter code. It first applies pending database migrations, then upserts the imported records without changing existing problem statuses.

```sh
DATABASE_URL='your Supabase transaction-pooler URL' \
backend/.venv/bin/python backend/scripts/populate_problem_bank.py --limit 500
```

Keep the connection URL private. Single-quote it so special characters in the password are not interpreted by your shell.

On success it prints `Imported 500 problems into the configured database.` Verify the result in Supabase with:

```sql
SELECT COUNT(*) FROM problems;
SELECT id, source_id, starter_code IS NOT NULL AS has_starter_code
FROM problems
ORDER BY CASE WHEN source_id ~ '^\\d+$' THEN source_id::integer END NULLS LAST
LIMIT 10;
```

Re-running the importer is safe: it updates source metadata by problem ID and preserves each problem's status and submissions.
