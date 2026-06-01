#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$ROOT_DIR/Taiji_Governance/system_info/host_restructure"
OUT_FILE="$OUT_DIR/taiji01_host_inventory_${TS}.jsonl"
SUMMARY="$OUT_DIR/taiji01_host_inventory_${TS}.md"
LATEST="$OUT_DIR/latest_inventory.jsonl"
AUDIT="$ROOT_DIR/Taiji_Governance/logs/taiji01_host_restructure_2026-05-12.jsonl"

mkdir -p "$OUT_DIR" "$(dirname "$AUDIT")"
: > "$OUT_FILE"

is_excluded() {
  local rel="$1"
  case "$rel" in
    .git/*|.ssh/*|.secrets/*|keys/*|*token*|*secret*|*credential*|*credentials*|*service_account*.json|*oauth*.json|*.pem|*.key|*.env|.env|Taiji_Odoo/postgres_data/*|Taiji_Odoo/odoo_data/*|open_webui_data/*|node_modules/*|.venv*/*|taiji_env/*|*/__pycache__/*|.pytest_cache/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

classify() {
  local rel="$1"
  case "$rel" in
    Taiji_Governance/*) echo "governance" ;;
    deploy/*|scripts/*|systemd/*) echo "deploy" ;;
    runtime_adapters/*|services/gateway/*|Taiji_Vector_Runtime_Lite/*) echo "runtime" ;;
    schemas/*|examples/*) echo "schemas_examples" ;;
    docs/*|site/*) echo "docs_site" ;;
    legacy_core/*|core/*|edge/*|Taiji_AutoBuild/*) echo "source_archive_review" ;;
    models/*) echo "model_definition" ;;
    data/*|logs/*|audit/*|runtime/*) echo "local_state_review" ;;
    *) echo "review" ;;
  esac
}

cd "$ROOT_DIR"

find . -maxdepth 5 -type f 2>/dev/null | sed 's#^\./##' | sort | while IFS= read -r rel; do
  if is_excluded "$rel"; then
    continue
  fi
  size="$(stat -c '%s' "$rel" 2>/dev/null || echo 0)"
  sha="pending_large_or_review"
  if [ "$size" -le 10485760 ]; then
    sha="sha256:$(sha256sum "$rel" | awk '{print $1}')"
  fi
  category="$(classify "$rel")"
  python3 - <<PY >> "$OUT_FILE"
import json
print(json.dumps({
    "path": "$rel",
    "size_bytes": int("$size"),
    "category": "$category",
    "sha256": "$sha",
    "secret_material_included": False,
    "member_plaintext_included": False,
    "five_code": {
        "intent": "host_file_restructure_inventory",
        "resource": "file_metadata_only",
        "time": "pre_apply_readonly",
        "authority": "audit_before_restructure",
        "topology": "taiji01_or_local_host_to_taiji_system_host_layout"
    }
}, ensure_ascii=False))
PY
done

cp "$OUT_FILE" "$LATEST"

python3 - <<PY
import json
from pathlib import Path
rows = [json.loads(x) for x in Path("$OUT_FILE").read_text(encoding="utf-8").splitlines() if x.strip()]
total = sum(r["size_bytes"] for r in rows)
by_cat = {}
for row in rows:
    by_cat[row["category"]] = by_cat.get(row["category"], 0) + 1
Path("$SUMMARY").write_text("# taiji01 Host Inventory\n\n```text\nfiles=%d\ntotal_bytes=%d\ninventory=%s\n```\n\n## Category Counts\n\n%s\n" % (
    len(rows),
    total,
    "$OUT_FILE",
    "\n".join(f"- {k}: {v}" for k, v in sorted(by_cat.items())),
), encoding="utf-8")
print(f"inventory=$OUT_FILE")
print(f"summary=$SUMMARY")
print(f"files={len(rows)}")
print(f"total_bytes={total}")
PY

python3 - <<PY >> "$AUDIT"
import json
from datetime import datetime, timezone, timedelta
print(json.dumps({
    "event": "taiji01_host_readonly_inventory",
    "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(),
    "inventory": "$OUT_FILE",
    "secret_material_printed": False,
    "credential_material_read": False,
    "external_api_called": False,
    "live_deploy_executed": False,
    "risk_level": "L0_exact_match"
}, ensure_ascii=False))
PY
