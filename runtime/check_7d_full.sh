#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/Taiji_Hub"

echo "===== 7D FULL RUNTIME CHECK ====="

check_json () {
  local file="$1"
  if [ -f "$file" ]; then
    python3 -m json.tool "$file" >/dev/null
    echo "[ok] $file"
  else
    echo "[missing] $file"
  fi
}

check_json "$ROOT/state/runtime_7d_state.json"
check_json "$ROOT/state/runtime_7d_packet.example.json"
check_json "$ROOT/state/7d_virtual_state.json"
check_json "$ROOT/policies/7d_cloud_ai_policy.json"
check_json "$ROOT/topology/7d_ai_io_odoo_metric_tensor_topology.json"

echo
echo "===== PORTS ====="
python3 - <<'PY'
import socket, json

def port_open(port):
    s = socket.socket()
    s.settimeout(0.35)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()

ports = {
    "five_metric_8105": port_open(8105),
    "odoo_8069": port_open(8069),
    "ollama_11434": port_open(11434),
    "mu_1_gateway_9004": port_open(9004),
    "formal_tensor_runtime_8126": port_open(8126)
}

print(json.dumps(ports, ensure_ascii=False, indent=2))
PY

echo
echo "===== AUDIT TAIL ====="
for f in \
  "$ROOT/logs/runtime_7d.jsonl" \
  "$ROOT/logs/7d_virtual_state.jsonl" \
  "$ROOT/logs/7d_cloud_ai_management.jsonl" \
  "$ROOT/logs/7d_topology.jsonl"
do
  echo "--- $f"
  [ -f "$f" ] && tail -n 2 "$f" || echo "[missing]"
done
