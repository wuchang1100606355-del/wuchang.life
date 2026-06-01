#!/usr/bin/env bash
set -u

cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
OUT="reports/memory/apply_container_memory_policy_$TS.md"

{
echo "# Apply Container Memory Policy"
echo "timestamp: $TS"
echo

echo "## Before"
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}' 2>/dev/null || true
echo

echo "## Apply Limits"

if docker ps --format '{{.Names}}' | grep -qx open-webui; then
  echo "open-webui -> memory=6g swap=8g"
  docker update --memory=6g --memory-swap=8g open-webui
fi

if docker ps --format '{{.Names}}' | grep -qx taiji_claw_safe; then
  echo "taiji_claw_safe -> memory=512m swap=1g"
  docker update --memory=512m --memory-swap=1g taiji_claw_safe
fi

if docker ps --format '{{.Names}}' | grep -qx taiji_pos_google_voice_tool; then
  echo "taiji_pos_google_voice_tool -> memory=512m swap=1g"
  docker update --memory=512m --memory-swap=1g taiji_pos_google_voice_tool
fi

if docker ps --format '{{.Names}}' | grep -qx taiji_device_resilience_adapter; then
  echo "taiji_device_resilience_adapter -> memory=512m swap=1g"
  docker update --memory=512m --memory-swap=1g taiji_device_resilience_adapter
fi

echo
echo "## Ollama"
echo "wuchang_gpu_brain -> no hard cap applied"

echo
echo "## After Inspect"
for C in $(docker ps --format '{{.Names}}'); do
  echo
  echo "### $C"
  docker inspect "$C" --format '
Memory={{.HostConfig.Memory}}
MemorySwap={{.HostConfig.MemorySwap}}
OOMKillDisable={{.HostConfig.OomKillDisable}}
RestartPolicy={{.HostConfig.RestartPolicy.Name}}
'
done

echo
echo "## After Stats"
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}' 2>/dev/null || true
} | tee "$OUT"

echo "REPORT=$OUT"
