#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="$ROOT_DIR/Taiji_Vector_Runtime_Lite"
HOST="${TAIJI_VECTOR_LITE_HOST:-127.0.0.1}"
PORT="${TAIJI_VECTOR_LITE_PORT:-8110}"
MODE="${1:---plan}"

printf 'service=Taiji_Vector_Runtime_Lite\n'
printf 'host=%s\n' "$HOST"
printf 'port=%s\n' "$PORT"
printf 'mode=%s\n' "$MODE"
printf 'external_api_called=false\n'

if [[ "$MODE" != "--plan" ]]; then
  printf 'refused=true\n'
  printf 'reason=Vector Lite launcher is plan-only; no live start path is embedded\n'
  exit 3
fi

printf 'plan_only=true\n'
printf 'preflight_required=true\n'
printf 'human_decision_required=true\n'
printf 'suggested_command=cd %s && python3 -m uvicorn app.main:app --host %s --port %s\n' "$APP_DIR" "$HOST" "$PORT"
