#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example"

"$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/PREFLIGHT.sh"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

mkdir -p "$TAIJI_STATE_DIR"
PID_FILE="$TAIJI_STATE_DIR/runtime.pid"
LOG_FILE="$TAIJI_STATE_DIR/runtime.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "already running: $(cat "$PID_FILE")"
  exit 0
fi

nohup python3 "$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py" >>"$LOG_FILE" 2>&1 &
echo "$!" >"$PID_FILE"
echo "started: $(cat "$PID_FILE")"
