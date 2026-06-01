#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${TAIJI_ENV_FILE:-$ROOT_DIR/deploy/env/runtime.env.example}"

"$ROOT_DIR/deploy/scripts/preflight_check.sh"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PID_FILE="${TAIJI_RUNTIME_STATE_DIR:?}/taiji-runtime.pid"
LOG_FILE="${TAIJI_RUNTIME_STATE_DIR:?}/taiji-runtime.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "runtime already running: $(cat "$PID_FILE")"
  exit 0
fi

nohup python3 "$ROOT_DIR/deploy/runtime/runtime_entry.py" >>"$LOG_FILE" 2>&1 &
echo "$!" >"$PID_FILE"
echo "runtime started: $(cat "$PID_FILE")"
