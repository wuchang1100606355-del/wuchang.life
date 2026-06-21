#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub

export POS_P2_SEARCH_ROOT="${POS_P2_SEARCH_ROOT:-/home/taiji_admin/Taiji_Hub/runtime/sandbox/pos_mvp_autodev_run}"
export POS_P2_RUN_DIR="${POS_P2_RUN_DIR:-/home/taiji_admin/Taiji_Hub/runtime/sandbox/pos_mvp_p2_projection_run}"

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

python3 - <<'PY'
import json
from pathlib import Path

root = Path("/home/taiji_admin/Taiji_Hub")
run = root / "runtime/sandbox/pos_mvp_p2_projection_run"
seal_path = root / "docs/evidence/pos_mvp_p2/POS_P2_CANDIDATE_READER_EVIDENCE_SEAL.json"
projection = json.loads((run / "projection/POS_P2_UI_PROJECTION.json").read_text(encoding="utf-8"))
confirm = json.loads((run / "confirm/POS_P2_CONFIRM_DRY_RUN.json").read_text(encoding="utf-8"))
evidence = json.loads((run / "evidence/POS_P2_CANDIDATE_READER_EVIDENCE.json").read_text(encoding="utf-8"))
seal = json.loads(seal_path.read_text(encoding="utf-8"))
html = (run / "ui/pos_p2_candidate_projection.html").read_text(encoding="utf-8")

required_projection = ["items", "subtotal", "discount", "payable_amount", "voice_reply", "rule_refs", "d8_ref"]
for key in required_projection:
    if key not in projection:
        raise SystemExit(f"projection missing {key}")
if not projection["items"]:
    raise SystemExit("projection items empty")
if confirm["state"] != "CONFIRM_DRY_RUN":
    raise SystemExit("confirm state drift")
if seal["state"] != "POS_P2_CANDIDATE_READER_EVIDENCE_SEALED":
    raise SystemExit("committed evidence seal state drift")
if seal["human_confirm_gate"] != "CONFIRM_DRY_RUN":
    raise SystemExit("committed evidence seal confirm gate drift")
for row in [projection, confirm, evidence["safety"], seal]:
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

echo "STATE=POS_P2_CANDIDATE_PROJECTION_PASS"
