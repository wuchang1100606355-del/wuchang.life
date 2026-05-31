#!/usr/bin/env bash
set -u

cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
OUT="reports/tailscale_mesh_probe_$TS.md"
JSON="reports/tailscale_status_$TS.json"

mkdir -p reports

{
echo "# Tailscale Mesh Probe"
echo
echo "timestamp: $TS"
echo "host: $(hostname)"
echo "user: $(whoami)"
echo "pwd: $(pwd)"
echo

echo "## Tailscale Version"
tailscale version 2>/dev/null || echo "tailscale_not_found"
echo

echo "## Tailscale IP"
tailscale ip -4 2>/dev/null || true
tailscale ip -6 2>/dev/null || true
echo

echo "## Tailscale Status"
tailscale status 2>/dev/null || true
echo

echo "## Tailscale Status JSON"
tailscale status --json 2>/dev/null | tee "$JSON" >/dev/null || true
[ -s "$JSON" ] && echo "json_saved: $JSON" || echo "json_not_available"
echo

echo "## Tailscale Netcheck"
tailscale netcheck 2>/dev/null || true
echo

echo "## Local Routes"
ip route 2>/dev/null || true
echo

echo "## Listening Ports Related to Taiji"
ss -lntp 2>/dev/null | grep -E ':3000|:8080|:11434|:6379|:8069|:5432|:9004|:50051' || true
echo

echo "## Docker Containers"
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || true
echo

echo "## Recommended Immediate Decision"
echo "- Do not add physical router yet."
echo "- Use taiji01 as primary subnet router candidate."
echo "- Draft ACL / Grants before adding router."
echo "- Keep cloud workers away from LAN."
} > "$OUT" 2>&1

echo "$OUT"
echo "$JSON"
