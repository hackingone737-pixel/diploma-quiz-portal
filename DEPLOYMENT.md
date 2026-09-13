# Deployment guide

## Local (Windows + VS Code)

Open the folder in VS Code, then PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Open **http://127.0.0.1:5000**.

Teacher login defaults (local only): `admin` / `admin123`.

## Render / other Gunicorn hosts

Use:

```text
Build: pip install -r requirements.txt
Start: gunicorn app:app
```

Set these environment variables in the host:

```text
SECRET_KEY=<long random value>
TEACHER_USERNAME=<your teacher username>
TEACHER_PASSWORD=<strong teacher password>
COOKIE_SECURE=1
SQLITE_PATH=/var/data/quiz_database.db
```

### Important SQLite note

SQLite is persistent only when the host gives the application a persistent disk/volume. On hosts with ephemeral filesystems, do not use the default local SQLite file for important exam data. Attach a persistent volume and point `SQLITE_PATH` to that volume, or migrate the application to a managed database.

The included `render.yaml` assumes a mounted path at `/var/data`. If your hosting plan does not provide persistent disks, use another database-backed deployment instead.

## First production login

Do not keep `admin` / `admin123` in production. Set `TEACHER_USERNAME` and `TEACHER_PASSWORD` before the first public launch.

## Data safety

The old application used destructive `DROP TABLE` statements. This version does **not** drop tables on startup. It creates the database only when needed and seeds the supplied 50 questions only when there are no exams.
