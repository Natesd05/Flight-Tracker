# Protected demo deployment

For the selected $0 Render/Neon setup, use [free-demo.md](free-demo.md).
This document covers the alternative single-server deployment.

This is a prepared deployment, not a published site. It keeps the existing
React/FastAPI/PostgreSQL architecture on a Docker-capable Linux server. The
standalone `compose.demo.yaml` publishes only Caddy on TCP ports 80 and 443.
The frontend, API and database have no published host ports. Caddy provides
HTTPS and a shared demo password for every page and API request. All admitted
visitors still share the same schedule, preferences and saved flights.

The deployment is fixed to sample flight data and needs no flight-provider
account, token or paid API. Sample fares are illustrative and are not live
prices or bookable inventory. Nothing books or pays for flights. Do not put private personal schedules in a shared demo.

## Prepare the server (no publication)

Use a maintained Linux server with Docker Engine, the Docker Compose plugin,
and Python 3 installed. Choose a domain, point its DNS at the server, and allow
inbound TCP 80/443 for HTTPS issuance and serving. Keep SSH restricted to the
administrator. No particular cloud provider or paid resource has been selected.

Copy the repository to the server without local `.env`, `.pgdata`, `.postgres`,
`.venv`, `node_modules`, or test output. Run these commands at its root:

```sh
cp .env.deploy.example .env.deploy
# Edit DEMO_DOMAIN to the hostname only, e.g. flights.your-domain.com.

# Prompts for a demo password without putting it in shell history.
docker run --rm -it caddy:2-alpine caddy hash-password

# Paste the resulting bcrypt hash at the hidden prompt, not the raw password.
python3 scripts/prepare-demo-secrets.py

docker compose --env-file .env.deploy -f compose.demo.yaml config --quiet
docker compose --env-file .env.deploy -f compose.demo.yaml build
docker compose --env-file .env.deploy -f compose.demo.yaml run --rm --no-deps proxy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

The helper generates a random database password and matching URL, stores files
with mode 0600 in a mode-0700 directory, and refuses to overwrite existing
secrets. The ignored `deploy/secrets/` directory must remain only on the server
or in a secure backup. Compose mounts only the required secrets into each
service. These are local files, not an encrypted cloud secret store; protect
the host and backups. Do not add the secrets to images, Git or chat.

The required files are `database_password`, `database_url`,
and `demo_auth` (one line:
`demo <bcrypt hash>`). A missing auth file prevents startup; an empty file
leaves authentication enabled with no valid users. Keep the auth directive in
`deploy/Caddyfile` itself. Environment variables override Pydantic secret files,
so do not add a `DATABASE_URL` environment entry to the hosted backend.

## Flight data

The demo uses the built-in sample provider, which makes no external flight API
requests. No Duffel setup or validation is required. Hosting is a separate
choice and may carry server/domain costs; no paid resources have been created.

## Publish only after approval

Review the intended hostname, server/provider cost, and access policy (anyone
given the shared demo password). Then approve starting the deployment:

```sh
docker compose --env-file .env.deploy -f compose.demo.yaml up -d --build --wait --wait-timeout 180
docker compose --env-file .env.deploy -f compose.demo.yaml ps
```

The backend applies migrations and the idempotent seed on startup. Database,
backend and frontend health checks gate dependent services. The proxy is checked
externally because the real acceptance check needs HTTPS and authentication.
Restart policies recover exited containers; Docker health status alone does not
restart an unhealthy but still-running process. Configure external monitoring.

Verify these manually against the real hostname:

- HTTP redirects to HTTPS and the browser accepts the certificate.
- Without credentials, `/`, `/api/health`, `/api/schedule` and `/healthz` return
  401. A wrong password must also fail.
- With user `demo` and the chosen password, `/api/health` returns database and
  provider status; the planner loads and saves changes across a restart.
- No externally accessible 5432, 8000 or 5173 port bypasses the gate.

For automated acceptance, use an isolated **mock-mode staging instance**. The
suite edits a shared profile and retains search history. It restores its
preferences, classes and saved options but should not run against real users:

```sh
cd frontend
npm ci
export E2E_BASE_URL=https://your-staging-hostname
export E2E_AUTH_USERNAME=demo
# Set E2E_AUTH_PASSWORD through your secret manager or a hidden shell prompt.
npx playwright test
unset E2E_AUTH_PASSWORD
```

`E2E_ALLOW_SELF_SIGNED=true` is for local test certificates only. Do not use it
for hosted acceptance. Tests require installed Google Chrome. Test artifacts
can contain credentials in HTTP traces: keep them local, and delete or protect
them after inspection. Share credentials with trusted viewers through a secure
channel. Basic authentication is browser-cached and has no application logout;
close the browser session to clear it or rotate the password to revoke access.

## Persistence, backup and updates

Named volumes retain PostgreSQL data and Caddy certificates across container
recreation and ordinary `down`. Never use `down -v` on a demo whose data matters.
A volume is not a backup. Before an update, save a database dump outside the
container, then copy it to protected storage off the server:

```sh
mkdir -p backups
chmod 700 backups
umask 077
docker compose --env-file .env.deploy -f compose.demo.yaml exec -T db pg_dump -U planner -d flightplanner -Fc > backups/flightplanner.dump
```

Periodically verify a restore into a new database, never over the active one:

```sh
docker compose --env-file .env.deploy -f compose.demo.yaml exec -T db createdb -U planner flightplanner_restore_test
docker compose --env-file .env.deploy -f compose.demo.yaml exec -T db pg_restore -U planner -d flightplanner_restore_test --no-owner --exit-on-error < backups/flightplanner.dump
docker compose --env-file .env.deploy -f compose.demo.yaml exec -T db psql -U planner -d flightplanner_restore_test -c 'SELECT count(*) FROM profiles;'
```

Use a fresh restore database name for subsequent drills. Keep source revision,
image identifiers, database dump and deployment settings together in the update
record. Build and test the new source before `up -d --build --wait`. Roll back
to the previous source/images only if its schema is compatible; otherwise restore
the backup into a separate database and update the secret URL deliberately.
Do not downgrade migrations automatically. Image tags currently track upstream
patches; record deployed image digests and test updates before rollout.

For demo-password rotation, create a new bcrypt hash, replace the `demo_auth`
file securely, then recreate the proxy. A database password change additionally needs
an SQL role-password change and an updated URL: changing `POSTGRES_PASSWORD_FILE`
alone does not change an already-initialized database password. Keep backups of
existing secrets and perform rotation during a maintenance window.

## Verification boundary

See [VERIFICATION.md](../VERIFICATION.md) for executed checks. Local native
processes verified the production frontend, API, database and Caddy gate; Docker
images, container networking, public DNS and public certificate issuance still
require the server acceptance steps above. Duffel validation is outside the selected sample-data scope. No server has
been provisioned or published.

References: [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
[Caddy basic authentication](https://caddyserver.com/docs/caddyfile/directives/basic_auth),
[Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).
