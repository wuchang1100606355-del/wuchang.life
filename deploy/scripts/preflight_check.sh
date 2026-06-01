#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${TAIJI_ENV_FILE:-$ROOT_DIR/deploy/env/runtime.env.example}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 missing" >&2
  exit 1
fi

if [ ! -f "$ROOT_DIR/schemas/formal_tensor_packet.schema.json" ]; then
  echo "missing schemas/formal_tensor_packet.schema.json" >&2
  exit 1
fi

if [ ! -f "$ROOT_DIR/services/gateway/policies/formal_tensor_validator.py" ]; then
  echo "missing services/gateway/policies/formal_tensor_validator.py" >&2
  exit 1
fi

if [ ! -f "$ROOT_DIR/deploy/runtime/runtime_entry.py" ]; then
  echo "missing deploy/runtime/runtime_entry.py" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

if [ "${TAIJI_BIND_HOST:-127.0.0.1}" = "0.0.0.0" ]; then
  echo "refusing unrestricted 0.0.0.0 bind" >&2
  exit 1
fi

python3 -m json.tool "$ROOT_DIR/schemas/formal_tensor_packet.schema.json" >/dev/null
python3 -m py_compile "$ROOT_DIR/services/gateway/policies/formal_tensor_validator.py"
python3 -m py_compile "$ROOT_DIR/deploy/runtime/runtime_entry.py"

python3 - "$TAIJI_BIND_HOST" "$TAIJI_PORT" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket()
try:
    sock.bind((host, port))
except OSError as exc:
    raise SystemExit(f"port unavailable: {host}:{port} ({exc})")
finally:
    sock.close()
PY

mkdir -p "${TAIJI_RUNTIME_STATE_DIR:?}" "${TAIJI_REPLAY_DIR:?}" "${TAIJI_DEADBOX_DIR:?}" "${TAIJI_CACHE_DIR:?}" "$(dirname "${TAIJI_AUDIT_PATH:?}")"

echo "preflight ok"
