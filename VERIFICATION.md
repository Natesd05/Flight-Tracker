# Verification record

Executed on September 8, 2026, in this workspace (macOS arm64).

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
