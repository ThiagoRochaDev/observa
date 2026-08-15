#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="$ROOT/apps/api"
WEB="$ROOT/apps/web"
CONN="$ROOT/packages/connectors"
DATA="$ROOT/data"

mkdir -p "$DATA"

echo "==> Observa local boot"
echo "    root: $ROOT"

if [[ ! -d "$API/.venv" ]]; then
  echo "==> Creating API venv"
  python3 -m venv "$API/.venv" || {
    echo "python3-venv missing; trying --break-system-packages install"
  }
fi

if [[ -x "$API/.venv/bin/pip" ]]; then
  PIP="$API/.venv/bin/pip"
  PY="$API/.venv/bin/python"
  UVICORN="$API/.venv/bin/uvicorn"
else
  PIP="python3 -m pip"
  PY="python3"
  UVICORN="python3 -m uvicorn"
  PIP_FLAGS="--break-system-packages"
fi

echo "==> Installing connectors + API"
$PIP ${PIP_FLAGS:-} install -q -e "$CONN"
$PIP ${PIP_FLAGS:-} install -q -e "$API"

echo "==> Installing web deps"
if [[ ! -d "$WEB/node_modules" ]]; then
  (cd "$WEB" && npm install)
fi
cp -n "$WEB/.env.example" "$WEB/.env.local" 2>/dev/null || true

echo "==> Starting API :8080"
(
  cd "$API"
  export PYTHONPATH="$API:${PYTHONPATH:-}"
  $UVICORN app.main:app --reload --host 0.0.0.0 --port 8080
) &
API_PID=$!

echo "==> Starting Web :3000"
(
  cd "$WEB"
  npm run dev
) &
WEB_PID=$!

cleanup() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "Observa is up:"
echo "  Web  http://localhost:3000"
echo "  API  http://localhost:8080/docs"
echo ""
echo "1) Open Connections → Mock Demo → Save → Sync"
echo "2) Overview / Products should show sample data"
echo "3) Settings → Authentication to configure GitLab/Google SSO"
echo ""
wait
