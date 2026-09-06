#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
LOGDIR="$ROOT/runtime/logs"
LEDGER="$ROOT/runtime/ledger/ui_03_events.jsonl"
DEAD="$ROOT/runtime/dead_letter/ui_03_rejected.jsonl"

mkdir -p "$LOGDIR" "$ROOT/runtime/ledger" "$ROOT/runtime/dead_letter"

port_open() {
  ss -ltn 2>/dev/null | grep -q ":$1 "
}

log() {
  printf '{"ts":"%s","service":"03_ui","event":"%s","detail":"%s"}\n' \
    "$(date -Is)" "$1" "$2" >> "$LEDGER"
}

reject() {
  printf '{"ts":"%s","service":"03_ui","reason":"%s","detail":"%s"}\n' \
    "$(date -Is)" "$1" "$2" >> "$DEAD"
}

align_openwebui_total_field() {
  LOCAL_DB="$HOME/wuchang_8_0_core/open-webui/backend/data/webui.db"
  ALIGNER="$ROOT/tools/align_openwebui_total_field.py"

  if [ ! -f "$LOCAL_DB" ]; then
    log "openwebui_alignment_skipped" "database_not_materialized"
    return 0
  fi
  if [ ! -f "$ALIGNER" ]; then
    reject "openwebui_alignment_failed" "aligner_missing"
    return 1
  fi
  if python3 "$ALIGNER" --db "$LOCAL_DB" --apply >> "$LOGDIR/openwebui_alignment.log" 2>&1; then
    log "openwebui_total_field_aligned" "8081"
    return 0
  fi
  reject "openwebui_alignment_failed" "fail_closed"
  return 1
}

start_openwebui() {
  if port_open 8080; then
    log "openwebui_already_running" "8080"
    return 0
  fi

  LOCAL_BACKEND="$HOME/wuchang_8_0_core/open-webui/backend"
  LOCAL_PY="$LOCAL_BACKEND/.venv/bin/python3"

  if [ -x "$LOCAL_PY" ] && [ -d "$LOCAL_BACKEND" ]; then
    log "start_openwebui_local" "$LOCAL_BACKEND"
    (
      cd "$LOCAL_BACKEND"
      nohup "$LOCAL_PY" -m uvicorn open_webui.main:app \
        --host 127.0.0.1 \
        --port 8080 \
        --forwarded-allow-ips 127.0.0.1 \
        --workers 1 \
        > "$LOGDIR/openwebui_8080.log" 2>&1 &
    )
    sleep 3
    return 0
  fi

  if command -v docker >/dev/null 2>&1; then
    docker start open-webui >/dev/null 2>&1 && {
      log "start_openwebui_docker" "open-webui"
      sleep 3
      return 0
    }
  fi

  reject "openwebui_start_failed" "no local backend or docker container"
}

start_bridge() {
  if port_open 8098; then
    log "bridge_already_running" "8098"
    return 0
  fi

  if [ -f "$ROOT/runtime/openwebui_bridge.py" ]; then
    log "start_openwebui_bridge" "$ROOT/runtime/openwebui_bridge.py"
    (
      cd "$ROOT"
      nohup python3 -m uvicorn runtime.openwebui_bridge:app \
        --host 127.0.0.1 \
        --port 8098 \
        > "$LOGDIR/openwebui_bridge_8098.log" 2>&1 &
    )
    sleep 2
    return 0
  fi

  reject "bridge_start_failed" "runtime/openwebui_bridge.py missing"
}

align_openwebui_total_field
start_openwebui
start_bridge

while true; do
  if port_open 8080; then ow="ok"; else ow="fail"; fi
  if port_open 8098; then br="ok"; else br="fail"; fi

  printf '{"ts":"%s","service":"03_ui","openwebui_8080":"%s","bridge_8098":"%s"}\n' \
    "$(date -Is)" "$ow" "$br" >> "$LEDGER"

  sleep 60
done
