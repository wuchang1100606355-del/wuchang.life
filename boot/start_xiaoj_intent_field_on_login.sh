#!/usr/bin/env bash
set -u

ROOT="$HOME/Taiji_Hub"
COMPOSE="$ROOT/docker-compose.xiaoj-intent-field.yml"
LOG="$ROOT/runtime/reports/xiaoj_intent_field_autostart.log"

mkdir -p "$ROOT/runtime/reports"

echo "[$(date -Is)] xiaoj intent field autostart check" >> "$LOG"

if ! command -v docker >/dev/null 2>&1; then
  echo "[$(date -Is)] docker not found" >> "$LOG"
  exit 0
fi

if docker ps --format '{{.Names}}' | grep -qx 'xiaoj-intent-field'; then
  echo "[$(date -Is)] already running" >> "$LOG"
  exit 0
fi

if [ -f "$COMPOSE" ]; then
  timeout 30s docker compose -f "$COMPOSE" up -d --no-recreate >> "$LOG" 2>&1 || true
fi
