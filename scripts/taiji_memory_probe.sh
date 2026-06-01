#!/usr/bin/env bash
set -u

cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
OUT="reports/memory/memory_probe_$TS.md"

{
echo "# Taiji Memory Probe"
echo "timestamp: $TS"
echo "host: $(hostname)"
echo

echo "## Host Memory"
free -h
echo

echo "## Host Swap"
swapon --show 2>/dev/null || true
echo

echo "## Docker Stats Snapshot"
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.PIDs}}' 2>/dev/null || true
echo

echo "## Container Memory Limits"
for C in $(docker ps --format '{{.Names}}'); do
  echo
  echo "### $C"
  docker inspect "$C" --format '
Name={{.Name}}
Memory={{.HostConfig.Memory}}
MemorySwap={{.HostConfig.MemorySwap}}
NanoCPUs={{.HostConfig.NanoCpus}}
OOMKillDisable={{.HostConfig.OomKillDisable}}
RestartPolicy={{.HostConfig.RestartPolicy.Name}}
ReadonlyRootfs={{.HostConfig.ReadonlyRootfs}}
'
done

echo
echo "## Ollama Models"
docker exec wuchang_gpu_brain ollama ps 2>/dev/null || true
docker exec wuchang_gpu_brain ollama list 2>/dev/null || true
echo

echo "## Queue Pressure"
echo "cloud_pilot_queue:"
find data/cloud_pilot_queue -type f 2>/dev/null | wc -l
echo "pos_voice_queue:"
find data/pos_voice_queue -type f 2>/dev/null | wc -l
echo "device_resilience:"
find data/device_resilience -type f 2>/dev/null | wc -l
echo

echo "## Recent OOM / Kill Logs"
dmesg 2>/dev/null | grep -Ei 'oom|killed process|out of memory' | tail -n 40 || true
} | tee "$OUT"

echo "REPORT=$OUT"
