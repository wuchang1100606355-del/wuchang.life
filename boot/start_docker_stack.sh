#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
LEDGER="$ROOT/runtime/ledger/docker_stack_events.jsonl"
DEAD="$ROOT/runtime/dead_letter/docker_stack_rejected.jsonl"

mkdir -p "$ROOT/runtime/ledger" "$ROOT/runtime/dead_letter"

if ! command -v docker >/dev/null 2>&1; then
  printf '{"ts":"%s","reason":"docker_not_found"}\n' "$(date -Is)" >> "$DEAD"
  exit 0
fi

docker ps >/dev/null 2>&1 || {
  printf '{"ts":"%s","reason":"docker_not_ready"}\n' "$(date -Is)" >> "$DEAD"
  exit 0
}

printf '{"ts":"%s","event":"docker_stack_check_ok"}\n' "$(date -Is)" >> "$LEDGER"

# 可依你的實際 compose 檔逐步打開：
# docker compose -f Taiji_Odoo/docker-compose.yml up -d
# docker start open-webui wuchang_gpu_brain taiji_claw 2>/dev/null || true

sleep infinity
