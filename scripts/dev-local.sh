#!/usr/bin/env bash
# Workspace helper for the isolated PostgreSQL/Python runtime installed during development.
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
if [[ ! -x .postgres/bin/pg_ctl || ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  echo "Local runtimes are missing. Follow README.md or use docker compose up --build."
  exit 1
fi
if ! .postgres/bin/pg_ctl -D .pgdata status >/dev/null 2>&1; then
  .postgres/bin/pg_ctl -D .pgdata -l .pglog -o '-p 55432 -h 127.0.0.1 -k /private/tmp' start
fi
export DATABASE_URL='postgresql+psycopg://planner@127.0.0.1:55432/flightplanner'
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.seed
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
backend_pid=$!
cd ../frontend
npm run dev -- --host 127.0.0.1 &
frontend_pid=$!
trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' EXIT INT TERM
wait
