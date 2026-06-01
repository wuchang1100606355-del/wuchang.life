#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PID_FILE="$TAIJI_STATE_DIR/runtime.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "runtime_pid=$(cat "$PID_FILE")"
else
  echo "runtime_pid=not_running"
fi

python3 - "$TAIJI_BIND_HOST" "$TAIJI_PORT" <<'PY'
import json
import sys
import urllib.error
import urllib.request

host = sys.argv[1]
port = int(sys.argv[2])
url = f"http://{host}:{port}/health"

try:
    with urllib.request.urlopen(url, timeout=5) as response:
        print(json.dumps(json.load(response), ensure_ascii=False, indent=2, sort_keys=True))
except urllib.error.URLError as exc:
    print(json.dumps({
        "ok": False,
        "runtime": "taiji_formal_tensor_runtime",
        "status": "not_reachable",
        "url": url,
        "error": str(exc.reason),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(1)
PY
