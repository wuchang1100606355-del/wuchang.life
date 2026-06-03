#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
LEDGER="$ROOT/runtime/ledger/admin_node_events.jsonl"

mkdir -p "$ROOT/runtime/ledger" "$ROOT/runtime/state"

printf '{"ts":"%s","event":"admin_node_online","authority":"guarded"}\n' "$(date -Is)" >> "$LEDGER"

while true; do
  printf '{"ts":"%s","event":"admin_node_heartbeat"}\n' "$(date -Is)" >> "$LEDGER"
  sleep 30
done
