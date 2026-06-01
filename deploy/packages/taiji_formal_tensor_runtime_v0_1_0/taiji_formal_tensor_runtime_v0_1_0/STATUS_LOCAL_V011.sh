#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PID_FILE="$TAIJI_STATE_DIR/runtime_v0_1_1.pid"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "runtime_pid=$(cat "$PID_FILE")"
else
  echo "runtime_pid=not_running"
fi

python3 - "$TAIJI_BIND_HOST" "$TAIJI_PORT" <<'PY'
import json
import sys
import urllib.request

host = sys.argv[1]
port = int(sys.argv[2])
with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5) as response:
    print(json.dumps(json.load(response), ensure_ascii=False, indent=2, sort_keys=True))
PY
