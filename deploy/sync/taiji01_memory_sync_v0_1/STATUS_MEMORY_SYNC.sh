#!/usr/bin/env bash
set -euo pipefail
REMOTE="${TAIJI01_REMOTE:-taiji_01@192.168.50.249}"
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
FILES=(
  "data/f5_core_memory.db"
  "data/wuchang_5d_knowledge_vault.db"
  "data/ledger/metric_memory.sqlite3"
)
cd "$ROOT"
echo "== local =="
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then sha256sum "$f"; else echo "MISSING  $f"; fi
done
echo "== remote =="
ssh -o BatchMode=yes -o ConnectTimeout=8 "$REMOTE" 'cd ~/Taiji_Hub; for f in data/f5_core_memory.db data/wuchang_5d_knowledge_vault.db data/ledger/metric_memory.sqlite3; do if [ -f "$f" ]; then sha256sum "$f"; else echo "MISSING  $f"; fi; done'
