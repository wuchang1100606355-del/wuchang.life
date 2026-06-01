#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/Taiji_Hub"
PIDFILE="$ROOT/runtime/7d_formal_tensor_runtime_8126.pid"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  kill "$(cat "$PIDFILE")"
  rm -f "$PIDFILE"
  echo "7D_FORMAL_TENSOR_RUNTIME_STOPPED"
else
  echo "7D_FORMAL_TENSOR_RUNTIME_NOT_RUNNING"
fi
