#!/usr/bin/env bash
set -euo pipefail

if [ "${APPLY:-0}" != "1" ]; then
  echo "blocked: set APPLY=1 to apply host restructure" >&2
  exit 1
fi

metric_write=false
if [ "${TAIJI_METRIC_GOVERNED_WRITE:-0}" = "1" ]; then
  metric_write=true
fi

if [ "$metric_write" = false ] && [ "${TAIJI_LOCAL_WRITE_WINDOW:-0}" != "1" ]; then
  echo "blocked: system host write requires TAIJI_LOCAL_WRITE_WINDOW=1 or metric-governed write" >&2
  exit 1
fi

if [ "$metric_write" = true ]; then
  if [ "${TAIJI_METRIC_GATE_DECISION:-}" != "allow_with_audit" ]; then
    echo "blocked: metric-governed write requires TAIJI_METRIC_GATE_DECISION=allow_with_audit" >&2
    exit 1
  fi
  if [ -z "${TAIJI_METRIC_WRITE_MANIFEST:-}" ] || [ ! -f "$TAIJI_METRIC_WRITE_MANIFEST" ]; then
    echo "blocked: metric-governed write requires TAIJI_METRIC_WRITE_MANIFEST pointing to an approved manifest" >&2
    exit 1
  fi
fi

if [ "${TAIJI_REMOTE_AUTOMATED_WRITE:-0}" = "1" ] && [ "$metric_write" = false ]; then
  echo "blocked: ungoverned remote automated write to system host is L3_metric_hazard" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PLAN="$ROOT_DIR/Taiji_Governance/system_info/host_restructure/taiji01_host_restructure_plan_2026-05-12.jsonl"
APPLY_LOG="$ROOT_DIR/Taiji_Governance/logs/taiji01_host_restructure_apply_2026-05-12.jsonl"
CREATED="$ROOT_DIR/Taiji_Governance/system_info/host_restructure/taiji01_host_restructure_created_2026-05-12.txt"

if [ ! -f "$PLAN" ]; then
  echo "missing plan: $PLAN" >&2
  exit 1
fi

: > "$CREATED"
mkdir -p "$(dirname "$APPLY_LOG")"

python3 - <<PY
import json
import shutil
from pathlib import Path

root = Path("$ROOT_DIR")
created = Path("$CREATED")
with Path("$PLAN").open(encoding="utf-8") as handle:
    rows = [json.loads(x) for x in handle if x.strip()]
for row in rows:
    if not row["copy_allowed"]:
        continue
    src = root / row["path"]
    dst = Path(row["target_path"])
    if not src.exists():
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    with created.open("a", encoding="utf-8") as out:
        out.write(str(dst) + "\n")
print(f"created_manifest={created}")
PY

python3 - <<PY >> "$APPLY_LOG"
import json
from datetime import datetime, timezone, timedelta
print(json.dumps({
    "event": "taiji01_host_restructure_applied",
    "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    "plan": "$PLAN",
    "created_manifest": "$CREATED",
    "source_deleted": False,
    "secret_material_printed": False,
    "external_api_called": False,
    "live_deploy_executed": False,
    "risk_level": "L1_near"
}, ensure_ascii=False))
PY
