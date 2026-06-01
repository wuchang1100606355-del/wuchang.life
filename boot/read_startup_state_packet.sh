#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-/home/taiji_admin/Taiji_Hub}"
OUT="$ROOT/W7TP_FIELD_ATLAS/runtime_status/startup_state_packet_$(date +%Y%m%d_%H%M%S).yaml"

mkdir -p "$(dirname "$OUT")"

{
echo "packet_id: STARTUP_STATE_PACKET"
echo "timestamp: $(date -Is)"
echo "host: $(hostname)"
echo "user: $(whoami)"
echo "pwd: $(pwd)"
echo
echo "d1_identity:"
echo "  owner: CHIANG_CHENG_LUNG"
echo "  field: WUCHANG_UNIVERSE_TOTAL_FIELD"
echo "  mode: startup_readonly_state_capture"
echo
echo "d2_intent:"
echo "  purpose: read Linux startup state into W7TP field"
echo "  no_deploy: true"
echo "  no_restart: true"
echo "  no_secret_read: true"
echo
echo "d3_state:"
echo "  git_root: $(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null || echo UNKNOWN)"
echo "  git_branch: $(git -C "$ROOT" branch --show-current 2>/dev/null || echo UNKNOWN)"
echo "  git_head: $(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo UNKNOWN)"
echo
echo "d4_topology:"
echo "  docker_containers:"
docker ps --format '    - name: {{.Names}} | status: {{.Status}}' 2>/dev/null || echo "    - docker_unavailable"
echo
echo "d5_resources:"
echo "  disk:"
df -h / | awk 'NR==2 {print "    root_used: "$3"\n    root_avail: "$4"\n    root_use_percent: "$5}'
echo "  memory:"
free -h | awk '/Mem:/ {print "    mem_total: "$2"\n    mem_used: "$3"\n    mem_available: "$7}'
echo
echo "d6_governance:"
echo "  readonly: true"
echo "  no_delete: true"
echo "  no_db_write: true"
echo "  no_service_restart: true"
echo
echo "d7_validation:"
echo "  startup_packet_written: true"
echo "  output: $OUT"
} > "$OUT"

ln -sfn "$OUT" "$ROOT/W7TP_FIELD_ATLAS/runtime_status/latest_startup_state_packet.yaml"

echo "STARTUP_STATE_PACKET_WRITTEN=$OUT"
