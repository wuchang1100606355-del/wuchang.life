#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT"

mkdir -p runtime/logs runtime/ledger runtime/dead_letter

if [ ! -f "services/gateway/main.py" ]; then
  printf '{"ts":"%s","reason":"gateway_missing","detail":"services/gateway/main.py not found"}\n' "$(date -Is)" >> runtime/dead_letter/boot_rejected.jsonl
  exit 1
fi

exec python3 -m uvicorn services.gateway.main:app --host 127.0.0.1 --port 8081
