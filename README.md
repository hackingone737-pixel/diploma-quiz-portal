# Diploma Quiz Portal

A modern Flask online MCQ examination system for diploma students.

## Included

- Student PIN + name login
- Multiple exams
- 50 seeded MCQs from the supplied project
- Random question order per attempt
- Server-side exam deadline
- Automatic submission after the time limit
- One attempt per student PIN per exam
- Teacher login and dashboard
- Create/publish/unpublish exams
- Add and delete questions
- Student result screen
- CSV-friendly result table in the teacher dashboard
- SQLite for local development
- PostgreSQL support through `DATABASE_URL` for production
- `/health` endpoint for hosting health checks
- Production Gunicorn configuration

## Local Windows setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Open: http://127.0.0.1:5000

Default teacher credentials for local development are `admin` / `admin123`. **Change these before deployment.**

## Important database behavior

The application uses `db.create_all()` and seeds the 50 supplied questions **only when the database has no exams**. It does not run destructive `DROP TABLE` statements on startup.

For production, set `DATABASE_URL` to a persistent PostgreSQL database. This avoids relying on an ephemeral server filesystem.

## Production environment variables

- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — long random secret
- `TEACHER_USERNAME` — teacher username
- `TEACHER_PASSWORD` — strong teacher password
- `EXAM_DURATION_MINUTES` — default duration for the seeded exam

## Deploying to a Python-capable host

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
gunicorn app:app
```

Set all production environment variables in the host dashboard. Do not commit `.env` or passwords to GitHub.

## Render

The included `render.yaml` contains the web-service build/start/health-check configuration. Connect a persistent PostgreSQL provider, set `DATABASE_URL`, and set the teacher credentials as environment variables.

## Security notes

This is an educational assessment application, not a high-stakes examination platform. It includes server-side timing, session-based authentication and one-attempt checks, but a production college deployment should additionally consider rate limiting, HTTPS-only cookies, stronger student authentication, audit logs, backups, and an external identity provider.


## Offline PDF Quiz Generator (4 GB PCs)

The teacher dashboard now includes an **Offline PDF Quiz Generator**. Upload any text-based/selectable PDF, enter its unit/subject name, choose 1-50 questions, and the app extracts definitions/facts locally and saves generated MCQs to the selected exam. It does not use an online API or a downloaded LLM, so it is suitable for low-storage/4 GB RAM machines. Scanned image-only PDFs need OCR or a text-based copy.
