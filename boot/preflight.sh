#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
LEDGER="$ROOT/runtime/ledger/boot_events.jsonl"
DEAD="$ROOT/runtime/dead_letter/boot_rejected.jsonl"

mkdir -p "$ROOT/runtime/ledger" "$ROOT/runtime/dead_letter" "$ROOT/runtime/logs" "$ROOT/runtime/state"

log() {
  printf '{"ts":"%s","event":"%s","detail":"%s"}\n' "$(date -Is)" "$1" "$2" >> "$LEDGER"
}

reject() {
  printf '{"ts":"%s","reason":"%s","detail":"%s"}\n' "$(date -Is)" "$1" "$2" >> "$DEAD"
}

cd "$ROOT"

for p in \
  "01_admin/boot/root_authority_guard.yaml" \
  "01_admin/boot/boot_policy.yaml" \
  "boot/taiji_boot_order.yaml" \
  "runtime/state" \
  "runtime/ledger" \
  "runtime/dead_letter"
do
  if [ ! -e "$p" ]; then
    reject "missing_required_path" "$p"
    exit 1
  fi
done

if find "$ROOT" -maxdepth 4 \( -name "*.key" -o -name "id_rsa" -o -name ".env" \) | grep -q .; then
  log "warning" "possible_secret_files_detected_check_permissions"
fi

log "preflight_ok" "Taiji boot preflight passed"
