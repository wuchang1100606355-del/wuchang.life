#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/Taiji_Hub"
PIDFILE="$ROOT/runtime/7d_formal_tensor_runtime_8126.pid"
LOGFILE="$ROOT/logs/7d_formal_tensor_runtime_8126.log"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "7D_FORMAL_TENSOR_RUNTIME_ALREADY_RUNNING pid=$(cat "$PIDFILE")"
  exit 0
fi

nohup python3 "$ROOT/runtime/7d_formal_tensor_runtime_8126.py" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"

sleep 0.5

python3 - <<'PY'
import socket, json
s = socket.socket()
s.settimeout(0.5)
ok = s.connect_ex(("127.0.0.1", 8126)) == 0
s.close()
print(json.dumps({"formal_tensor_runtime_8126": ok}, ensure_ascii=False))
raise SystemExit(0 if ok else 1)
PY
