# Database migrations

The application no longer creates tables during startup. Apply Alembic migrations
from the `backend` directory after installing `requirements.txt`:

```powershell
.\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

Set `DATABASE_URL` in the environment or in the ignored local `.env` file first.
The application loads `backend/.env` directly regardless of the current working
directory. Keep that local file out of version control and configure the
database and evaluation settings there. A fresh database is created by the
bootstrap migration. The bootstrap has a fixed schema snapshot: it creates
missing tables and does not drop or rewrite existing tables.

For an existing database, take a verified backup first. The `upgrade head`
command creates only missing tables, adds only missing evaluation/completion
columns, and checks for duplicate feedback before adding the
one-feedback-per-answer unique constraint. Duplicates stop the migration
without deleting rows. Missing legacy foreign keys are added only after an
orphan-reference check; orphaned rows stop the migration. Review the actual PostgreSQL schema and row counts
before rollout, then compare it with the SQLAlchemy models using `alembic check`.
Do not stamp a database to a revision unless its schema has been inspected and
verified.

If an existing `answers` table belongs to the older `questions`/`interviews`
schema rather than the current `interview_questions`/`interview_sessions`
schema, the evaluation migration renames it to `legacy_answers` and the linked
feedback table to `legacy_feedback`, then creates the current tables. Existing
rows and their original columns are preserved in those archive tables; they are
not silently associated with unrelated new interview sessions.

The bootstrap baseline's downgrade is intentionally a no-op so an initial
rollback never drops application tables. The evaluation revision also retains
its additive columns on downgrade to avoid data loss. Rolling back application
code is therefore safe; dropping tables or columns requires a separate,
explicitly reviewed data-retention decision.

Useful commands:

```powershell
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini check
python -m alembic -c alembic.ini downgrade -1
python -m alembic -c alembic.ini upgrade head
```
