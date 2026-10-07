# Daily Interview Console

Single-user interview-prep console: daily LeetCode plans, Python submissions, structured review placeholders, and persisted history. The frontend is Next.js; the API is FastAPI. PostgreSQL/Supabase is used in deployment, with SQLite as the local fallback.

## Run locally

```sh
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/fastapi dev backend/app/main.py
```

In another terminal:

```sh
npm install
npm run dev
```

Set `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` before making authenticated API requests. The frontend runs at `http://localhost:3000`; FastAPI docs are at `http://localhost:8000/docs`.

## Database and problem bank

Set `DATABASE_URL` to a PostgreSQL connection string to use Supabase; otherwise the API uses `backend/data/interview_console.db`. Numbered migrations run when the API starts.

Populate or refresh static LeetCode metadata with the one-shot importer. It writes to the configured database; the deployed app does not depend on LeetCode at runtime.

```sh
DATABASE_URL='your connection URL' backend/.venv/bin/python backend/scripts/populate_problem_bank.py --limit 150
```

## Authentication and deployment

All API routes except `GET /api/health` require HTTP Basic auth. Configure these private environment variables locally and in Vercel:

```text
BASIC_AUTH_USERNAME
BASIC_AUTH_PASSWORD
DATABASE_URL
CORS_ORIGINS=https://your-dashboard.vercel.app
```

Never put API credentials in `NEXT_PUBLIC_` variables. `CORS_ORIGINS` may be a comma-separated list and should include `http://localhost:3000` for local browser development.

`backend/vercel.json` schedules `GET /api/cron/generate-daily-plan` daily at 12:00 UTC. Configure `CRON_SECRET` so only Vercel Cron can invoke it, and set `APP_TIMEZONE` for the local plan date.

## Recommender (in progress)

The recommender will build five-day adaptive plans from concept mastery, exposure, elapsed practice time, difficulty fit, and recent repetition. Concept state is persisted separately from problems; recommendations and automatic learning-state updates are being implemented phase by phase in [`RECOMMENDER_PLAN.md`](RECOMMENDER_PLAN.md).

## Tests

```sh
backend/.venv/bin/python -m unittest discover backend/tests
npm run build
```

## Deferred

- Sandboxed Python 3 execution against test cases. User code must not run in the browser or primary API process.
- Live LLM review/chat and recommendation explainability logging.
