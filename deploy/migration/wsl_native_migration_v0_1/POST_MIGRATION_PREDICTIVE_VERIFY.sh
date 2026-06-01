#!/usr/bin/env bash
set -euo pipefail

TARGET="${TARGET:-/home/taiji_admin/Taiji_Hub}"
TAIJI_TEST_TMPDIR="${TAIJI_TEST_TMPDIR:-/tmp/taiji_pytest_tmp}"
mkdir -p "$TAIJI_TEST_TMPDIR"

cd "$TARGET"

warn() {
  printf 'WARN: %s\n' "$*" >&2
}

ok() {
  printf 'OK: %s\n' "$*"
}

require_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    printf 'FAIL: missing required file: %s\n' "$path" >&2
    exit 1
  fi
  ok "file exists: $path"
}

expect_blocked() {
  local label="$1"
  shift
  set +e
  "$@" >/tmp/taiji_predictive_block.out 2>&1
  local rc=$?
  set -e
  if [ "$rc" -eq 2 ] && grep -qi '^blocked:' /tmp/taiji_predictive_block.out; then
    ok "legacy hazard blocked: $label"
  else
    warn "legacy hazard did not block as expected: $label rc=$rc"
    cat /tmp/taiji_predictive_block.out >&2 || true
  fi
}

printf 'post_migration_predictive_verify_started=%s\n' "$(date -Is)"
printf 'target=%s\n' "$TARGET"

if [ "$TARGET" != "/home/taiji_admin/Taiji_Hub" ]; then
  warn "TARGET is not canonical native workspace"
fi

require_file "Taiji_Governance/system_info/active_workspace_canonical_2026-05-14.json"
require_file "Taiji_Governance/system_info/vpn_node_declaration_2026-05-14.json"
require_file "site/taiji_system_dashboard/refresh_dashboard_state.py"
require_file "deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL_V011.sh"
require_file "deploy/migration/wsl_native_migration_v0_1/POST_MIGRATION_RUNTIME_CHECK.sh"

python3 -m py_compile site/taiji_system_dashboard/refresh_dashboard_state.py
python3 -m py_compile services/gateway/policies/formal_tensor_validator.py
python3 -m py_compile runtime_adapters/taiji_formal_tensor_runtime_v0_1_1_adapter.py
python3 -m py_compile deploy/packages/taiji_formal_tensor_runtime_v0_1_0/runtime_entry_v0_1_1.py
ok "python syntax checks passed"

python3 site/taiji_system_dashboard/refresh_dashboard_state.py >/tmp/taiji_dashboard_refresh.out
python3 -m json.tool site/taiji_system_dashboard/dashboard_state.json >/dev/null
ok "dashboard refresh and JSON validation passed"

TARGET="$TARGET" bash deploy/migration/wsl_native_migration_v0_1/POST_MIGRATION_RUNTIME_CHECK.sh >/tmp/taiji_post_migration_runtime_check.out
ok "post migration runtime check passed"

python3 - <<'PY'
from pathlib import Path
paths = [
    "deploy/systemd/taiji-runtime.service",
    "deploy/systemd/taiji-gateway.service",
    "deploy/systemd/taiji-audit.service",
    "deploy/packages/taiji_formal_tensor_runtime_v0_1_0/systemd.service",
    "deploy/formal_runtime_pkg_v0_1/systemd/taiji-formal-runtime-pkg-v0-1.service",
]
legacy = "/mnt/c/Users/o0930/Taiji_Hub"
for path in paths:
    text = Path(path).read_text(encoding="utf-8")
    if legacy in text:
        raise SystemExit(f"legacy path still present in {path}")
print("OK: systemd deployment templates use native workspace")
PY

expect_blocked "full_system.sh" bash full_system.sh
expect_blocked "run_nodes.sh" bash run_nodes.sh
expect_blocked "run_nodes_status.sh" bash run_nodes_status.sh
expect_blocked "Wuchang_Unified_Core/systemd_ignition.sh" bash Wuchang_Unified_Core/systemd_ignition.sh

bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/START_LOCAL_V011.sh >/tmp/taiji_runtime_start.out
bash deploy/packages/taiji_formal_tensor_runtime_v0_1_0/STATUS_LOCAL_V011.sh >/tmp/taiji_runtime_status.out
ok "formal tensor runtime local health passed"

python3 - <<'PY'
import urllib.request
checks = {
    "odoo": "http://127.0.0.1:8069/web/database/selector",
    "five_metric": "http://127.0.0.1:8105/health",
}
for name, url in checks.items():
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status >= 400:
                raise RuntimeError(response.status)
        print(f"OK: {name} reachable")
    except Exception as exc:
        raise SystemExit(f"FAIL: {name} not reachable: {type(exc).__name__}: {exc}")
PY

if tailscale serve status 2>&1 | grep -qv '^No serve config$'; then
  warn "tailscale serve has active config; inspect manually"
else
  ok "tailscale serve has no config"
fi

if tailscale funnel status 2>&1 | grep -qv '^No serve config$'; then
  warn "tailscale funnel has active config; inspect manually"
else
  ok "tailscale funnel has no config"
fi

if ss -tulpen 2>/dev/null | awk 'NR>1 && /LISTEN/ && /0\\.0\\.0\\.0|\\[::\\]/ {print}' >/tmp/taiji_public_listeners.txt; then
  if [ -s /tmp/taiji_public_listeners.txt ]; then
    warn "public listeners remain; classify as L2 until firewall/Gateway proof or bind-down"
    sed -E 's/users:\(\(.*\)\)//g' /tmp/taiji_public_listeners.txt >&2
  else
    ok "no public TCP listeners detected"
  fi
fi

printf 'post_migration_predictive_verify_completed=%s\n' "$(date -Is)"
printf 'result=ok_with_l2_listener_warnings_possible\n'
