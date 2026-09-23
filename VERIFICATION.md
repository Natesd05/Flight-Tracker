# Verification record

## September 23, 2026 — Render Free / Neon Free adaptation

Prepared `render.yaml` and `Dockerfile.render` for one free web service serving
both the production frontend and FastAPI. Added a password gate covering pages,
assets, API and API docs, with a public minimal `/healthz` endpoint that does not
query Neon. Cross-origin writes are rejected. Startup validates the password,
origin, static build, database URL and sample-only provider before migrations.
Standard Neon PostgreSQL URIs are normalized to psycopg 3 without losing SSL
parameters. See [free-demo.md](docs/free-demo.md) for the selected $0 path.

Executed after this adaptation:

- **59 backend tests passed**, no skips, including real PostgreSQL integration
  tests and new access-control/configuration regressions.
- **Frontend type-check and production build passed.**
- **8 desktop/mobile Playwright tests passed** against `app.start_hosted` on
  loopback port 18000, the production static build and the isolated
  `flightplanner_demo_e2e_test` database. This exercised the new Python gate,
  public liveness endpoint, protected health/API, cross-origin checks and full
  planner workflow. This run used local HTTP; public HTTPS remains Render's
  responsibility and is not yet verified.
- Startup applied migrations and seeded the test database successfully.
- `render.yaml` passed JSON Schema validation against the schema downloaded
  from `https://render.com/schema/render.yaml.json`. Confirmed exactly one
  service on `plan: free` and no Render database resources.
- `git diff --check` passed. The temporary hosted process was stopped.

Still pending: account connection, source publication to the linked GitHub
repository, actual Neon connectivity, Render's Docker build, deployment and
public acceptance checks. Docker Engine is absent locally. The Neon plugin was
suggested but is not yet installed/connected; no Render API key was supplied.
Browser control was unavailable. No cloud resources or paid services were
created and no site was published. The earlier portable archive does not
contain this adaptation; use the current repository source.

## September 23, 2026 — final sample-demo handoff

The full backend suite was rerun after removing the Duffel setup requirement:
**47 passed, no skips** against `flightplanner_test`. The count dropped by one
because the secret helper no longer accepts or validates a Duffel token. The
existing Starlette/AnyIO warning remains. No application UI or ranking changes
were made after the previously passing frontend build and eight browser checks.

A portable source archive was prepared from the current tracked and untracked
non-ignored project files. It excludes Git metadata, local environment values,
secret files, databases, virtual environments, dependencies and test artifacts.
It includes the Dockerfiles, lockfiles, standalone Compose file and runbook.
The extracted deployment configuration was checked with the Compose CLI.
Docker Engine is still absent here; container build/startup and public hosting
need a Docker-capable server and selected hostname. No deployment or spending
has been authorized or performed.

## September 23, 2026 — sample-data deployment selected

The user chose not to use Duffel. Local `.env` now selects `mock`; the hosted
Compose configuration fixes the provider to `mock`, removes the Duffel secret,
and the setup helper no longer asks for a token. The deployment runbook no
longer treats Duffel validation as a prerequisite. The optional adapter code
remains unused; sample searches do not make flight-provider API requests.

Rechecked after this change: both secret-helper tests passed, and the Compose
configuration parsed successfully. Its resolved backend provider stayed `mock`
even with `FLIGHT_PROVIDER=duffel` in the invoking environment, and no Duffel
secret was defined. Prior full-suite results below remain historical; only
these relevant checks were rerun for this setup-only change. Docker startup
and hosted acceptance remain unverified. No paid resources were provisioned.

## September 23, 2026 — protected demo preparation

Executed in this workspace on macOS arm64. No deployment was published.

### Passed

- **48 backend tests**, with no skips, using the dedicated PostgreSQL
  `flightplanner_test` database. Command from `backend/`:
  `TEST_DATABASE_URL=postgresql+psycopg://planner@127.0.0.1:55432/flightplanner_test ../.venv/bin/pytest -q`.
  Includes actual migrations and schema comparison, provider regressions,
  mounted-secret loading, and secret-file permissions/no-overwrite behavior.
- **TypeScript check and Vite production build**: `npm run build`.
- **8 Playwright tests passed** (four desktop, four mobile Chrome emulation).
  All six existing planning cases passed plus two proxy-access cases. Tests
  covered anonymous page/API denial, authenticated health, cross-origin and
  cross-site write rejection, class/preference persistence, ranking explanations,
  saved comparisons, sorting/filtering and layout overflow.
- Browser checks used the production `frontend/dist` build, the actual FastAPI
  app on port 18000, and a separate `flightplanner_demo_e2e_test` database.
  Caddy 2.11.4 served a temporary local HTTPS endpoint with an internal test
  certificate; no root certificate was installed in the system trust store.
  Desktop/mobile results screenshots were visually inspected.
- The deployment Caddy configuration was exercised with only local hostname,
  secret-path, certificate and upstream substitutions. A native Caddy static/API
  server stood in for the nginx container. This does **not** verify the nginx
  image or Docker networking. Initial test-harness failures (upstream Host
  matching and inherited Playwright credentials) were corrected before the
  final passing run.
- Empty proxy auth secrets returned 401 for both anonymous and credentialed
  requests. Missing auth secret files failed Caddy validation. Authentication
  remains in the Caddyfile, outside the imported credential file.
- Both `compose.yaml` and standalone `compose.demo.yaml` passed
  `docker-compose config --quiet` with the official standalone Compose 2.39.4
  CLI downloaded to a temporary directory. No Docker engine was installed.
- Native PostgreSQL `pg_dump -Fc` and `pg_restore --no-owner --exit-on-error`
  succeeded from the browser-test database into the separate
  `flightplanner_demo_restore_test` database; the restored profile count was one.
  This verifies a local backup/restore drill, not the Docker runbook commands.
- `git diff --check` passed. The existing Starlette/AnyIO deprecation warning
  remains; tests pass.

### Prepared changes

- Duffel mode flags are strictly boolean; mismatched routes/dates and malformed
  nested responses are rejected. The hosted configuration enforces test tokens
  and test offers, while local mock mode remains available.
- `python -m app.verify_duffel` performs one credential-based, search-only smoke
  check using future dates and prints a summary without exposing tokens or
  saving raw offers. Its missing-token refusal was executed successfully; no
  provider request was made.
- `compose.demo.yaml`, `deploy/Caddyfile`, `.env.deploy.example` and the secret
  preparation helper provide HTTPS, password protection, private internal
  services, mounted secret files, persistent database/certificate volumes,
  readiness checks, restart policies and bounded container logs.
- [Deployment runbook](docs/deployment.md) includes setup, approval boundary,
  hosted acceptance checks, backup/restore, updates and credential rotation.

### Still unverified / blocked

- **Credential-based Duffel validation:** `DUFFEL_ACCESS_TOKEN` was absent. A
  secure local test-token configuration was requested; no token value was
  printed. Account access, actual inventory, currency and real response
  variations remain unverified. Simulated contract tests are not a substitute.
- **Docker startup:** Docker Engine was unavailable. No container builds or
  Compose service startup were executed. Run the deployment build, validation
  and startup steps on a Docker-capable server before calling it deployed.
- **Public hosting:** no server, hostname or paid resource was provisioned.
  Public DNS, certificates, external port isolation and server restart recovery
  remain acceptance steps. No individual accounts or booking/payment flows were
  added; access is a shared demo password protecting a shared profile.

The temporary verification servers were stopped after testing. Existing app
data was not modified; the separate verification databases remain available.

## Historical record — September 8, 2026

The sections below describe the earlier execution and runtime state, not the
current availability of local preview URLs.

## Interface and documentation revision

Rechecked on September 8, 2026 after the design and copy changes:

- TypeScript check and Vite production build passed.
- All six existing Playwright tests passed in desktop and mobile Chrome emulation. They cover class editing, preferences, search explanations, saved comparisons, persistence, filters, and horizontal overflow.
- Inspected the generated desktop/mobile results and desktop comparison screenshots.
- Updated existing assertions for the revised headings. No dependencies or backend behavior changed; the backend suite was not rerun for this revision.
- The README now links to `docs/development.md` and `docs/engineering.md`; the detailed setup and ranking rules are retained there.

## Original implementation checks

- **33 backend tests** with Python 3.13.9 against PostgreSQL 17.11. Command from `backend/`:
  ```sh
  TEST_DATABASE_URL=postgresql+psycopg://planner@127.0.0.1:55432/flightplanner_test ../.venv/bin/pytest -q
  ```
- Actual Alembic upgrade on both the application and isolated test database. Migration metadata matches the SQLAlchemy ORM. Demo seed is idempotent.
- Engine tests cover deterministic mock data, date-pair coverage, cost and travel-time accounting, hard constraints, weights, stable ties, overnight classes, one-time changes, time away at the destination, partial overlaps, interval boundaries, overlap union, different class/airport timezones, spring-forward gaps and fall-back folds, timezone-offset input rejection, and no-result explanations.
- PostgreSQL integration tests cover class CRUD, preferences, cancellations, cascade deletion, search snapshots, saved-option idempotency, server-validated itinerary ownership, persistence after preference changes, errors, and rollback isolation.
- Duffel contract tests use `httpx.MockTransport` to verify request construction, offer mapping, operating carrier, test-mode labeling, UTC offsets, non-USD rejection, missing timezone errors, and HTTP 401/429/500 handling. No provider fallback on errors.
- **Frontend type-check and production build passed** using Node 24.13.1 and Vite 6.4.3 (`cd frontend && npm run build`). Final bundle: approximately 236 KB JavaScript / 72 KB gzip and 20 KB CSS / 5 KB gzip.
- **6 Playwright tests passed** in installed Google Chrome using temporary profiles: three flows at a 1440×1100 desktop viewport and three at an iPhone 13 viewport. Mobile means Chromium device emulation, not real-device Safari verification.
- Browser flow: add class → edit class → save budget → search mock flights → open ranking explanation → save two flights → compare side by side → reload and verify persistence.
- Additional browser cases: no-match explanations, comparison limited to three selections, re-enabling selection after deselection, cost sorting, filtering to zero results, clearing filters, and no page-level horizontal overflow.
- No JavaScript page errors during the main smoke flow.
- Desktop/mobile result and comparison screenshots inspected. Date inputs were adjusted to fit the search panel; navigation anchoring and screenshot scroll position were corrected.
- Compose YAML parsed successfully, with database readiness checks and an isolated test service. This is a configuration check, not container execution.
- npm installation audit reported zero vulnerabilities.

## Current local preview

- Frontend: http://127.0.0.1:5173
- API and Swagger docs: http://127.0.0.1:8000/docs
- Isolated PostgreSQL: 127.0.0.1:55432
- App database: `flightplanner`; test database: `flightplanner_test`.
- App servers and PostgreSQL were left running. The app defaults to the mock provider. Browser tests restored original preferences and removed their added classes/saved options. Their search snapshots remain in recent history.
- Restart the prepared local runtime with `./scripts/dev-local.sh` after stopping existing app servers. See README for portable Docker setup and manual development commands.

## Not verified / limitations

- **Docker images and Docker Compose startup were not executed**: Docker is not installed in this environment. The underlying frontend build, FastAPI server, PostgreSQL migrations, API, and integrated browser flow were exercised directly.
- **No credential-based Duffel requests were executed**: no Duffel access token was available. The adapter is based on current official documentation and simulated contract tests; account access, currency settings, inventory, and real-provider response variations remain unverified.
- Native computer-control browser access was unavailable. Browser QA used an approved isolated Playwright/Chrome process instead.
- One third-party deprecation warning remains from Starlette's use of an AnyIO test portal alias. Tests pass; it does not affect the running application.
- No authentication or production deployment is included. The app intentionally uses one local demo profile and no booking/payment flows.

Initial verification attempts encountered sandbox network/process restrictions and a browser-test configuration issue. Dependencies and local server execution were approved, the harness was configured for installed Chrome, and the final applicable checks all passed. Screenshots live in `frontend/test-results/` and are intentionally ignored by Git.
