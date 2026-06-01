#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/Taiji_Hub"

echo "===== TEFMR 7D Eight-Formation Runtime Check ====="

python3 -m json.tool "$ROOT/state/runtime_7d_state.json" >/dev/null
echo "[ok] state json"

python3 -m json.tool "$ROOT/state/runtime_7d_packet.example.json" >/dev/null
echo "[ok] packet json"

echo
echo "[state]"
cat "$ROOT/state/runtime_7d_state.json"

echo
echo "[packet]"
cat "$ROOT/state/runtime_7d_packet.example.json"

echo
echo "[audit tail]"
tail -n 5 "$ROOT/logs/runtime_7d.jsonl"
