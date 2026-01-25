# Deployment & Run Instructions

## Local (Windows)
- Create venv: `python -m venv .venv`
- Activate: `.venv\\Scripts\\Activate.ps1`
- Install: `pip install -r requirements.txt`
- Env: set `DATABASE_URL=sqlite:///db.sqlite3` for local
- Migrate: `python manage.py migrate`
- Seed (optional): `python run_seeds.py`
- Run dev: `python manage.py runserver 127.0.0.1:8000`

## Local (Unix)
- Activate venv; install requirements
- Migrate and seed
- Run dev: `python manage.py runserver 0.0.0.0:8000`

## Production (Linux)
- Env: `DATABASE_URL`, Redis, Celery beat, `ALLOWED_HOSTS`, `SECRET_KEY`
- Static: `python manage.py collectstatic`
- App: `gunicorn goexplorer.wsgi:application --bind 0.0.0.0:8000`
- Reverse proxy: Nginx with `proxy_pass` to Gunicorn; serve `/static/` via Nginx

## Health & Monitoring
- Add `/healthz` endpoint (simple view) returning 200 OK with version and DB check
- CI pre-step: curl `/healthz` with retries before Playwright

## Test Lifecycle
- Scripts: `scripts/test_server.ps1` and `scripts/test_server.sh` start/stop server for E2E
- DB: `manage.py flush` + `migrate` + deterministic seeds per run
