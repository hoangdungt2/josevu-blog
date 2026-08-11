#!/usr/bin/env bash
# Start the josevu-blog admin server (and optionally the cloudflared tunnel).
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

VENV="$ROOT/admin/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating venv..."
  uv venv "$VENV" --python 3.12
  uv pip install --python "$VENV/bin/python" -r "$ROOT/admin/requirements.txt"
fi

if [ ! -f "$ROOT/admin/.env" ]; then
  echo "WARNING: admin/.env not found. Copy admin/.env.example to admin/.env and fill it in."
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-7331}"

echo "Admin server on http://$HOST:$PORT  (tunnel: https://posts.josevu.com)"
exec "$VENV/bin/python" -m uvicorn admin.app:app --host "$HOST" --port "$PORT"
