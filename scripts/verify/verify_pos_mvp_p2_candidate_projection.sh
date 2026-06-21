#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub

export POS_P2_SEARCH_ROOT="${POS_P2_SEARCH_ROOT:-/home/taiji_admin/Taiji_Hub/runtime/sandbox/pos_mvp_autodev_run}"
export POS_P2_RUN_DIR="${POS_P2_RUN_DIR:-/home/taiji_admin/Taiji_Hub/runtime/sandbox/pos_mvp_autodev_run/POS_MVP_P2_CANDIDATE_READER}"
status_before="$(git status --short --untracked-files=all)"

out="$(python3 tools/w7tp_pos_p2_candidate_projection.py --search-root "$POS_P2_SEARCH_ROOT" --run-dir "$POS_P2_RUN_DIR")"
printf '%s\n' "$out"

grep -q "STATE=PASS_POS_P2_CANDIDATE_READER" <<<"$out"
grep -q "CONFIRM_STATE=CONFIRM_DRY_RUN" <<<"$out"
grep -q "FORMAL_DB_WRITE=false" <<<"$out"
grep -q "FORMAL_POS_WRITE=false" <<<"$out"
grep -q "PAYMENT_CAPTURE=false" <<<"$out"
grep -q "SERVICE_RESTART=false" <<<"$out"
grep -q "DEPLOY=false" <<<"$out"
grep -q "PRODUCTION_RELEASE=false" <<<"$out"
grep -q "TOTAL_FIELD_SEAL=runtime/total_field/evidence/TOTAL_FIELD_SEAL_POS_MVP_P2_CANDIDATE_READER/TOTAL_FIELD_POS_MVP_P2_CANDIDATE_READER_SEAL.json" <<<"$out"

python3 - <<'PY'
import json
from pathlib import Path

root = Path("/home/taiji_admin/Taiji_Hub")
run = root / "runtime/sandbox/pos_mvp_autodev_run/POS_MVP_P2_CANDIDATE_READER"
seal_path = root / "docs/evidence/pos_mvp_p2/POS_P2_CANDIDATE_READER_EVIDENCE_SEAL.json"
total_field_seal_path = root / "runtime/total_field/evidence/TOTAL_FIELD_SEAL_POS_MVP_P2_CANDIDATE_READER/TOTAL_FIELD_POS_MVP_P2_CANDIDATE_READER_SEAL.json"
total_field_index_path = root / "runtime/total_field/evidence/POS_MVP_P2_CANDIDATE_READER_INDEX.jsonl"
projection = json.loads((run / "projection/POS_P2_UI_PROJECTION.json").read_text(encoding="utf-8"))
confirm = json.loads((run / "confirm/POS_P2_CONFIRM_DRY_RUN.json").read_text(encoding="utf-8"))
evidence = json.loads((run / "evidence/POS_P2_CANDIDATE_READER_EVIDENCE.json").read_text(encoding="utf-8"))
seal = json.loads(seal_path.read_text(encoding="utf-8"))
total_field_seal = json.loads(total_field_seal_path.read_text(encoding="utf-8"))
html = (run / "ui/pos_p2_candidate_projection.html").read_text(encoding="utf-8")

required_projection = ["items", "subtotal", "discount", "payable_amount", "voice_reply", "rule_refs", "d8_ref"]
for key in required_projection:
    if key not in projection:
        raise SystemExit(f"projection missing {key}")
if not projection["items"]:
    raise SystemExit("projection items empty")
if projection["payable_amount"] != 235:
    raise SystemExit("payable_amount must be 235")
if confirm["state"] != "CONFIRM_DRY_RUN":
    raise SystemExit("confirm state drift")
if seal["state"] != "POS_P2_CANDIDATE_READER_EVIDENCE_SEALED":
    raise SystemExit("committed evidence seal state drift")
if seal["human_confirm_gate"] != "CONFIRM_DRY_RUN":
    raise SystemExit("committed evidence seal confirm gate drift")
if total_field_seal["state"] != "PASS_POS_P2_CANDIDATE_READER":
    raise SystemExit("total field seal state drift")
if total_field_seal["payable_amount"] != 235:
    raise SystemExit("total field payable amount drift")
if total_field_seal["runtime_output_root"] != "runtime/sandbox/pos_mvp_autodev_run":
    raise SystemExit("runtime output root drift")
if not total_field_index_path.exists() or "PASS_POS_P2_CANDIDATE_READER" not in total_field_index_path.read_text(encoding="utf-8"):
    raise SystemExit("total field index missing pass row")
for row in [projection, confirm, evidence["safety"], seal, total_field_seal]:
    for key in ["formal_db_write", "formal_pos_write", "payment_capture", "service_restart", "deploy", "production_release"]:
        if row.get(key) is not False:
            raise SystemExit(f"{key} is not false")
for key in ["secret_read", "member_plaintext_read"]:
    if seal.get(key) is not False:
        raise SystemExit(f"{key} is not false")
for phrase in ["items", "subtotal", "discount", "payable_amount", "voice_reply", "rule_refs", "d8_ref", "CONFIRM_DRY_RUN"]:
    if phrase not in html:
        raise SystemExit(f"html missing {phrase}")
print("STATE=PASS_VERIFY_POS_P2_CANDIDATE_PROJECTION")
PY

status_after="$(git status --short --untracked-files=all)"
if [[ "$status_before" != "$status_after" ]]; then
  echo "STATE=POS_P2_BASELINE_DIRTY_FAIL"
  diff -u <(printf '%s\n' "$status_before") <(printf '%s\n' "$status_after") || true
  exit 1
fi
echo "BASELINE_DIRTY=FALSE"

echo "STATE=POS_P2_CANDIDATE_PROJECTION_PASS"
