#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
INV_DIR="$ROOT_DIR/Taiji_Governance/system_info/host_restructure"
INVENTORY="$INV_DIR/latest_inventory.jsonl"
PLAN="$INV_DIR/taiji01_host_restructure_plan_2026-05-12.jsonl"
SUMMARY="$INV_DIR/taiji01_host_restructure_plan_2026-05-12.md"
TARGET_ROOT="${TAIJI_HOST_TARGET_ROOT:-$HOME/Taiji_System_Host}"

if [ ! -f "$INVENTORY" ]; then
  echo "missing inventory: $INVENTORY" >&2
  echo "run HOST_READONLY_INVENTORY.sh first" >&2
  exit 1
fi

: > "$PLAN"

python3 - <<PY
import json
from pathlib import Path

target_root = "$TARGET_ROOT"
mapping = {
    "governance": "governance",
    "deploy": "deploy",
    "runtime": "runtime",
    "schemas_examples": "schemas",
    "docs_site": "docs",
    "source_archive_review": "archive/source_review",
    "model_definition": "runtime/model_definitions",
    "local_state_review": "controlled_manifest_only",
    "review": "archive/review",
}

with Path("$PLAN").open("w", encoding="utf-8") as out:
    for line in Path("$INVENTORY").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        category = row["category"]
        target_group = mapping.get(category, "archive/review")
        copy_allowed = category not in {"local_state_review"}
        record = {
            **row,
            "target_root": target_root,
            "target_group": target_group,
            "target_path": f"{target_root}/{target_group}/{row['path']}",
            "copy_allowed": copy_allowed,
            "reverse_sync_allowed": False,
            "apply_requires": "APPLY=1",
            "rollback": "remove created target copy only; source is never deleted",
        }
        out.write(json.dumps(record, ensure_ascii=False) + "\n")

rows = [json.loads(x) for x in Path("$PLAN").read_text(encoding="utf-8").splitlines() if x.strip()]
allowed = sum(1 for r in rows if r["copy_allowed"])
Path("$SUMMARY").write_text(f"""# taiji01 Host Restructure Plan

```text
target_root={target_root}
files={len(rows)}
copy_allowed={allowed}
copy_blocked_manifest_only={len(rows) - allowed}
plan=$PLAN
```

## Rule

Source files are never deleted. Apply mode only creates target folders and copies allowed files.

Restricted local state is represented by manifest only.
""", encoding="utf-8")
print(f"plan=$PLAN")
print(f"summary=$SUMMARY")
print(f"files={len(rows)}")
print(f"copy_allowed={allowed}")
PY
