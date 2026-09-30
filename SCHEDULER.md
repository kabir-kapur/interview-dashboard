# Daily digest scheduler

The scheduler runs when the daily digest job is triggered by the deployment platform. It should not depend on a user opening the dashboard.

## Schedule

- Generate the daily plan at **04:00** in `APP_TIMEZONE`.
- Send the SMS digest at the chosen notification time, initially recommended as **09:00** in the same timezone.
- The deployment scheduler (cron, platform scheduler, or worker) triggers the commands; the FastAPI web process does not keep its own timer.

## Generate-plan job

`generate_daily_plan.py` performs these steps:

1. Resolve the current local date using `APP_TIMEZONE`.
2. Look up the existing daily plan for that date.
3. If one exists, return it unchanged.
4. Otherwise, use the scheduler selection policy to choose topic-diverse problems.
5. Persist the plan before returning success.

This makes repeated triggers safe. A redeploy or scheduler retry cannot replace a user's established daily plan.

## Send-digest job

`send_daily_digest.py --send` should perform these steps:

1. Resolve the local date using `APP_TIMEZONE`.
2. Ensure the daily plan exists by invoking the same generate-plan operation.
3. Check whether a successful `sms_daily_digest` delivery record already exists for that date.
4. If delivered already, exit successfully without sending another message.
5. Build the message from the persisted plan and dashboard URL.
6. Send through the configured SMS provider.
7. Persist the provider message ID and delivery timestamp on success.
8. On a transient provider failure, return a non-zero exit code so the deployment scheduler can retry.

## Persistence to add before enabling `--send`

Add a `digest_deliveries` SQLite table:

```text
date              TEXT
channel           TEXT         # e.g. sms_daily_digest
status            TEXT         # sent | failed
provider_message_id TEXT NULL
attempted_at      TEXT
sent_at           TEXT NULL
error_message     TEXT NULL

PRIMARY KEY (date, channel)
```

The `(date, channel)` key prevents duplicate sends when a job overlaps, retries, or is invoked manually. Store failed attempts too, but only treat `sent` as a deduplication success.

## Initial deployment schedule

```cron
# Create today’s stable plan.
0 4 * * * APP_TIMEZONE=America/Los_Angeles /path/to/backend/.venv/bin/python /path/to/backend/scripts/generate_daily_plan.py

# Send the already-created plan.
0 9 * * * APP_TIMEZONE=America/Los_Angeles /path/to/backend/.venv/bin/python /path/to/backend/scripts/send_daily_digest.py --dashboard-url https://your-dashboard.example --send
```

Use deployment-managed environment variables for Twilio credentials. Do not put credentials in the cron line or repository.
