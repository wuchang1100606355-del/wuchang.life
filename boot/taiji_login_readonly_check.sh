#!/usr/bin/env bash
set -euo pipefail

ACTUAL_CWD="${PWD:-$(pwd -P)}"
CONFIGURED_CANONICAL="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
ROOT="$CONFIGURED_CANONICAL"
LEDGER="$ROOT/runtime/ledger/login_readonly_check.jsonl"
LEDGER_ENABLED="${TAIJI_LOGIN_READONLY_LEDGER:-0}"

resolve_git_root() {
  local path="$1"
  if [ ! -e "$path/.git" ]; then
    return 0
  fi
  git -C "$path" rev-parse --show-toplevel 2>/dev/null || true
}

RESOLVED_GIT_ROOT="$(resolve_git_root "$ACTUAL_CWD")"
if [ -z "$RESOLVED_GIT_ROOT" ]; then
  RESOLVED_GIT_ROOT="$(resolve_git_root "$CONFIGURED_CANONICAL")"
fi
if [ -z "$RESOLVED_GIT_ROOT" ]; then
  RESOLVED_GIT_ROOT="UNRESOLVED"
fi

if command -v wslpath >/dev/null 2>&1; then
  WINDOWS_PATH_HINT="$(wslpath -w "$ACTUAL_CWD" 2>/dev/null || printf "%s" "UNAVAILABLE")"
else
  WINDOWS_PATH_HINT="UNAVAILABLE"
fi

READONLY_GUARD="readonly only; no SSH, no process kill, no auto-start"

write_ledger() {
  if [ "$LEDGER_ENABLED" != "1" ]; then
    return 0
  fi
  mkdir -p "$ROOT/runtime/ledger"
  printf "%s\n" "$1" >> "$LEDGER"
}

check_url() {
  local name="$1"
  local url="$2"
  if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
    status="running"
  else
    status="not_running"
  fi
  printf "[status] %-24s %s\n" "$name:" "$status"
  write_ledger "$(printf '{"ts":"%s","check":"%s","url":"%s","status":"%s"}' \
    "$(date -Is)" "$name" "$url" "$status")"
}

check_port() {
  local name="$1"
  local port="$2"
  if ss -ltn 2>/dev/null | grep -q ":$port "; then
    status="listening"
  else
    status="not_listening"
  fi
  printf "[port]   %-24s %s\n" "$name $port:" "$status"
  write_ledger "$(printf '{"ts":"%s","check":"%s","port":"%s","status":"%s"}' \
    "$(date -Is)" "$name" "$port" "$status")"
}

echo "======================================================"
echo "     Taiji Login Readonly Check - CURRENT"
echo "======================================================"
echo "[workspace] actual_cwd: $ACTUAL_CWD"
echo "[workspace] configured_canonical: $CONFIGURED_CANONICAL"
echo "[workspace] resolved_git_root: $RESOLVED_GIT_ROOT"
echo "[workspace] windows_path_hint: $WINDOWS_PATH_HINT"
echo "[guard] readonly_guard: $READONLY_GUARD"

check_url  "taiji_gateway"      "http://127.0.0.1:8081/health"
check_url  "open_webui"         "http://127.0.0.1:8080"
check_url  "openwebui_bridge"   "http://127.0.0.1:8098/v1/models"
check_url  "ollama"             "http://127.0.0.1:11434/api/tags"
check_url  "native_claw"        "http://127.0.0.1:9004/healthz"
check_url  "xiaoj_intent_field" "http://127.0.0.1:9107/healthz"
check_port "ssh_tunnel"         "2222"

if command -v tailscale >/dev/null 2>&1; then
  echo "[vpn] self_ip: $(tailscale ip -4 2>/dev/null | head -n 1 || true)"
  tailscale status 2>/dev/null | awk 'NR<=12 {print "[vpn] " $0}' || true
fi

echo "[legacy] 8000 / 9090 / mu_0 / mu_2 are archived checks, not current boot targets"
echo "======================================================"
