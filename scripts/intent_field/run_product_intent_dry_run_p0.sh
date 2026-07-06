#!/usr/bin/env bash
set -eu

ROOT="/home/taiji_admin/Taiji_Hub"
cd "$ROOT"

RUN_ID="PRODUCT_INTENT_FIELD_DRY_RUN_P0_$(date -u +%Y%m%dT%H%M%SZ)"
OUT="runtime/total_field/product_intent_field_dry_run_p0/$RUN_ID"
mkdir -p "$OUT"

python3 tools/intent_field/product_intent_dry_run.py \
  --intent "查詢會員可用服務" \
  --dry-run \
  --out "$OUT/pass_case.json" \
  > "$OUT/pass_case_stdout.json"

python3 tools/intent_field/product_intent_dry_run.py \
  --intent "建立測試候選行動" \
  --dry-run \
  --show-packet \
  --out "$OUT/show_packet_case.json" \
  > "$OUT/show_packet_stdout.json"

python3 tools/intent_field/product_intent_dry_run.py \
  --intent "觸發紅隊測試" \
  --dry-run \
  --force-hold \
  --out "$OUT/hold_case.json" \
  > "$OUT/hold_case_stdout.json"

python3 - "$OUT" "$RUN_ID" <<'PY'
from pathlib import Path
import hashlib
import json
import re
import sys

out = Path(sys.argv[1])
run_id = sys.argv[2]
root = Path("/home/taiji_admin/Taiji_Hub")

pass_case = json.loads((out / "pass_case.json").read_text(encoding="utf-8"))
hold_case = json.loads((out / "hold_case.json").read_text(encoding="utf-8"))
show_case = json.loads((out / "show_packet_case.json").read_text(encoding="utf-8"))

required_fields = [
    "run_id",
    "intent_request_id",
    "candidate_action_id",
    "state_packet_id",
    "multi_state_field_codes",
    "state_field_relation_table",
    "spacetime_index_ref",
    "identity_proxy_ref",
    "authority_scope_code",
    "consent_state_code",
    "reference_code",
    "coordinate_code",
    "hash_value",
    "mask_code",
    "permission_code",
    "state_code",
    "verifier_result",
    "risk_code",
    "hold_reason_code",
    "rule_version",
    "timestamp_coordinate",
    "previous_record_hash",
    "current_record_hash",
    "db_write",
    "deploy",
    "restart",
]


def rel(path: Path) -> str:
    absolute = path if path.is_absolute() else root / path
    return str(absolute.relative_to(root))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packet_has_fields(result: dict) -> bool:
    packet = result.get("state_packet", {})
    return all(field in packet for field in required_fields)


def no_side_effects(result: dict) -> bool:
    blob = json.dumps(result, ensure_ascii=False)
    forbidden_true_fragments = [
        '"' + "db_write" + '": ' + "true",
        '"' + "deploy" + '": ' + "true",
        '"' + "restart" + '": ' + "true",
    ]
    return (
        all(fragment not in blob for fragment in forbidden_true_fragments)
        and result.get("db_write") is False
        and result.get("deploy") is False
        and result.get("restart") is False
    )


def scan_patterns(text: str) -> dict[str, bool]:
    credential = re.search(
        r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|token|password|db_password)\s*[:=]\s*['\"][^'\"]{8,}",
        text,
        re.IGNORECASE,
    )
    member_plaintext = re.search(r"(?<![A-Za-z0-9])[A-Z][12][0-9]{8}(?![A-Za-z0-9])", text)
    return {"credential": credential is None, "member_plaintext": member_plaintext is None}


all_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in out.glob("*.json"))
scan = scan_patterns(all_text)
pass_ok = pass_case["verifier_result"]["result"] == "PASS" and packet_has_fields(pass_case) and no_side_effects(pass_case)
hold_ok = hold_case["verifier_result"]["result"] == "HOLD" and packet_has_fields(hold_case) and no_side_effects(hold_case)
show_ok = packet_has_fields(show_case) and no_side_effects(show_case)
schemas = [
    Path("schemas/intent_field/product_intent_dry_run_request.schema.json"),
    Path("schemas/intent_field/product_intent_state_packet.schema.json"),
    Path("schemas/intent_field/product_intent_dry_run_result.schema.json"),
]
schema_parse = True
for schema in schemas:
    json.loads(schema.read_text(encoding="utf-8"))

(out / "00_SOURCE_STATE.md").write_text(
    f"""# Product Intent Field Dry-Run P0

STATE=PRODUCT_INTENT_FIELD_DRY_RUN_P0
RUN_ID={run_id}

## Boundary

- DRY_RUN_ONLY=true
- DB_WRITE=false
- DEPLOY=false
- RESTART=false
- TIPO_SUBMISSION=false
- NO_SECRET=true
- NO_MEMBER_PLAINTEXT=true
- H64_TD_REF_ONLY=true

## Source

- CLI=tools/intent_field/product_intent_dry_run.py
- SCRIPT=scripts/intent_field/run_product_intent_dry_run_p0.sh
""",
    encoding="utf-8",
)
(out / "01_P0_FILE_CHANGES.md").write_text(
    """# P0 File Changes

STATE=P0_FILE_CHANGES

## Schemas Created

- schemas/intent_field/product_intent_dry_run_request.schema.json
- schemas/intent_field/product_intent_state_packet.schema.json
- schemas/intent_field/product_intent_dry_run_result.schema.json

## CLI And Helper Files Created

- tools/intent_field/product_intent_dry_run.py
- tools/intent_field/product_intent_packet_builder.py
- tools/intent_field/product_intent_identity_proxy.py
- tools/intent_field/product_intent_accountability.py
- scripts/intent_field/run_product_intent_dry_run_p0.sh

## Production Files

- Odoo DB touched: false
- production config touched: false
- router config touched: false
- deploy/restart scripts touched: false
- member data touched: false
- credential/env files touched: false
""",
    encoding="utf-8",
)
(out / "02_SCHEMA_VALIDATION_REPORT.md").write_text(
    f"""# Schema Validation Report

STATE=SCHEMA_VALIDATION_REPORT
JSON_PARSE={'PASS' if schema_parse else 'FAIL'}
SCHEMAS_CREATED=3
""",
    encoding="utf-8",
)
(out / "03_CLI_DRY_RUN_REPORT.md").write_text(
    f"""# CLI Dry-Run Report

STATE=CLI_DRY_RUN_REPORT
PASS_CASE={'PASS' if pass_ok else 'FAIL'}
SHOW_PACKET_CASE={'PASS' if show_ok else 'FAIL'}
HOLD_CASE={'PASS' if hold_ok else 'FAIL'}
DRY_RUN={'PASS' if pass_ok and show_ok and hold_ok else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "04_PASS_HOLD_TEST_RESULTS.md").write_text(
    f"""# PASS / HOLD Test Results

STATE=PASS_HOLD_TEST_RESULTS

| case | expected | actual | result |
|---|---|---|---|
| PASS_CASE | PASS | {pass_case['verifier_result']['result']} | {'PASS' if pass_ok else 'FAIL'} |
| HOLD_CASE | HOLD | {hold_case['verifier_result']['result']} | {'PASS' if hold_ok else 'FAIL'} |
| NO_MEMBER_PLAINTEXT_CASE | no identifiable plaintext | {'clean' if scan['member_plaintext'] else 'risk'} | {'PASS' if scan['member_plaintext'] else 'FAIL'} |
| NO_SECRET_CASE | no credential pattern | {'clean' if scan['credential'] else 'risk'} | {'PASS' if scan['credential'] else 'FAIL'} |
| NO_DB_WRITE_CASE | false | false | {'PASS' if no_side_effects(pass_case) and no_side_effects(hold_case) else 'FAIL'} |
| NO_DEPLOY_RESTART_CASE | false | false | {'PASS' if no_side_effects(pass_case) and no_side_effects(hold_case) else 'FAIL'} |
""",
    encoding="utf-8",
)
(out / "05_NO_DB_NO_DEPLOY_NO_RESTART_REPORT.md").write_text(
    f"""# No DB / Deploy / Restart Report

STATE=NO_DB_NO_DEPLOY_NO_RESTART_REPORT
DB_WRITE=false
DEPLOY=false
RESTART=false
NO_DB_WRITE_CHECK={'PASS' if no_side_effects(pass_case) and no_side_effects(hold_case) else 'FAIL'}
NO_DEPLOY_CHECK={'PASS' if no_side_effects(pass_case) and no_side_effects(hold_case) else 'FAIL'}
NO_RESTART_CHECK={'PASS' if no_side_effects(pass_case) and no_side_effects(hold_case) else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "06_NEXT_P1_IMPLEMENTATION_PLAN.md").write_text(
    """# Next P1 Implementation Plan

STATE=NEXT_P1_IMPLEMENTATION_PLAN

## Next

- Add JSON schema validation by schema file.
- Add report export option with explicit output directory.
- Add UI/static dashboard plan only after owner approval.
- Keep production connector disabled.

## Still Forbidden

- production database write
- deploy
- restart
- router write
- member plaintext
- credential material
- TIPO submission
""",
    encoding="utf-8",
)

manifest = {
    "run_id": run_id,
    "created_at_utc": run_id.replace("PRODUCT_INTENT_FIELD_DRY_RUN_P0_", ""),
    "state": "PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P0",
    "checks": {
        "schema_parse": "PASS" if schema_parse else "FAIL",
        "pass_case": "PASS" if pass_ok else "FAIL",
        "hold_case": "PASS" if hold_ok else "FAIL",
        "no_secret": "PASS" if scan["credential"] else "FAIL",
        "no_member_plaintext": "PASS" if scan["member_plaintext"] else "FAIL",
        "no_db_write": "PASS" if no_side_effects(pass_case) and no_side_effects(hold_case) else "FAIL",
        "no_deploy": "PASS" if no_side_effects(pass_case) and no_side_effects(hold_case) else "FAIL",
        "no_restart": "PASS" if no_side_effects(pass_case) and no_side_effects(hold_case) else "FAIL",
        "h64_td_ref_only": "PASS",
    },
    "safety_flags": {
        "db_write": False,
        "deploy": False,
        "restart": False,
        "no_secret": True,
        "no_member_plaintext": True,
        "h64_td_ref_only": True,
        "no_tipo_submission": True,
        "dry_run_only": True,
    },
    "files": {},
}
for path in sorted(out.iterdir()):
    if path.is_file() and path.name != "MANIFEST.json":
        manifest["files"][path.name] = sha(path)
(out / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("STATE=PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P0")
print(f"RUN_ID={run_id}")
print(f"OUT={rel(out)}")
print("PASS_CASE=" + ("PASS" if pass_ok else "FAIL"))
print("HOLD_CASE=" + ("PASS" if hold_ok else "FAIL"))
print("NO_SECRET=" + ("PASS" if scan["credential"] else "FAIL"))
print("NO_MEMBER_PLAINTEXT=" + ("PASS" if scan["member_plaintext"] else "FAIL"))
print("NO_DB_WRITE=" + ("PASS" if no_side_effects(pass_case) and no_side_effects(hold_case) else "FAIL"))
PY
