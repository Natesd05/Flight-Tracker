# Development

[Back to the README](../README.md)

## Local development without Docker

Requires Python 3.11+ (tested on 3.13), Node 22+ (tested on 24), and PostgreSQL 17.

In this workspace, isolated runtimes were installed in `.venv` and `.postgres`, with application and test databases on port 55432. After stopping any existing app servers, `./scripts/dev-local.sh` restarts that local setup. This helper is specific to the prepared workspace; Docker Compose remains the portable setup. The helper leaves PostgreSQL running after the app stops; stop it with `.postgres/bin/pg_ctl -D .pgdata stop`.

Create two PostgreSQL databases with an appropriate local account: `flightplanner` and `flightplanner_test`. Keep the test database separate. Set `DATABASE_URL` and `TEST_DATABASE_URL` to your connection strings; SQLAlchemy uses `postgresql+psycopg://` URLs.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock.txt
cp .env.example .env
# Edit DATABASE_URL in .env to point to your PostgreSQL instance.
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.seed
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Vite proxies `/api` to `127.0.0.1:8000`. Docker serves the compiled frontend with nginx and proxies the same path to FastAPI. The application needs no runtime frontend secrets. The UI uses system fonts and has no external font requests.

## Verification

```sh
# Engine, provider, and isolated PostgreSQL integration tests with Docker:
docker compose --profile test run --build --rm tests

# Without Docker, from backend/:
TEST_DATABASE_URL=postgresql+psycopg://planner:planner@localhost:5432/flightplanner_test ../.venv/bin/pytest -q

# Frontend type-check and production build:
cd frontend
npm ci
npm run build

# With backend + frontend running, and Google Chrome installed:
npm run test:e2e
```

Integration tests apply actual Alembic migrations and roll each test back, including application commits. They refuse to use a database not ending in `_test`; without `TEST_DATABASE_URL` they are explicitly skipped. Browser tests run in temporary Chrome profiles at desktop and mobile viewport sizes; they restore preferences, remove their added classes/saved options, and retain search history. They test edit class → save preferences → search → ranking details → save → compare → reload, plus no-match explanations and horizontal overflow. Screenshots and failure traces go to `frontend/test-results/` (ignored by Git).

See [VERIFICATION.md](../VERIFICATION.md) for the checks executed in this workspace and any limitations.

The protected demo adds two access-control browser cases (one per viewport).
They run when `E2E_AUTH_PASSWORD` is set; otherwise they explicitly skip. Set
`E2E_AUTH_USERNAME` (default `demo`) and `E2E_BASE_URL` for a protected staging
instance. `E2E_ALLOW_SELF_SIGNED=true` is only for local certificates. See the
[deployment runbook](deployment.md) for setup and acceptance checks.
