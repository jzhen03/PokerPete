#!/usr/bin/env bash
# Boots the backend (FastAPI on :8000) and frontend (Vite on :5173) together.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  jobs -p | xargs -r kill
}
trap cleanup EXIT

(cd "$ROOT_DIR/backend" && uv run alembic upgrade head && uv run uvicorn pokerpete.main:app --reload --port 8000) &
(cd "$ROOT_DIR/frontend" && npm run dev) &

wait
