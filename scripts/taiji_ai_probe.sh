#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
OUT="reports/ai_probe_$TS.md"
JSON="reports/ai_probe_$TS.json"

mkdir -p reports .ai

{
echo "# Taiji AI Probe"
echo
echo "timestamp: $TS"
echo "pwd: $(pwd)"
echo "user: $(whoami)"
echo "host: $(hostname)"
echo

echo "## Human Files"
for f in contexts/human/*.md; do
  [ -f "$f" ] && echo "- $f : $(sha256sum "$f" | awk '{print $1}')"
done

echo
echo "## AI Metric Tensor Files"
for f in contexts/ai_metric/*.json; do
  [ -f "$f" ] && echo "- $f : $(sha256sum "$f" | awk '{print $1}')"
done

echo
echo "## Ports"
ss -lntp 2>/dev/null | grep -E ':8000|:9004|:9090|:50051|:8069' || true

echo
echo "## Processes"
ps aux | grep -Ei 'taiji|wuchang|jules|sister|python|node|odoo|8000|9004|9090|50051|8069' | grep -v grep || true

echo
echo "## Top Directory"
find . -maxdepth 1 -mindepth 1 -printf '%f\n' | sort

echo
echo "## Sensitive Filenames Only"
find keys security config taiji_env admin -maxdepth 3 -type f 2>/dev/null | sed 's#^\./##' | sort | head -n 200

echo
echo "## HTTP Health"
for p in 8000 9004 9090 8069; do
  echo "### port $p"
  timeout 2 bash -c "cat < /dev/null > /dev/tcp/127.0.0.1/$p" && echo "tcp_open=true" || echo "tcp_open=false"
  curl -I --max-time 2 "http://127.0.0.1:$p" 2>/dev/null | head -n 5 || true
done
} > "$OUT"

cat > "$JSON" <<EOFJSON
{
  "timestamp": "$TS",
  "base_dir": "$(pwd)",
  "human_context_dir": "contexts/human",
  "ai_metric_context_dir": "contexts/ai_metric",
  "bootstrap": "contexts/ai_metric/BOOTSTRAP.json",
  "probe_report": "$OUT"
}
EOFJSON

cp "$JSON" .ai/AI_BOOTSTRAP.json
cp "$OUT" .ai/LATEST_PROBE.md

echo "$OUT"
echo "$JSON"
echo ".ai/AI_BOOTSTRAP.json"
echo ".ai/LATEST_PROBE.md"
