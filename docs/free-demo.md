# $0 demo: Render Free + Neon Free

This is the selected deployment path. `render.yaml` defines one **Free** web
service. `Dockerfile.render` builds the React frontend and serves it alongside
FastAPI in one container. PostgreSQL lives in Neon; no paid Render database,
persistent disk, custom domain or flight-provider subscription is needed.

The Linux-server instructions in `deployment.md` remain an alternative, not a
requirement for this free setup. The earlier source archive predates this
adaptation; deploy the current repository files instead.

## Prepare Neon

1. In your Neon account, confirm you are on the **Free** plan. Create a project
   named `flightplanner-demo`, with a database such as `neondb` and PostgreSQL 17.
2. Choose a region near the Render service (its default region is Oregon).
3. Open **Connect**, select the database and owner role, disable connection
   pooling for this small demo, and copy the PostgreSQL connection string.
   Keep its SSL parameters. The app converts `postgresql://` to its psycopg 3
   driver automatically. The same connection runs the migrations on startup.
4. Keep the connection string in a secret manager or the Render secret field.
   Never put it in Git, chat, screenshots or the Blueprint itself.

Creating an account does not connect it to this workspace. For agent-assisted
setup, connect the Neon plugin, or configure the database secret directly in
Render. Render API access is optional; the dashboard flow below works without it.

## Review before publishing

The current source changes must be committed and pushed to the repository
connected to Render before it can build them. The configured remote is
`https://github.com/Natesd05/Flight-Tracker.git`. Do not deploy the older revision
that lacks `render.yaml`, `Dockerfile.render` and `backend/app/hosted.py`.

The intended access policy is: a public HTTPS address with a shared password
protecting every page and API endpoint. Only `/healthz`, a minimal `ok` response,
is public for Render's health checks. All signed-in viewers share one profile.

Before applying the Blueprint, review and approve publication of this protected
demo. No paid plan or add-on is authorized. Selecting **Deploy/Apply** starts the
initial deployment even though automatic future deployments are disabled.

## Render dashboard deployment

1. Use the free/Hobby workspace and connect the GitHub repository containing
   the reviewed source. Choose **New → Blueprint** and that repository/branch.
2. Render should find `render.yaml`. Confirm exactly one web service named
   `flightplanner-demo`, with plan **Free**, Docker runtime and no disks or
   Render databases. Do not upgrade a workspace or add a payment method.
3. Enter the Neon connection string when prompted for `DATABASE_URL`.
4. The Blueprint generates `DEMO_PASSWORD` automatically. After creation, view
   it only in the service's environment settings; store it privately. The
   username is `demo`. The app refuses to start with a password shorter than
   16 characters, without an origin, without a database URL, or with a provider
   other than `mock`.
5. After the publishing approval, apply the Blueprint. Render builds the image,
   runs migrations and seeds the initial profile, then serves the app at its
   `https://...onrender.com` address. No domain purchase is needed.
6. Open that address, enter the demo credentials and verify the planning flow.

Render provides `PORT` and `RENDER_EXTERNAL_URL`; do not replace them. The latter
is used to reject cross-origin browser writes. If you later use a different
public hostname, configure and test the origin handling before sharing it.
`autoDeployTrigger: "off"` prevents future pushes from publishing automatically.

## Acceptance checks

- `/healthz` returns `ok` without touching the database, so health polling does
  not itself keep Neon's compute awake.
- `/`, `/api/health`, `/api/schedule`, `/docs` and static assets require the
  password. Wrong or missing credentials return 401.
- After login, `/api/health` reports PostgreSQL and provider `mock`.
- Add a class, search sample flights and save an option. Verify persistence
  after a browser reload and after a service restart.
- Test the page on desktop and mobile. The automated mock-data suite can run
  against an isolated staging profile with `E2E_BASE_URL`, `E2E_AUTH_USERNAME`,
  `E2E_AUTH_PASSWORD` and `E2E_PUBLIC_LIVENESS=true`. Do not bypass HTTPS
  certificate validation on the public site.

Basic auth credentials can appear in test traces; keep those artifacts private.
The browser caches the login, so password rotation is the way to revoke shared
access. Change `DEMO_PASSWORD` in Render and redeploy to rotate it.

## Free-tier boundaries

Render Free sleeps after 15 minutes without incoming traffic and can take about
a minute to wake. Its filesystem is ephemeral, so all saved application data
must stay in Neon. With no payment method, Render suspends services or builds
when applicable free quotas are exhausted instead of billing overages. Do not
configure uptime pings to defeat sleeping. External-database traffic also counts
toward Render's free-service restrictions.

Neon's Free plan has storage, compute and transfer quotas. Keep the account on
Free, monitor usage, and do not approve an upgrade. Search snapshots accumulate
in PostgreSQL; a frequently used demo may eventually need deliberate cleanup or
a fresh demo database. Free hosting is suitable for this demo, not a promise of
continuous availability. Keep protected database exports if the data matters.

Sources checked September 23, 2026:
[Render Free limits](https://render.com/docs/free),
[Blueprint fields](https://render.com/docs/blueprint-spec),
[Neon Free plan](https://neon.com/blog/how-to-make-the-most-of-neons-free-plan).
