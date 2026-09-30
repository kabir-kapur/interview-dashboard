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

## Edit the problem bank

Edit `backend/data/problem-bank.csv` in a spreadsheet or text editor, then refresh the browser. Preserve the header row. Separate multiple topics or companies with semicolons.

Problem history, daily plans, statuses, and reviews persist in `backend/data/interview_console.db` by default. Set `DATABASE_URL` to a PostgreSQL connection URL to use a hosted database; numbered migrations in `backend/migrations/` run automatically at API startup.

PostgreSQL uses the `psycopg` driver listed in `backend/requirements.txt`; it is the only added production dependency and is loaded only when `DATABASE_URL` is configured.

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

The review panel supports structured self-review. Its assessment fields are optional so incomplete submissions are not forced into fabricated feedback. The selected daily plan and all problem progress/submissions persist locally.
