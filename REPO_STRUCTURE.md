# Repository structure

```text
.
├── frontend/                 # Next.js React client
│   ├── app/                  # Thin page composition and global styles
│   ├── components/           # Dashboard, workspace, submission, and review UI
│   └── lib/                  # API client and frontend data types
├── backend/
│   ├── app/main.py           # FastAPI routes and application persistence calls
│   ├── app/models/           # Typed API models and status state machine
│   ├── app/services/database.py # SQLite fallback/PostgreSQL connection and migration runner
│   ├── app/services/sms.py    # Twilio digest composition and delivery
│   ├── app/services/scheduler.py # Local-time daily scheduling support
│   ├── migrations/            # Ordered SQL schema and seed migrations
│   ├── scripts/               # Deployment-oriented command-line utilities
│   └── tests/                 # Backend model and API unit tests
├── package.json              # Frontend workspace scripts
├── SCHEDULER.md              # Daily plan and digest execution design
├── README.md           # Local run instructions and behavior
└── REPO_STRUCTURE.md   # This repository map
```

## Application layout

- `problems` is the canonical problem bank, seeded by migrations and editable in Supabase's Table Editor.
- The backend scheduler samples across distinct topic buckets and is the intended extension point for spaced repetition or weak-topic weighting.
- Daily plans and submissions use PostgreSQL when `DATABASE_URL` is configured, with SQLite retained as the local fallback.
- `Problem.status` is the dashboard source of truth: `not_started`, `attempted`, `solved`, `reviewed_needs_retry`, or `reviewed_complete`.
- Submission evaluations have a required `retryRecommended` decision and optional assessment fields. Saving a review keeps that decision synchronized with the displayed reviewed status.

## Future extension points

- Replace `scheduler.selectProblems` with weighted or spaced-repetition selection.
- Add problem types alongside coding problems for system design.
- Add independent route/page modules for the recruiting pipeline and calendar digest.
