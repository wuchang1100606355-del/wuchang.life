#!/usr/bin/env bash
set -euo pipefail

NODE_ID="${1:?node id required}"
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"

NODE_FILE="$ROOT/02_edge_nodes/$NODE_ID/node_boot.yaml"
STATE_DIR="$ROOT/runtime/state/edge_nodes"
STATE_FILE="$STATE_DIR/${NODE_ID}.json"
LEDGER="$ROOT/runtime/ledger/edge_node_events.jsonl"
DEAD="$ROOT/runtime/dead_letter/edge_node_rejected.jsonl"

mkdir -p "$STATE_DIR" "$ROOT/runtime/ledger" "$ROOT/runtime/dead_letter"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip(), ensure_ascii=False))'
}

log_event() {
  local event="$1"
  local detail="${2:-}"
  printf '{"ts":"%s","node":"%s","event":"%s","detail":%s}\n' \
    "$(date -Is)" "$NODE_ID" "$event" "$(printf '%s' "$detail" | json_escape)" >> "$LEDGER"
}

reject() {
  local reason="$1"
  local detail="${2:-}"
  printf '{"ts":"%s","node":"%s","reason":"%s","detail":%s}\n' \
    "$(date -Is)" "$NODE_ID" "$reason" "$(printf '%s' "$detail" | json_escape)" >> "$DEAD"
}

if [ ! -f "$NODE_FILE" ]; then
  reject "missing_node_boot_yaml" "$NODE_FILE"
  exit 1
fi

HASH="$(sha256sum "$NODE_FILE" | awk '{print $1}')"

write_state() {
  local status="$1"
  cat > "$STATE_FILE" <<JSON
{
  "ts": "$(date -Is)",
  "node": "$NODE_ID",
  "status": "$status",
  "pid": $$,
  "boot_file": "$NODE_FILE",
  "boot_file_sha256": "$HASH",
  "gateway_required": true,
  "managed_by": "taiji-edge@${NODE_ID}.service"
}
JSON
}

write_state "online"
log_event "edge_node_online" "canonical boot started"

trap 'write_state "stopping"; log_event "edge_node_stopping" "signal received"; exit 0' INT TERM

while true; do
  write_state "online"

  if curl -fsS --max-time 2 http://127.0.0.1:8081/health >/dev/null 2>&1; then
    log_event "heartbeat" "gateway_ok"
  else
    log_event "heartbeat" "gateway_unreachable"
  fi

  sleep 60
done
