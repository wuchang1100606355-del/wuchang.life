#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

mkdir -p "$TAIJI_STATE_DIR"
PID_FILE="$TAIJI_STATE_DIR/runtime_v0_1_1.pid"
LOG_FILE="$TAIJI_STATE_DIR/runtime_v0_1_1.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "already running: $(cat "$PID_FILE")"
  exit 0
fi

python3 -m py_compile "$ROOT_DIR/runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py"
python3 -m py_compile "$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry_v0_1_1.py"

nohup python3 "$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry_v0_1_1.py" >>"$LOG_FILE" 2>&1 &
echo "$!" >"$PID_FILE"
echo "started_v0_1_1: $(cat "$PID_FILE")"

python3 - "$TAIJI_BIND_HOST" "$TAIJI_PORT" "$LOG_FILE" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request

host = sys.argv[1]
port = int(sys.argv[2])
log_file = sys.argv[3]
url = f"http://{host}:{port}/health"
last_error = None
for _ in range(30):
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            data = json.load(response)
        print(json.dumps(data, ensure_ascii=False, sort_keys=True))
        raise SystemExit(0 if data.get("ok") else 1)
    except urllib.error.URLError as exc:
        last_error = exc
        time.sleep(0.2)
print(f"health_not_ready: {url} ({last_error})", file=sys.stderr)
try:
    with open(log_file, "r", encoding="utf-8") as handle:
        print(handle.read()[-4000:], file=sys.stderr)
except FileNotFoundError:
    print("runtime log missing", file=sys.stderr)
raise SystemExit(1)
PY
