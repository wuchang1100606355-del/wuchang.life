#!/usr/bin/env bash
set -euo pipefail
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
PKG="$ROOT/deploy/packages/taiji01_metric_identity_gateway_v0_1"
cd "$PKG"
if [ ! -f "$ROOT/Taiji_Odoo/identity_map/five_code_identity_allowlist.json" ]; then
  echo "blocked: missing Odoo identity map $ROOT/Taiji_Odoo/identity_map/five_code_identity_allowlist.json"
  exit 2
fi
if [ -f "$ROOT/run/taiji01_metric_identity_gateway.pid" ]; then
  old_pid="$(cat "$ROOT/run/taiji01_metric_identity_gateway.pid" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    echo "stopping_legacy_nohup_pid=$old_pid"
    kill "$old_pid" || true
    sleep 1
  fi
fi
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose up -d --build
else
  echo "blocked: docker compose unavailable"
  exit 2
fi
