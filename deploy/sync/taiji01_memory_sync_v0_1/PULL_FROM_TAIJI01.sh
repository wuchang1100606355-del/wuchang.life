#!/usr/bin/env bash
set -euo pipefail
REMOTE="${TAIJI01_REMOTE:-taiji_01@192.168.50.249}"
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
TS="$(date +%Y%m%dT%H%M%S%z)"
BACKUP="$ROOT/Taiji_Governance/backups/memory_cache_before_pull_$TS"
FILES=(
  "data/f5_core_memory.db"
  "data/wuchang_5d_knowledge_vault.db"
)
cd "$ROOT"
mkdir -p "$BACKUP" data
python3 - <<'PY'
print('preflight=pull_from_taiji01_no_secrets')
PY
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    mkdir -p "$BACKUP/$(dirname "$f")"
    cp -a "$f" "$BACKUP/$f"
  fi
  mkdir -p "$(dirname "$f")"
  rsync -az "$REMOTE:/home/taiji_01/Taiji_Hub/$f" "$f"
done
python3 - <<'PY'
import sqlite3
from pathlib import Path
for name in ['data/f5_core_memory.db', 'data/wuchang_5d_knowledge_vault.db']:
    path = Path(name)
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    result = con.execute('pragma integrity_check').fetchone()[0]
    con.close()
    print(f'integrity {name}: {result}')
PY
echo "backup=$BACKUP"
echo "pull_complete"
