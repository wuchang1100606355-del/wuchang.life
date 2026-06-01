#!/usr/bin/env bash
set -euo pipefail
if [ "${TAIJI_ALLOW_MEMORY_PUSH_TO_01:-false}" != "true" ]; then
  echo "blocked: set TAIJI_ALLOW_MEMORY_PUSH_TO_01=true for manual governed push"
  exit 2
fi
REMOTE="${TAIJI01_REMOTE:-taiji_01@192.168.50.249}"
ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
FILES=(
  "data/f5_core_memory.db"
  "data/wuchang_5d_knowledge_vault.db"
)
cd "$ROOT"
python3 - <<'PY'
import sqlite3
from pathlib import Path
for name in ['data/f5_core_memory.db', 'data/wuchang_5d_knowledge_vault.db']:
    path = Path(name)
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    result = con.execute('pragma integrity_check').fetchone()[0]
    con.close()
    if result != 'ok':
        raise SystemExit(f'integrity_failed {name}: {result}')
    print(f'integrity {name}: {result}')
PY
ssh -o BatchMode=yes -o ConnectTimeout=8 "$REMOTE" 'mkdir -p ~/Taiji_Hub/data ~/Taiji_Hub/Taiji_Governance/backups'
for f in "${FILES[@]}"; do
  rsync -az "$f" "$REMOTE:/home/taiji_01/Taiji_Hub/$f"
done
echo "manual_push_complete"
