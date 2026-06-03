#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/packages/taiji_formal_tensor_runtime_v0_1_0/env.example"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$ROOT_DIR/Taiji_Governance/runtime/reconciliation/node_diagnostics"
OUT_FILE="$OUT_DIR/runtime_node_diagnostics_${TS}.txt"
AUDIT_LOG="$ROOT_DIR/Taiji_Governance/logs/runtime_node_diagnostics_2026-05-12.jsonl"

mkdir -p "$OUT_DIR" "$(dirname "$AUDIT_LOG")"

{
  printf 'runtime_node_diagnostics=%s\n' "$TS"
  printf 'root=%s\n' "$ROOT_DIR"
  printf 'hostname=%s\n' "$(hostname 2>/dev/null || true)"
  printf 'whoami=%s\n' "$(whoami 2>/dev/null || true)"
  printf 'kernel=%s\n' "$(uname -a 2>/dev/null || true)"
  printf 'bind_host=%s\n' "$TAIJI_BIND_HOST"
  printf 'port=%s\n' "$TAIJI_PORT"
  printf 'state_dir=%s\n' "$TAIJI_STATE_DIR"
  printf 'cache_policy_path=%s\n' "$TAIJI_INTENT_CACHE_POLICY_PATH"
  printf '\n== pid files ==\n'
  find "$TAIJI_STATE_DIR" -maxdepth 1 -type f -name '*.pid' -print -exec sh -c 'for f; do printf "%s=" "$f"; cat "$f"; printf "\n"; done' sh {} + 2>/dev/null || true
  printf '\n== process summary ==\n'
  ps -eo pid,ppid,stat,comm,args --sort=pid 2>/dev/null | grep -E 'taiji|runtime_entry|python3|ollama|odoo|postgres|docker' | grep -v grep || true
  printf '\n== listening ports ==\n'
  ss -ltnp 2>/dev/null | grep -E ':(8000|8069|8105|8126|9004|9090)\\b' || true
  printf '\n== health probe ==\n'
  python3 - "$TAIJI_BIND_HOST" "$TAIJI_PORT" <<'PY' || true
import json
import sys
import urllib.error
import urllib.request

url = f"http://{sys.argv[1]}:{int(sys.argv[2])}/health"
try:
    with urllib.request.urlopen(url, timeout=2) as response:
        print(json.dumps(json.load(response), ensure_ascii=False, sort_keys=True))
except Exception as exc:
    print(json.dumps({"ok": False, "url": url, "error": str(exc)}, ensure_ascii=False, sort_keys=True))
PY
  printf '\n== tailscale summary ==\n'
  if command -v tailscale >/dev/null 2>&1; then
    tailscale status --self 2>/dev/null || true
    tailscale ip 2>/dev/null || true
  else
    printf 'tailscale=not_installed_or_not_in_path\n'
  fi
  printf '\n== runtime log tail ==\n'
  tail -n 80 "$TAIJI_STATE_DIR/runtime_v0_1_1.log" 2>/dev/null || true
} > "$OUT_FILE"

python3 - <<PY >> "$AUDIT_LOG"
import json
from datetime import datetime, timezone, timedelta
print(json.dumps({
    "event": "runtime_node_diagnostics_collected",
    "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    "diagnostics_path": "$OUT_FILE",
    "secret_material_printed": False,
    "credential_material_read": False,
    "external_api_called": False,
    "live_deploy_executed": False,
    "trigger": "runtime_health_check_failed_or_manual_diagnostics",
}, ensure_ascii=False))
PY

echo "diagnostics_path=$OUT_FILE"
