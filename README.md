# Student Flight Planner

A React + FastAPI application that ranks round-trip flights around a student's classes, budget, and travel preferences. PostgreSQL stores the demo profile, recurring classes, schedule exceptions, searches, evaluations, and saved itineraries.

## Run with Docker Compose

Install Docker Desktop or Docker Engine with Compose v2, then run from this directory:

```sh
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5173**. API documentation: **http://localhost:8000/docs**. Health: **http://localhost:8000/api/health**.

The backend runs Alembic migrations and an idempotent seed automatically. No API credentials are needed. The default provider is deterministic **mock data**, prominently labeled in the UI. These fares are illustrative and cannot be booked. All services bind to localhost. Docker uses the configured PostgreSQL credentials and overrides `DATABASE_URL` to use the internal `db` host.

```sh
docker compose exec backend python -m app.seed  # preserves existing profile and classes
docker compose down                           # stops services; retains database volume
```

This is a **single shared demo student profile without authentication**. Run locally. Authentication, multi-user isolation, booking, and payments are outside this MVP.

## Try the product

1. Open **My schedule**. Add recurring classes; click a class to edit or delete it. Add a cancellation for a matching class date or a one-time extra class.
2. Open **Preferences**. Save your class timezone, airport, campus transit, airport buffer, budget, round-trip extras, travel windows, and ranking priorities.
3. Open **Find flights**. Choose airports and flexible dates (up to four dates in each range). Set days away and optional hard constraints. The default next-Friday-to-Sunday ORD–LAX search produces six varied demo options.
4. Run the search. Sort or filter results, inspect **Why this flight**, and save options. Adjust priorities and search again to rerank. Changed inputs are marked as requiring a new search.
5. Open **Saved flights**. Select up to three checkboxes for a comparison table. Saved evaluations are snapshots; changing your preferences does not rewrite them.

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

Vite proxies `/api` to `127.0.0.1:8000`. Docker serves the compiled frontend with nginx and proxies the same path to FastAPI. The application needs no runtime frontend secrets. Fonts use Google Fonts with local sans-serif fallbacks; flight data and application functionality do not depend on that service.

## Architecture

```text
frontend/src/
  App.tsx           planner views and coordinated UI state
  components.tsx    accessible forms, flight cards, score details
  api.ts / types.ts HTTP client and frontend contracts
  styles.css        responsive theme and layouts
backend/app/
  main.py           validated REST endpoints and consistent errors
  schemas.py        Pydantic request and response contracts
  db.py             SQLAlchemy models and PostgreSQL sessions
  engine.py         pure evaluation and ranking functions
  timeutils.py      timezone and daylight-saving rules
  providers/        provider protocol, mock and optional Duffel adapter
  seed.py           idempotent demo setup
backend/alembic/     versioned PostgreSQL migration
backend/tests/      engine, provider contract, and PostgreSQL integration tests
frontend/tests/     desktop and mobile end-to-end flows
```

The database uses relational tables, foreign keys, indexed ownership and search references, timezone-aware audit timestamps, and JSONB for validated preference/schedule payloads and immutable provider/evaluation snapshots. Saving the same option from the same search is idempotent via a unique constraint. A saved option must reference an actual evaluated search result; clients cannot submit their own prices or scores. Search records also retain the preferences and schedule used during evaluation.

## Recommendation rules

All prices are USD for one adult in economy. Estimated total is **provider round-trip airfare + round-trip baggage estimate + all ground transportation estimate**, rounded to cents. Each extra is counted once. Baggage and transport are user estimates, not provider quotes; set baggage to zero when already included in the fare. Lodging, meals, seat selection, and other optional charges are not included.

Hard constraints are applied **before** ranking:

- Total estimated cost must be within budget, if selected.
- No class conflicts, if selected.
- Both directions must meet the local departure/arrival windows, if selected.
- Maximum stops applies **per direction**, when selected.
- Minimum/maximum days away always apply. Days away means elapsed time from leaving home to returning home, divided by 24, not calendar dates or destination nights.

Classes conflict with the full interval from outbound departure minus home transit and airport buffer through final return arrival plus home transit. This includes the entire stay at the destination and inbound journey. Recurrences use Monday=0 through Sunday=6 in the profile's IANA timezone. A class ending earlier than it starts continues into the following day. Intersections use half-open intervals: returning exactly at class start is not a conflict. Concurrent class overlaps are unioned so missed minutes aren't double-counted; individual affected classes still appear in the explanation.

Cancellations remove a specific recurrence on its start date; extra classes add a one-time interval. For fall-back DST ambiguity, class starts use the earliest instant and ends the latest, conservatively accounting for possible conflicts. For nonexistent spring-forward times, shift forward by the transition gap (02:30 becomes 03:30 for a one-hour gap). Elapsed durations are calculated in UTC.

Preferred windows apply to first departure and final arrival of **each direction**, using airport-local time (four checks). An overnight window such as 21:00–06:00 is supported; equal endpoints mean the full day. Connecting flight departure times do not create additional window penalties.

Total travel minutes = outbound elapsed journey (including layovers) + inbound elapsed journey (including layovers) + two home transit estimates + two airport arrival buffers. Destination ground-transit time and post-arrival baggage/immigration queues are not modeled. Update the home transit estimate if using a different origin airport. Total days away includes the destination stay; total travel time excludes it.

The normalized penalties, each clamped to [0, 1], are:

| Factor | Penalty | Default weight |
| --- | --- | --- |
| Cost | total / budget | 35 |
| Classes | union of missed minutes / 180 | 30 |
| Layovers | total stops across both directions / 4 | 10 |
| Travel windows | failed endpoint window checks / 4 | 10 |
| Travel time | total travel minutes / 1440 | 15 |

**Score = 100 × (1 − sum(weight × penalty) / sum(weights)).** Higher is better. Weights are nonnegative, at least one must be positive. Scores are rounded to two decimals. Ties break by lower estimated cost, shorter travel time, then stable itinerary ID. The UI's per-factor bars show `100 × (1 − penalty)`; they are not each factor's weighted contribution. Absolute normalization keeps scores stable when unrelated candidates are added. Normalization thresholds are MVP heuristics, not a learned model. Costs above budget saturate the cost penalty when budget is a soft preference.

No-match responses report failed hard-constraint counts and specific suggestions. One itinerary can fail more than one constraint. The engine never silently relaxes a constraint.

## REST API

All routes below are under `/api`. Swagger UI at `/docs` documents request/response schemas.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | PostgreSQL connectivity and selected provider |
| GET | `/airports` | Supported airport and IANA timezone catalog |
| GET / PUT | `/preferences` | Read/replace demo profile preferences |
| GET | `/schedule` | Recurring classes and exceptions |
| POST | `/classes` | Add recurring class |
| PUT / DELETE | `/classes/{id}` | Edit/delete recurring class (deletion cascades cancellations) |
| POST | `/exceptions` | Add cancellation or extra class |
| DELETE | `/exceptions/{id}` | Remove exception |
| POST | `/searches` | Fetch, evaluate, rank, and persist options |
| GET | `/searches` | Ten most recent search snapshots |
| GET | `/searches/{id}` | Retrieve one search |
| GET / POST | `/saved` | List/save evaluated options |
| DELETE | `/saved/{id}` | Remove saved option |

Errors use `{ "error": { "message": "...", "details": [...] } }`; `details` appears on validation errors. Unknown records return 404, invalid requests 422, provider failures 502, database failures 503. Request logs include method, path, status, and duration, without request bodies or API credentials.

## Optional Duffel provider

The adapter implements [Duffel v2 offer requests](https://duffel.com/docs/api/v2/offer-requests) and maps [offer responses](https://duffel.com/docs/api/v2/offers) into the same ranking pipeline. Set `FLIGHT_PROVIDER=duffel` and `DUFFEL_ACCESS_TOKEN` to your Duffel test access token, then restart the backend. Token type determines test/live mode; results are labeled using the provider response. No order or payment endpoints are used.

Queries are limited to 16 date pairs, one adult in economy, and up to two connections per direction. Requests run sequentially, with a 10-second airline timeout and a 25-second HTTP timeout. Airport timezones come from Duffel. Returned fares must be USD: configure your Duffel organisation accordingly. Non-USD fares, missing timezones, intermediate technical stops, malformed offers, missing credentials, and provider failures return explicit errors instead of misrepresenting results or switching to mock data. Local searches offer 14 supported origin/destination airports; Duffel connections may use any valid provider-supplied IANA zone.

Extras remain user estimates. Provider access, quotas, charges, coverage, and currency configuration depend on your Duffel account. Simulated HTTP contract tests pass, but **no credential-based Duffel call has been verified**. Test offers are not live inventory. The default mock provider needs no account.

## Environment variables

| Variable | Default / meaning |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URL; local default in `.env.example` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Compose database configuration; demo defaults `planner`, `planner`, `flightplanner` |
| `CORS_ORIGINS` | Comma-separated local frontend origins |
| `FLIGHT_PROVIDER` | `mock` (default) or `duffel` |
| `DUFFEL_ACCESS_TOKEN` | Required only for Duffel; use a test token for development |
| `TEST_DATABASE_URL` | Dedicated PostgreSQL database whose name ends in `_test` |
| `E2E_BASE_URL` | Running frontend URL, default `http://127.0.0.1:5173` |

Backend local commands load `../.env` when run from `backend/`; environment variables take precedence. Docker injects values directly. No real secrets are committed.

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

See `VERIFICATION.md` for the checks executed in this workspace and any limitations.
