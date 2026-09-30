# Database migrations

The application applies numbered `*.sql` files through `app.services.database.run_migrations()` during startup. Applied filenames are recorded in `schema_migrations`, so startup is safe to repeat.

`001_initial.sql` is deliberately portable between PostgreSQL and the local SQLite fallback. Production uses a `DATABASE_URL` such as `postgresql://...`; without it, the application continues to use `backend/data/interview_console.db`.

Add future migrations as an immutable, ascending filename (for example, `002_add_review_model.sql`). Test each against an empty PostgreSQL database before deployment. Do not edit an applied migration.
