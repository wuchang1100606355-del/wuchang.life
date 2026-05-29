#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
LEDGER="$ROOT/runtime/ledger/native_claw_events.jsonl"
DEAD="$ROOT/runtime/dead_letter/native_claw_rejected.jsonl"

mkdir -p "$ROOT/runtime/ledger" "$ROOT/runtime/dead_letter"

port_open() {
  ss -ltn 2>/dev/null | grep -q ":$1 "
}

log() {
  printf '{"ts":"%s","service":"native_claw","event":"%s","detail":"%s"}\n' \
    "$(date -Is)" "$1" "$2" >> "$LEDGER"
}

reject() {
  printf '{"ts":"%s","service":"native_claw","reason":"%s","detail":"%s"}\n' \
    "$(date -Is)" "$1" "$2" >> "$DEAD"
}

if ! port_open 9004; then
  if command -v docker >/dev/null 2>&1; then
    docker start taiji_claw_safe >/dev/null 2>&1 && log "docker_started" "taiji_claw_safe" || \
    docker start taiji_claw >/dev/null 2>&1 && log "docker_started" "taiji_claw" || \
    reject "docker_start_failed" "taiji_claw_safe / taiji_claw not started"
  else
    reject "docker_missing" "docker command not found"
  fi
fi

while true; do
  if port_open 9004; then st="ok"; else st="fail"; fi
  printf '{"ts":"%s","service":"native_claw","port_9004":"%s"}\n' \
    "$(date -Is)" "$st" >> "$LEDGER"
  sleep 60
done
