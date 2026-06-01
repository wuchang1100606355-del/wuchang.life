#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$ROOT/runtime/reports/system_conformity_for_patent_${STAMP}.md"
mkdir -p "$ROOT/runtime/reports" "$ROOT/runtime/ledger" "$ROOT/runtime/dead_letter"

check_path() {
  local name="$1"
  local path="$2"
  if [ -e "$path" ]; then
    echo "| $name | $path | OK |" >> "$OUT"
  else
    echo "| $name | $path | MISSING |" >> "$OUT"
  fi
}

check_url() {
  local name="$1"
  local url="$2"
  if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
    echo "| $name | $url | OK |" >> "$OUT"
  else
    echo "| $name | $url | FAIL |" >> "$OUT"
  fi
}

check_unit() {
  local unit="$1"
  if systemctl --user is-active "$unit" >/dev/null 2>&1; then
    echo "| $unit | systemd user | ACTIVE |" >> "$OUT"
  else
    echo "| $unit | systemd user | NOT_ACTIVE |" >> "$OUT"
  fi
}

cat > "$OUT" <<MD
# Patent/System Conformity Check

time: $(date -Is)

## 1. Core paths

| item | path | status |
|---|---|---|
MD

check_path "01_admin" "$ROOT/01_admin"
check_path "02_edge_nodes" "$ROOT/02_edge_nodes"
check_path "03_ui_script" "$ROOT/boot/start_03_ui.sh"
check_path "gateway_service_code" "$ROOT/services/gateway"
check_path "runtime_state" "$ROOT/runtime/state"
check_path "runtime_ledger" "$ROOT/runtime/ledger"
check_path "runtime_dead_letter" "$ROOT/runtime/dead_letter"
check_path "configs_topology" "$ROOT/configs"
check_path "latency_probe" "$ROOT/scripts/taiji_layer_latency_probe.sh"

cat >> "$OUT" <<MD

## 2. Services

| item | target | status |
|---|---|---|
MD

check_unit "taiji-gateway.service"
check_unit "taiji-admin-node.service"
check_unit "taiji-edge@taiji01.service"
check_unit "taiji-edge@openwebui.service"
check_unit "taiji-edge@odoo.service"
check_unit "taiji-edge@sensor.service"
check_unit "taiji-03-ui.service"
check_unit "taiji-native-claw.service"
check_unit "taiji-healthcheck.timer"

cat >> "$OUT" <<MD

## 3. Local endpoints

| item | target | status |
|---|---|---|
MD

check_url "gateway_8081" "http://127.0.0.1:8081/health"
check_url "openwebui_8080" "http://127.0.0.1:8080"
check_url "bridge_8098" "http://127.0.0.1:8098/v1/models"
check_url "ollama_11434" "http://127.0.0.1:11434/api/tags"
check_url "claw_9004" "http://127.0.0.1:9004/healthz"

cat >> "$OUT" <<MD

## 4. Edge node state files

\`\`\`
$(ls -l "$ROOT/runtime/state/edge_nodes" 2>/dev/null || true)
\`\`\`

## 5. Edge boot hashes

\`\`\`
$(find "$ROOT/02_edge_nodes" -name node_boot.yaml -print -exec sha256sum {} \; 2>/dev/null || true)
\`\`\`

## 6. Dead letter files

\`\`\`
$(find "$ROOT/runtime/dead_letter" -maxdepth 1 -type f -print -exec wc -l {} \; 2>/dev/null || true)
\`\`\`

## 7. Ledger files

\`\`\`
$(find "$ROOT/runtime/ledger" -maxdepth 1 -type f -print -exec wc -l {} \; 2>/dev/null || true)
\`\`\`

## 8. Ports

\`\`\`
$(ss -ltnp | grep -E ':8081|:8080|:8098|:11434|:9004|:2222' || true)
\`\`\`

## 9. Red-team notes

- 若 OpenWebUI/Bridge 同時由多個 service 管理，應只保留 taiji-03-ui.service。
- 若 router topology API 尚未掛載，專利稿中的「度規拓樸路由」只能作附屬或待實作。
- 若 0xF124771717 尚無測試數據，不應放主權利項。
- 若 dead_letter 沒有 routing_rejected.jsonl，需統一路由拒收檔。
- 若 ledger 非 append-only，需補政策或權限控制。

MD

sha256sum "$OUT" > "$OUT.sha256"

printf '{"ts":"%s","event":"patent_system_conformity_report_created","report":"%s"}\n' \
  "$(date -Is)" "$OUT" >> "$ROOT/runtime/ledger/authority_events.jsonl"

echo "REPORT=$OUT"
echo "HASH=$OUT.sha256"
