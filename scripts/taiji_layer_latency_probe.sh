#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
STAMP="$(date +%Y%m%d_%H%M%S)"
N="${1:-5}"

OUT_JSON="$ROOT/runtime/reports/taiji_layer_latency_${STAMP}.jsonl"
OUT_MD="$ROOT/runtime/reports/taiji_layer_latency_${STAMP}.md"
LEDGER="$ROOT/runtime/ledger/latency_probe_events.jsonl"

mkdir -p "$ROOT/runtime/reports" "$ROOT/runtime/ledger"

ms_now() {
  python3 - <<'PY'
import time
print(int(time.perf_counter() * 1000))
PY
}

measure_cmd() {
  local name="$1"
  local from="$2"
  local to="$3"
  shift 3

  local total=0
  local ok=0
  local fail=0
  local min=999999999
  local max=0

  for i in $(seq 1 "$N"); do
    local start end dur status
    start="$(ms_now)"

    if "$@" >/dev/null 2>&1; then
      status="ok"
      ok=$((ok+1))
    else
      status="fail"
      fail=$((fail+1))
    fi

    end="$(ms_now)"
    dur=$((end-start))
    total=$((total+dur))

    [ "$dur" -lt "$min" ] && min="$dur"
    [ "$dur" -gt "$max" ] && max="$dur"

    printf '{"ts":"%s","name":"%s","from":"%s","to":"%s","try":%s,"status":"%s","ms":%s}\n' \
      "$(date -Is)" "$name" "$from" "$to" "$i" "$status" "$dur" >> "$OUT_JSON"
  done

  local avg
  avg=$((total/N))

  printf "| %s | %s | %s | %s/%s | %s | %s | %s |\n" \
    "$name" "$from" "$to" "$ok" "$N" "$min" "$avg" "$max" >> "$OUT_MD"

  printf '{"ts":"%s","summary":"%s","from":"%s","to":"%s","runs":%s,"ok":%s,"fail":%s,"min_ms":%s,"avg_ms":%s,"max_ms":%s}\n' \
    "$(date -Is)" "$name" "$from" "$to" "$N" "$ok" "$fail" "$min" "$avg" "$max" >> "$LEDGER"
}

measure_http() {
  local name="$1"
  local from="$2"
  local to="$3"
  local url="$4"

  measure_cmd "$name" "$from" "$to" curl -fsS --max-time 5 "$url"
}

measure_post_json() {
  local name="$1"
  local from="$2"
  local to="$3"
  local url="$4"
  local body="$5"

  measure_cmd "$name" "$from" "$to" \
    curl -fsS --max-time 10 -X POST "$url" \
      -H "Content-Type: application/json" \
      -d "$body"
}

cat > "$OUT_MD" <<MD
# Taiji 01 / 02 / 03 Layer Latency Probe

time: $(date -Is)  
runs per target: $N

| test | from | to | ok | min ms | avg ms | max ms |
|---|---|---|---:|---:|---:|---:|
MD

echo "=== Taiji 01 / 02 / 03 latency probe ==="
echo "runs per target: $N"

# 01 admin
measure_cmd  "01_admin_boot_policy_read"   "01_admin"      "local_file"      test -f "$ROOT/01_admin/boot/boot_policy.yaml"
measure_cmd  "01_admin_service_query"      "01_admin"      "systemd"         systemctl --user is-active taiji-admin-node.service
measure_http "01_to_gateway_health"        "01_admin"      "gateway_8081"    "http://127.0.0.1:8081/health"

# 02 edge nodes
for node in taiji01 openwebui odoo sensor; do
  measure_cmd "02_${node}_state_read"       "02_edge_nodes" "${node}_state"     test -f "$ROOT/runtime/state/edge_nodes/${node}.json"
  measure_cmd "02_${node}_systemd_query"    "02_edge_nodes" "${node}_systemd"   systemctl --user is-active "taiji-edge@${node}.service"
done

# 03 UI
measure_http "03_openwebui_http"            "03_ui"         "openwebui_8080"  "http://127.0.0.1:8080"
measure_http "03_bridge_models"             "03_ui"         "bridge_8098"     "http://127.0.0.1:8098/v1/models"
measure_http "03_to_gateway_health"         "03_ui"         "gateway_8081"    "http://127.0.0.1:8081/health"

# core services behind gateway
measure_http "gateway_to_ollama_tags"       "gateway"       "ollama_11434"    "http://127.0.0.1:11434/api/tags"
measure_http "gateway_to_claw_health"       "gateway"       "claw_9004"       "http://127.0.0.1:9004/healthz"

# topology API, may fail if not mounted
measure_http "gateway_topology_summary"     "gateway"       "topology_api"    "http://127.0.0.1:8081/taiji/topology/summary"

# route decision, may fail if topology router not mounted
measure_post_json \
  "gateway_route_decide_taiji01" \
  "gateway" \
  "02_taiji01" \
  "http://127.0.0.1:8081/taiji/route/decide" \
  '{"task_class":"topology_compute","action":"topology_compute","payload_summary":"latency probe","authority_level":3,"human_online":true}'

# short Ollama generation
measure_post_json \
  "ollama_short_generate" \
  "03_ui" \
  "ollama_11434" \
  "http://127.0.0.1:11434/api/generate" \
  '{"model":"taiji-memory:latest","prompt":"只回覆 OK","stream":false}'

{
  echo
  echo "## ports"
  echo '```'
  ss -ltnp | grep -E ':8081|:8080|:8098|:11434|:9004|:2222' || true
  echo '```'
  echo
  echo "## output files"
  echo "- report: $OUT_MD"
  echo "- jsonl: $OUT_JSON"
} >> "$OUT_MD"

echo
echo "=== report ==="
cat "$OUT_MD"

echo
echo "MD:    $OUT_MD"
echo "JSONL: $OUT_JSON"
\n\n# patched dynamic model for ollama generate\n\n\n# patched dynamic model for ollama generate\n