#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

section() {
  printf '\n[%s]\n' "$1"
}

run_readonly() {
  local label="$1"
  shift
  printf '## %s\n' "$label"
  if "$@"; then
    printf '## %s: ok\n' "$label"
  else
    local code=$?
    printf '## %s: failed code=%s\n' "$label" "$code"
  fi
}

section "TAIJI_READONLY_PROBE"
printf 'root=%s\n' "$ROOT_DIR"
printf 'mode=read_only_no_secret_output\n'

section "PATHS"
for path in \
  "Taiji_AutoBuild" \
  "Taiji_AutoBuild/scripts/00_readonly_probe.sh" \
  "Taiji_AutoBuild/scripts/01_import_chatgpt_export.py" \
  "Taiji_AutoBuild/scripts/02_start_vector_lite.sh" \
  "Taiji_AutoBuild/scripts/03_collect_runtime_snapshot.sh" \
  "Taiji_AutoBuild/prompts/codex_readonly_prompt.md" \
  "Taiji_AutoBuild/prompts/xiaoj_master_prompt.md" \
  "Taiji_Governance/worklist/worklist.md" \
  "Taiji_Governance/progress/progress.md" \
  "Taiji_Governance/logs/audit.log" \
  "Taiji_Governance/syslog/system_journal.log" \
  "Taiji_Vector_Runtime_Lite" \
  "Taiji_Odoo/docker-compose.yml"; do
  if [[ -e "$ROOT_DIR/$path" ]]; then
    printf 'EXISTS %s\n' "$path"
  else
    printf 'MISSING %s\n' "$path"
  fi
done

section "CONTAINERS"
if command -v docker >/dev/null 2>&1; then
  run_readonly "docker_ps" docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
else
  printf 'docker=missing\n'
fi

section "NETWORK"
if command -v ss >/dev/null 2>&1; then
  run_readonly "listening_ports" ss -ltnp
else
  printf 'ss=missing\n'
fi
if command -v ip >/dev/null 2>&1; then
  run_readonly "ip_route" ip route
else
  printf 'ip=missing\n'
fi

section "TAILSCALE"
if command -v tailscale >/dev/null 2>&1; then
  run_readonly "tailscale_status" tailscale status
else
  printf 'tailscale=missing\n'
fi

section "LOCAL_ENDPOINTS"
if command -v curl >/dev/null 2>&1; then
  run_readonly "five_metric_health" curl -fsS --max-time 2 http://127.0.0.1:8105/health
  run_readonly "five_metric_policy" curl -fsS --max-time 2 http://127.0.0.1:8105/policy
  run_readonly "odoo_database_manager_head" curl -I -fsS --max-time 2 http://127.0.0.1:8069/web/database/manager
else
  printf 'curl=missing\n'
fi

section "CREDENTIAL_FILE_NAMES_ONLY"
find "$ROOT_DIR" -maxdepth 5 -type f \
  \( -iname '*credential*' -o -iname '*service*account*.json' -o -iname '*oauth*' -o -iname '*client_secret*' -o -path '*/keys/*.json' \) \
  -printf '%P\n' | sort || true

section "HAZARD_PATTERNS"
if [[ -f "$ROOT_DIR/legacy_core/wuchang_tailscale_deployer.py" ]]; then
  if rg -n -- 'gcp_key|GCP_KEY|client_secret|StrictHostKeyChecking=no|cat .*ssh|ssh_cmd|scp_cmd|proc_key|KEY_PATH|key_local_path' "$ROOT_DIR/legacy_core/wuchang_tailscale_deployer.py" >/tmp/taiji_hazard_scan.txt 2>/dev/null; then
    printf 'L3_metric_hazard legacy_core/wuchang_tailscale_deployer.py contains unsafe deployment patterns\n'
    sed -n '1,80p' /tmp/taiji_hazard_scan.txt
  else
    printf 'legacy_deployer_hazard_patterns=not_found\n'
  fi
fi

section "DONE"
printf 'result=read_only_probe_complete\n'
