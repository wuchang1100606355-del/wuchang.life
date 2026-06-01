#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PLAN="$ROOT_DIR/Taiji_Governance/system_info/host_restructure/taiji01_host_restructure_plan_2026-05-12.jsonl"

if [ ! -f "$PLAN" ]; then
  echo "missing plan: $PLAN" >&2
  echo "run BUILD_HOST_RESTRUCTURE_PLAN.sh first" >&2
  exit 1
fi

python3 - <<PY
import json
from pathlib import Path
rows = [json.loads(x) for x in Path("$PLAN").read_text(encoding="utf-8").splitlines() if x.strip()]
print("dry_run=true")
print(f"planned_files={len(rows)}")
for row in rows[:80]:
    mode = "copy" if row["copy_allowed"] else "manifest_only"
    print(f"{mode}: {row['path']} -> {row['target_path']}")
if len(rows) > 80:
    print(f"... {len(rows) - 80} more")
PY
