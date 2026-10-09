# October 8, 2026 update

Personal accounts now replace the shared profile in the app. Sign up or log in to access your own schedule, preferences, searches, and saved flights. Existing legacy demo data is preserved in profile 1 and is not assigned to a new user. New accounts receive four starter classes, Monday–Thursday. Sunday appears first; one-time changes expand on click; optional recurring classes are excluded from conflict scoring and hard conflict filters.

Browser location requests are opt-in. Distances are straight-line, calculated locally using an OurAirports coordinate snapshot; recommendations are limited to the 49 supported major airports. The selected home airport is saved with preferences, not the coordinates. Driving distances and transit estimates are not inferred.

Run `./scripts/dev-local.sh` to apply the new `0002` migration and start the app. Hosted deployments still have the existing shared Basic Auth gate in addition to personal app accounts. No public deployment was performed. Password reset and email verification are not implemented.

The September 23 handoff below is historical and describes the previous shared-profile release.

---

# FlightPlanner handoff

Updated September 23, 2026.

## Current state

FlightPlanner is a React, FastAPI and PostgreSQL flight-planning demo. It uses
the built-in sample-flight provider by default. Sample fares are illustrative and
are not bookable. There is no booking, payment or sign-in flow. The app has one
shared profile, so everyone using a deployed demo sees the same schedule,
preferences and saved flights.

The selected hosting target is a $0 demo using Render Free for the app and Neon
Free for PostgreSQL. No cloud service has been published yet, and no paid
resource has been created.

## Verified

- 59 backend tests pass against the isolated PostgreSQL test database.
- The frontend TypeScript check and production build pass.
- Eight desktop/mobile Playwright tests pass against the hosted-style local app.
- The hosted-style app applies migrations, seeds the profile, serves the built
  frontend and API together, protects pages/API with Basic Authentication, and
  rejects cross-origin writes.
- `render.yaml` validates against Render’s Blueprint schema.
- Neon-style PostgreSQL URLs are accepted and normalized for psycopg 3 while
  preserving SSL query parameters.
- `git diff --check` passes.

## Files for the free deployment

- [render.yaml](../render.yaml): one Render Free web service.
- [Dockerfile.render](../Dockerfile.render): builds the frontend and backend
  into one image.
- [backend/app/hosted.py](../backend/app/hosted.py): access gate and static/API
  hosting wrapper.
- [backend/app/start_hosted.py](../backend/app/start_hosted.py): migration,
  seed and server startup command.
- [docs/free-demo.md](free-demo.md): the complete Render/Neon setup guide.
- [docs/deployment.md](deployment.md): alternative Docker-server deployment.

## Remaining deployment steps

1. Commit and push the current repository to the GitHub repository connected to
   Render. Deploy the current revision, including `render.yaml` and
   `Dockerfile.render`; an older archive will not work.
2. In Neon, create a Free PostgreSQL project and copy its SSL-enabled connection
   string. Keep it private.
3. In Render, create a Blueprint from the repository and select the Free plan.
4. Supply the Neon connection string as `DATABASE_URL` when Render prompts for
   it. Keep `FLIGHT_PROVIDER=mock`.
5. Let Render generate `DEMO_PASSWORD`. Save it privately; the login username is
   `demo`.
6. Review the generated `onrender.com` URL and approve the initial deployment.
7. Test the URL: anonymous requests should receive 401 except `/healthz`;
   authenticated requests should load the planner, report PostgreSQL/mock health,
   save a class and save a flight, then retain those changes after reload.

Render Free sleeps after 15 minutes of inactivity and may take about one minute
to wake. Neon Free has storage, compute and transfer quotas. This is suitable
for a temporary demo, not guaranteed continuous production availability.

## Credentials and safety

Never commit or paste the Neon connection string or Render password. Do not add
a Duffel token: this deployment intentionally uses sample data and does not
need a flight-provider account. Keep `DATABASE_URL` and `DEMO_PASSWORD` in
Render’s secret environment settings. Do not add a payment method if you want
to stay at $0.

## Useful checks

From `backend/`:

```sh
TEST_DATABASE_URL=postgresql+psycopg://planner@127.0.0.1:55432/flightplanner_test ../.venv/bin/pytest -q
```

From `frontend/`:

```sh
npm run build
```

For hosted browser verification, set `E2E_BASE_URL`, `E2E_AUTH_USERNAME=demo`,
`E2E_AUTH_PASSWORD` and `E2E_PUBLIC_LIVENESS=true`, then run:

```sh
npx playwright test
```

Keep Playwright traces private because authenticated requests may appear in
test artifacts.

## Known limitations

- Render and Neon accounts are not connected to this workspace.
- Docker Engine is unavailable locally, so the Render image and public startup
  still need to run in Render.
- Public HTTPS, Render wake behavior, Neon connectivity and persistence across
  a Render restart remain unverified.
- The shared profile is intentionally protected by one shared password rather
  than individual accounts.

Start with [docs/free-demo.md](free-demo.md), then complete the seven remaining
steps above.
