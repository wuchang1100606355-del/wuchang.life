#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PID_FILE="$TAIJI_STATE_DIR/runtime.pid"
LOG_FILE="$TAIJI_STATE_DIR/runtime.log"

echo "== package =="
echo "root=$ROOT_DIR"
echo "env=$ENV_FILE"
echo "bind=${TAIJI_BIND_HOST:-127.0.0.1}"
echo "port=${TAIJI_PORT:-8126}"
echo "state=${TAIJI_STATE_DIR:-unset}"

echo
echo "== pid =="
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  echo "pid_file=$PID"
  if kill -0 "$PID" >/dev/null 2>&1; then
    echo "pid_status=running"
  else
    echo "pid_status=not_running_or_exited"
  fi
else
  echo "pid_file=missing"
fi

echo
echo "== log tail =="
if [ -f "$LOG_FILE" ]; then
  tail -80 "$LOG_FILE"
else
  echo "log_file=missing"
fi

echo
echo "== import check =="
python3 - <<'PY'
import pathlib
import sys

root = pathlib.Path.cwd()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

try:
    from runtime_adapters.taiji_formal_tensor_runtime_v0_1_0_adapter import validate
    print("adapter_import=ok")
    result = validate({"TensorPacket": {"tau": {}, "pi": {}, "rho": {}, "alpha": {}}})
    print("adapter_validate=ok")
    print(result)
except Exception as exc:
    print(f"adapter_import_or_validate=failed:{type(exc).__name__}:{exc}")
    raise
PY

echo
echo "== foreground launch hint =="
echo "If the log does not explain the failure, run:"
echo "python3 deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry.py"
