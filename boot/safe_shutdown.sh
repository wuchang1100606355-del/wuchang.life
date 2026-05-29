#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
mkdir -p "$ROOT/runtime/ledger"
printf '{"ts":"%s","event":"safe_shutdown_requested"}\n' "$(date -Is)" >> "$ROOT/runtime/ledger/boot_events.jsonl"
