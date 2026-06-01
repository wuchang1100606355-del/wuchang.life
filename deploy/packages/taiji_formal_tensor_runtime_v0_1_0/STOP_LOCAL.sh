#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PID_FILE="$TAIJI_STATE_DIR/runtime.pid"
if [ ! -f "$PID_FILE" ]; then
  echo "not running"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID"
  echo "stopped: $PID"
else
  echo "stale pid removed: $PID"
fi
rm -f "$PID_FILE"
