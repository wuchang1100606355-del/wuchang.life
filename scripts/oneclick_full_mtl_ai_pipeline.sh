#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
TODAY="$(date +%Y-%m-%d)"

PREFIX="prompts/FINAL_MTL_AI_CONCEPT_ARCHITECTURE_EN_ONLY_PREFIX.md"
HOST_MODEL="metric-language-gateway-ai:latest"
CONTAINER_MODEL="metric-language-gateway-ai:latest"
CONTAINER_MODELFILE="models/ollama/Modelfile.metric_language_gateway_ai.container"
REPORT="reports/finalization/full_mtl_ai_pipeline_${TS}.md"
JSON="contexts/current/FULL_MTL_AI_PIPELINE_STATUS.mtl.json"
LOG="logs/system/SYSTEM_LOG_FULL_MTL_AI_PIPELINE_${TS}.md"

echo "=== 0. CHECK PREFIX ==="
test -f "$PREFIX" || { echo "MISSING_PREFIX: $PREFIX"; exit 1; }
ls -lh "$PREFIX"

echo "=== 1. HOST OLLAMA MODEL CHECK ==="
if ollama show "$HOST_MODEL" >/dev/null 2>&1; then
  HOST_MODEL_OK=true
  echo "HOST_MODEL_OK: $HOST_MODEL"
else
  HOST_MODEL_OK=false
  echo "HOST_MODEL_MISSING: $HOST_MODEL"
fi

echo "=== 2. CONTAINER / NETWORK CHECK ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | tee /tmp/mtl_ai_containers.txt

echo "=== 3. OPENWEBUI -> CLAW SAFE ==="
OPENWEBUI_CLAW_OK=false
if docker exec open-webui sh -lc 'curl -fsS http://taiji_claw_safe:9004/healthz >/tmp/claw_health.json' 2>/dev/null; then
  OPENWEBUI_CLAW_OK=true
  docker exec open-webui sh -lc 'cat /tmp/claw_health.json'
else
  echo "OPENWEBUI_CLAW_SAFE_FAIL"
fi
echo

echo "=== 4. OPENWEBUI -> WUCHANG GPU BRAIN OLLAMA ==="
OPENWEBUI_OLLAMA_OK=false
if docker exec open-webui sh -lc 'curl -fsS http://wuchang_gpu_brain:11434/api/tags >/tmp/ollama_tags.json' 2>/dev/null; then
  OPENWEBUI_OLLAMA_OK=true
  docker exec open-webui sh -lc 'cat /tmp/ollama_tags.json' | head -c 1200
  echo
else
  echo "OPENWEBUI_OLLAMA_FAIL"
fi

echo "=== 5. BUILD MTL-AI MODEL INSIDE wuchang_gpu_brain IF NEEDED ==="
GPU_MODEL_OK=false

if docker exec wuchang_gpu_brain ollama show "$CONTAINER_MODEL" >/dev/null 2>&1; then
  GPU_MODEL_OK=true
  echo "GPU_CONTAINER_MODEL_ALREADY_EXISTS: $CONTAINER_MODEL"
else
  echo "GPU_CONTAINER_MODEL_MISSING: $CONTAINER_MODEL"
  echo "Detecting base model inside wuchang_gpu_brain..."

  BASE_MODEL=""
  for CANDIDATE in "llama3.1:latest" "llama3.1:8b" "qwen2.5:7b" "mistral:7b" "phi4-mini:latest"; do
    if docker exec wuchang_gpu_brain ollama show "$CANDIDATE" >/dev/null 2>&1; then
      BASE_MODEL="$CANDIDATE"
      break
    fi
  done

  if [ -z "$BASE_MODEL" ]; then
    echo "NO_BASE_MODEL_FOUND_IN_wuchang_gpu_brain"
  else
    echo "BASE_MODEL=$BASE_MODEL"

    {
      echo "FROM $BASE_MODEL"
      echo
      echo 'SYSTEM """'
      cat "$PREFIX"
      echo
      echo '"""'
    } > "$CONTAINER_MODELFILE"

    docker cp "$CONTAINER_MODELFILE" wuchang_gpu_brain:/tmp/Modelfile.metric_language_gateway_ai

    docker exec wuchang_gpu_brain ollama create "$CONTAINER_MODEL" -f /tmp/Modelfile.metric_language_gateway_ai

    if docker exec wuchang_gpu_brain ollama show "$CONTAINER_MODEL" >/dev/null 2>&1; then
      GPU_MODEL_OK=true
      echo "GPU_CONTAINER_MODEL_CREATED: $CONTAINER_MODEL"
    fi
  fi
fi

echo "=== 6. OPENWEBUI CAN SEE MODEL ==="
OPENWEBUI_SEES_MODEL=false
if docker exec open-webui sh -lc 'curl -fsS http://wuchang_gpu_brain:11434/api/tags | grep -q "metric-language-gateway-ai"' 2>/dev/null; then
  OPENWEBUI_SEES_MODEL=true
  echo "OPENWEBUI_SEES_MODEL=true"
else
  echo "OPENWEBUI_SEES_MODEL=false"
fi

echo "=== 7. OPENWEBUI -> OLLAMA GENERATE TEST ==="
OPENWEBUI_GENERATE_OK=false
if docker exec open-webui python - <<'PY'
import json, urllib.request, sys
payload = {
    "model": "metric-language-gateway-ai:latest",
    "prompt": "Confirm active invariant architecture using Ω0, I0, SA7, Tμν, Gτ, and EΣ. One paragraph.",
    "stream": False
}
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    "http://wuchang_gpu_brain:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=120) as res:
        body = res.read().decode("utf-8")
    print(body[:3000])
except Exception as e:
    print("GENERATE_FAIL:", e)
    sys.exit(1)
PY
then
  OPENWEBUI_GENERATE_OK=true
else
  echo "OPENWEBUI_GENERATE_FAIL"
fi

echo "=== 8. POS VOICE TOOL CHECK ==="
POS_LOCAL_OK=false
POS_VPN_OK=false

if curl -fsS http://127.0.0.1:9011/healthz >/tmp/pos_local_health.json 2>/dev/null; then
  POS_LOCAL_OK=true
  cat /tmp/pos_local_health.json
  echo
else
  echo "POS_LOCAL_FAIL"
fi

if curl -fsS http://100.107.187.77:9011/healthz >/tmp/pos_vpn_health.json 2>/dev/null; then
  POS_VPN_OK=true
  cat /tmp/pos_vpn_health.json
  echo
else
  echo "POS_VPN_FAIL_OR_NOT_REACHABLE_FROM_THIS_CONTEXT"
fi

echo "=== 9. METRIC GATEWAY TOOL FILE CHECK ==="
TOOL_OK=false
if [ -f openwebui_tools/taiji_metric_gateway_assembly_tool.py ]; then
  TOOL_OK=true
  ls -lh openwebui_tools/taiji_metric_gateway_assembly_tool.py
else
  echo "MISSING_TOOL_FILE"
fi

echo "=== 10. DEVICE RESILIENCE CHECK ==="
DEVICE_OK=false
if docker ps --format '{{.Names}}' | grep -qx taiji_device_resilience_adapter; then
  if docker exec open-webui sh -lc 'curl -fsS http://taiji_device_resilience_adapter:9012/healthz' 2>/dev/null; then
    DEVICE_OK=true
  fi
fi
echo "DEVICE_RESILIENCE_OK=$DEVICE_OK"

echo "=== 11. WRITE REPORT ==="
cat > "$REPORT" <<REPORT_EOF
# Full MTL-AI Pipeline Report

timestamp: $TS
date: $TODAY

## Formula

MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

## Status

host_model_ok: $HOST_MODEL_OK
openwebui_claw_ok: $OPENWEBUI_CLAW_OK
openwebui_ollama_ok: $OPENWEBUI_OLLAMA_OK
gpu_container_model_ok: $GPU_MODEL_OK
openwebui_sees_model: $OPENWEBUI_SEES_MODEL
openwebui_generate_ok: $OPENWEBUI_GENERATE_OK
pos_local_ok: $POS_LOCAL_OK
pos_vpn_ok: $POS_VPN_OK
metric_gateway_tool_file_ok: $TOOL_OK
device_resilience_ok: $DEVICE_OK

## Interpretation

Full local AI line is considered pass when:
- openwebui_claw_ok=true
- openwebui_ollama_ok=true
- openwebui_sees_model=true
- openwebui_generate_ok=true
- metric_gateway_tool_file_ok=true

POS line is considered pass when:
- pos_local_ok=true
- pos_vpn_ok=true

Device resilience line is optional until adapter is deployed:
- device_resilience_ok=true

## Runtime Selection

Open WebUI model:
metric-language-gateway-ai:latest

Open WebUI tools:
Taiji Claw Safe Bridge
Taiji Metric Gateway Assembly
REPORT_EOF

cat > "$JSON" <<JSON_EOF
{
  "type": "FULL_MTL_AI_PIPELINE_STATUS",
  "timestamp": "$TS",
  "date": "$TODAY",
  "formula": "MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ",
  "host_model_ok": $HOST_MODEL_OK,
  "openwebui_claw_ok": $OPENWEBUI_CLAW_OK,
  "openwebui_ollama_ok": $OPENWEBUI_OLLAMA_OK,
  "gpu_container_model_ok": $GPU_MODEL_OK,
  "openwebui_sees_model": $OPENWEBUI_SEES_MODEL,
  "openwebui_generate_ok": $OPENWEBUI_GENERATE_OK,
  "pos_local_ok": $POS_LOCAL_OK,
  "pos_vpn_ok": $POS_VPN_OK,
  "metric_gateway_tool_file_ok": $TOOL_OK,
  "device_resilience_ok": $DEVICE_OK,
  "local_ai_line_pass": $OPENWEBUI_CLAW_OK,
  "model_runtime_pass": $OPENWEBUI_GENERATE_OK,
  "pos_line_pass": $POS_LOCAL_OK,
  "status": "PIPELINE_PROBED"
}
JSON_EOF

cp "$JSON" .ai/FULL_MTL_AI_PIPELINE_STATUS.mtl.json

cat > "$LOG" <<LOG_EOF
# Full MTL-AI Pipeline Probe

timestamp: $TS
status: PIPELINE_PROBED

Formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Results:
- host_model_ok: $HOST_MODEL_OK
- openwebui_claw_ok: $OPENWEBUI_CLAW_OK
- openwebui_ollama_ok: $OPENWEBUI_OLLAMA_OK
- gpu_container_model_ok: $GPU_MODEL_OK
- openwebui_sees_model: $OPENWEBUI_SEES_MODEL
- openwebui_generate_ok: $OPENWEBUI_GENERATE_OK
- pos_local_ok: $POS_LOCAL_OK
- pos_vpn_ok: $POS_VPN_OK
- metric_gateway_tool_file_ok: $TOOL_OK
- device_resilience_ok: $DEVICE_OK

Next:
Select metric-language-gateway-ai:latest in Open WebUI and enable Taiji Claw Safe Bridge plus Taiji Metric Gateway Assembly.
LOG_EOF

cp "$LOG" logs/system/LATEST_SYSTEM_LOG.md

cat >> contexts/current/SYSTEM_CURRENT_STATE.md <<STATE_EOF

## Full MTL-AI Pipeline Probe

timestamp:
$TS

status:
PIPELINE_PROBED

Formula:
MTL-AI = Ω0 ⊕ I0 ⊕ SA7 ⊕ Tμν ⊕ Gτ ⊕ EΣ

Results:
- host_model_ok: $HOST_MODEL_OK
- openwebui_claw_ok: $OPENWEBUI_CLAW_OK
- openwebui_ollama_ok: $OPENWEBUI_OLLAMA_OK
- gpu_container_model_ok: $GPU_MODEL_OK
- openwebui_sees_model: $OPENWEBUI_SEES_MODEL
- openwebui_generate_ok: $OPENWEBUI_GENERATE_OK
- pos_local_ok: $POS_LOCAL_OK
- pos_vpn_ok: $POS_VPN_OK
- metric_gateway_tool_file_ok: $TOOL_OK
- device_resilience_ok: $DEVICE_OK
STATE_EOF

echo "=== FULL PIPELINE REPORT ==="
cat "$REPORT"

echo "=== FILES ==="
ls -lh "$REPORT" "$JSON" .ai/FULL_MTL_AI_PIPELINE_STATUS.mtl.json "$LOG" logs/system/LATEST_SYSTEM_LOG.md
