#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${TAIJI_ENV_FILE:-$ROOT_DIR/deploy/env/runtime.env.example}"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PID_FILE="${TAIJI_RUNTIME_STATE_DIR:?}/taiji-runtime.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "runtime not running"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID"
  echo "runtime stopped: $PID"
else
  echo "stale pid removed: $PID"
fi
rm -f "$PID_FILE"
