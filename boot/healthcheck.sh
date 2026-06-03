#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
LEDGER="$ROOT/runtime/ledger/health_events.jsonl"
mkdir -p "$ROOT/runtime/ledger"

check_url() {
  name="$1"
  url="$2"
  if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
    status="ok"
  else
    status="fail"
  fi
  printf '{"ts":"%s","service":"%s","url":"%s","status":"%s"}\n' "$(date -Is)" "$name" "$url" "$status" >> "$LEDGER"
}

check_any() {
  name="$1"
  shift
  ok="fail"
  chosen=""
  for url in "$@"; do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      ok="ok"
      chosen="$url"
      break
    fi
  done
  [ -z "$chosen" ] && chosen="$1"
  printf '{"ts":"%s","service":"%s","url":"%s","status":"%s"}\n' "$(date -Is)" "$name" "$chosen" "$ok" >> "$LEDGER"
}

check_url "gateway" "http://127.0.0.1:8081/health"
check_any "openwebui" \
  "http://127.0.0.1:3000" \
  "http://127.0.0.1:8080" \
  "http://127.0.0.1:8080/health"
check_url "openwebui_bridge" "http://127.0.0.1:8098/v1/models"
check_url "ollama" "http://127.0.0.1:11434/api/tags"
check_url "claw" "http://127.0.0.1:9004/healthz"
