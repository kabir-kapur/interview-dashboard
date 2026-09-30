# Daily digest scheduler

The scheduler runs when the daily digest job is triggered by the deployment platform. It should not depend on a user opening the dashboard.

## Schedule

- Generate the daily plan at **04:00** in `APP_TIMEZONE`.
- SMS delivery is deferred until deployment. The current sender can be invoked manually after a plan exists.
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

`send_daily_digest.py --send` currently performs these steps:

1. Resolve the local date using `APP_TIMEZONE`.
2. Ensure the daily plan exists by invoking the same generate-plan operation.
3. Build the message from the persisted plan and dashboard URL.
4. Send through the configured SMS provider.

There is intentionally no persistence or deduplication for SMS delivery yet. Do not schedule `--send` until we choose how delivery retry behavior should work.

## Initial deployment schedule

```cron
# Create today’s stable plan.
0 4 * * * APP_TIMEZONE=America/Los_Angeles /path/to/backend/.venv/bin/python /path/to/backend/scripts/generate_daily_plan.py

```

Use deployment-managed environment variables for future Twilio credentials. Do not put credentials in a cron line or repository.
