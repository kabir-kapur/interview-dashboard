# Database migrations

The application applies numbered `*.sql` files through `app.services.database.run_migrations()` during startup. Applied filenames are recorded in `schema_migrations`, so startup is safe to repeat.

The migrations are deliberately portable between PostgreSQL and the local SQLite fallback. Production uses a `DATABASE_URL` such as `postgresql://...`; without it, the application continues to use `backend/data/interview_console.db`.

Migrations ending in `.postgres.sql` apply only when `DATABASE_URL` points to PostgreSQL. `003_postgres_plan_arrays.postgres.sql` upgrades `daily_plans` to use its native ordered `TEXT[]` `problem_ids` column; SQLite keeps a JSON-text fallback for local testing.

Add future migrations as an immutable, ascending filename (for example, `002_add_review_model.sql`). Test each against an empty PostgreSQL database before deployment. Do not edit an applied migration.
