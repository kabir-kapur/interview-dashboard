# Daily Interview Console

A local Next.js + FastAPI POC for daily coding-interview preparation.

## Run

Start the API:

```sh
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/fastapi dev backend/app/main.py
```

In a second terminal, start the frontend:

```sh
npm install
npm run dev
```

Open `http://localhost:3000`. The interactive FastAPI docs are at `http://localhost:8000/docs`.

## Test

```sh
backend/.venv/bin/python -m unittest discover backend/tests
```

## Problem bank and persistence

Problems, daily plans, statuses, and submissions persist in the configured database. The initial migration seeds a small bank; edit it through Supabase's Table Editor until an admin page and bank-populator CLI are added.

Set `DATABASE_URL` to a PostgreSQL connection URL to use a hosted database; numbered migrations in `backend/migrations/` run automatically at API startup. Without it, the app uses `backend/data/interview_console.db` locally.

PostgreSQL uses the `psycopg` driver listed in `backend/requirements.txt`; it is the only added production dependency and is loaded only when `DATABASE_URL` is configured.

To populate the bank with static public LeetCode metadata, run the one-shot importer. It saves the resulting data to the configured database; after that, the dashboard does not depend on LeetCode at runtime. Re-running it refreshes metadata but preserves each problem's status.

```sh
DATABASE_URL='your Supabase connection URL' backend/.venv/bin/python backend/scripts/populate_problem_bank.py --limit 150
```

## API authentication

All API routes except `GET /api/health` require HTTP Basic authentication. Set `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` as private environment variables locally and in Vercel. The API fails closed with a configuration error if either value is missing. The frontend asks for those credentials once and keeps the resulting header only in browser session storage.

For deployment, set `CORS_ORIGINS` to your frontend URL, for example `https://your-dashboard.vercel.app`. You may provide multiple comma-separated URLs for preview deployments. Do not expose API credentials through `NEXT_PUBLIC_` environment variables.

## Daily plan schedule

The plan generator is idempotent: it creates the configured local day's plan only if one does not already exist. Schedule it at 4:00 AM in the deployment's scheduler, with `APP_TIMEZONE` set to your preferred IANA timezone (default: `America/Los_Angeles`):

```sh
backend/.venv/bin/python backend/scripts/generate_daily_plan.py
```

For a traditional cron host, run `0 4 * * *` followed by that command. Schedule SMS delivery separately at the time you actually want the notification.

## SMS daily digest

The SMS sender uses Twilio. Copy `.env.example` to your deployment's private environment and set the Twilio API key, sender, and destination values in E.164 format. Twilio recommends API keys and environment variables for production credentials. [Twilio SMS guide](https://www.twilio.com/docs/messaging/tutorials/how-to-send-sms-messages)

Preview today's message without sending anything:

```sh
backend/.venv/bin/python backend/scripts/send_daily_digest.py --dashboard-url https://your-dashboard.example
```

After deployment, run the same command with `--send` from a daily scheduler. This is the only path that sends an SMS.

## Status model

`not_started` → `attempted` → `solved` → `reviewed_needs_retry` or `reviewed_complete`.

A new submission can move any active problem back to `attempted`. A review must include the required retry decision; it sets the matching reviewed status.

## Scope

The review panel displays structured agent feedback. Its assessment fields are optional so incomplete submissions are not forced into fabricated feedback. Daily plans, problems, and submissions persist in the configured database.

## Deferred work

- Add a separately deployed, sandboxed Python 3 execution service to run a submission against test cases before review. Do not execute user code in the frontend or the primary API process.
