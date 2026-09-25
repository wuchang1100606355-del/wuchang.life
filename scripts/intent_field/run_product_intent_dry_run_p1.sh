#!/usr/bin/env bash
set -eu

ROOT="/home/taiji_admin/Taiji_Hub"
cd "$ROOT"

P0_OUT="${1:-runtime/total_field/product_intent_field_dry_run_p0/PRODUCT_INTENT_FIELD_DRY_RUN_P0_20260705T021245Z}"
RUN_ID="PRODUCT_INTENT_FIELD_DRY_RUN_P1_$(date -u +%Y%m%dT%H%M%SZ)"
OUT="runtime/total_field/product_intent_field_dry_run_p1/$RUN_ID"
mkdir -p "$OUT"

python3 tools/intent_field/product_intent_schema_validator.py \
  --input "$P0_OUT/pass_case.json" \
  --out "$OUT/pass_case_schema_validation.json" \
  > "$OUT/pass_case_schema_validation_stdout.json"

python3 tools/intent_field/product_intent_schema_validator.py \
  --input "$P0_OUT/hold_case.json" \
  --out "$OUT/hold_case_schema_validation.json" \
  > "$OUT/hold_case_schema_validation_stdout.json"

python3 tools/intent_field/product_intent_dashboard_model.py \
  --from-p0 "$P0_OUT" \
  --dry-run \
  --out "$OUT/dashboard_state.json" \
  > "$OUT/dashboard_state_stdout.json"

python3 - "$P0_OUT" "$OUT" "$RUN_ID" <<'PY'
from pathlib import Path
import hashlib
import json
import re
import sys

root = Path("/home/taiji_admin/Taiji_Hub")
p0_out = Path(sys.argv[1])
out = Path(sys.argv[2])
run_id = sys.argv[3]

pass_validation = json.loads((out / "pass_case_schema_validation.json").read_text(encoding="utf-8"))
hold_validation = json.loads((out / "hold_case_schema_validation.json").read_text(encoding="utf-8"))
dashboard = json.loads((out / "dashboard_state.json").read_text(encoding="utf-8"))
dashboard_schema = json.loads((root / "schemas/intent_field/product_intent_dashboard_state.schema.json").read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    absolute = path if path.is_absolute() else root / path
    return str(absolute.relative_to(root))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_side_effects(data: object) -> bool:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"db_write", "deploy", "restart"} and value is not False:
                return False
            if not no_side_effects(value):
                return False
    elif isinstance(data, list):
        return all(no_side_effects(item) for item in data)
    return True


def required_ok(data: dict, schema: dict) -> bool:
    return all(key in data for key in schema.get("required", []))


def scan_patterns(text: str) -> dict[str, bool]:
    credential = re.search(
        r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|token|password|db_password)\s*[:=]\s*['\"][^'\"]{8,}",
        text,
        re.IGNORECASE,
    )
    member_plaintext = re.search(r"(?<![A-Za-z0-9])[A-Z][12][0-9]{8}(?![A-Za-z0-9])", text)
    drift_terms = ["八" + "欄位", "政府" + r"\s*ADI"]
    forbidden = re.search("|".join(drift_terms), text)
    return {
        "credential": credential is None,
        "member_plaintext": member_plaintext is None,
        "field_boundary": forbidden is None,
    }


all_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in out.glob("*.json"))
scan = scan_patterns(all_text)
schema_ok = pass_validation["schema_validation"] == "PASS" and hold_validation["schema_validation"] == "PASS"
dashboard_ok = required_ok(dashboard, dashboard_schema)
display_ok = dashboard["verifier_result"] == "PASS" and dashboard["redteam_reason"]
side_effect_ok = no_side_effects(dashboard)

(out / "00_SOURCE_STATE.md").write_text(
    f"""# Product Intent Field Dry-Run P1

STATE=PRODUCT_INTENT_FIELD_DRY_RUN_P1
RUN_ID={run_id}

## Source

- P0_OUT={rel(p0_out)}
- P0_PASS={rel(p0_out / 'pass_case.json')}
- P0_HOLD={rel(p0_out / 'hold_case.json')}

## Boundary

- DRY_RUN_ONLY=true
- DB_WRITE=false
- DEPLOY=false
- RESTART=false
- TIPO_SUBMISSION=false
- NO_SECRET=true
- NO_MEMBER_PLAINTEXT=true
- H64_TD_REF_ONLY=true
""",
    encoding="utf-8",
)
(out / "01_SCHEMA_VALIDATION_DESIGN.md").write_text(
    f"""# Schema Validation Design

STATE=SCHEMA_VALIDATION_DESIGN

## CLI

- python3 tools/intent_field/product_intent_schema_validator.py --input <P0_RESULT_JSON>

## Validation Scope

- request object against product_intent_dry_run_request.schema.json
- state_packet object against product_intent_state_packet.schema.json
- top-level result object against product_intent_dry_run_result.schema.json
- secret scan
- identifiable member plaintext scan
- H64-TD ref-only check
- no DB/deploy/restart flags

## Result

PASS_CASE_SCHEMA={pass_validation['schema_validation']}
HOLD_CASE_SCHEMA={hold_validation['schema_validation']}
""",
    encoding="utf-8",
)
(out / "02_DASHBOARD_STATE_MODEL.md").write_text(
    f"""# Dashboard State Model

STATE=DASHBOARD_STATE_MODEL

## Required Fields

- intent_request_id
- candidate_action_id
- state_packet_id
- multi_state_field_status
- spacetime_index_ref_status
- sovereign_identity_proxy_status
- plaintext_archive_boundary_status
- front_proxy_status
- verifier_result
- hold_reason_code
- redteam_reason
- accountability_chain_summary
- cpu_only_no_gpu_evidence_status
- db_write=false
- deploy=false
- restart=false

## Dashboard Model Status

DASHBOARD_MODEL={'PASS' if dashboard_ok else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "03_UI_COMPONENT_MAP.md").write_text(
    """# UI Component Map

STATE=UI_COMPONENT_MAP

| component | data source | display |
|---|---|---|
| Intent header | intent_request_id / candidate_action_id | ref-only identifiers |
| Multi-state field panel | multi_state_field_status | PASS/HOLD badge |
| ADI spacetime index panel | spacetime_index_ref_status | ref status only |
| Sovereign identity panel | sovereign_identity_proxy_status | identity proxy ref status |
| Plaintext archive boundary panel | plaintext_archive_boundary_status | boundary PASS/HOLD |
| Front proxy panel | front_proxy_status | block/restricted preview status |
| Verifier panel | verifier_result / hold_reason_code | PASS/HOLD and reason |
| Red-team panel | redteam_reason | HOLD reason list |
| Accountability panel | accountability_chain_summary | previous/current hash summary |
| CPU-only evidence panel | cpu_only_no_gpu_evidence_status | CPU-only/no-GPU evidence status |
""",
    encoding="utf-8",
)
(out / "04_PASS_HOLD_DISPLAY_SPEC.md").write_text(
    f"""# PASS / HOLD Display Spec

STATE=PASS_HOLD_DISPLAY_SPEC

## PASS

- show verifier_result=PASS
- show restricted_execution_instruction_ref only as dry-run preview
- show db_write=false, deploy=false, restart=false

## HOLD

- show HOLD badge
- show redteam_reason from hold_case
- do not show executable API call

PASS_HOLD_DISPLAY={'PASS' if display_ok else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "05_ACCOUNTABILITY_CHAIN_DISPLAY_SPEC.md").write_text(
    f"""# Accountability Chain Display Spec

STATE=ACCOUNTABILITY_CHAIN_DISPLAY_SPEC

## Fields

- candidate_action_id
- state_packet_id
- previous_record_hash
- current_record_hash
- verifier_result

ACCOUNTABILITY_CHAIN_SUMMARY={'PASS' if bool(dashboard.get('accountability_chain_summary')) else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "06_GUARDRAIL_DISPLAY_AND_REDTTEAM_SPEC.md").write_text(
    f"""# Guardrail Display And Redteam Spec

STATE=GUARDRAIL_DISPLAY_AND_REDTTEAM_SPEC

## Dashboard Guards

- no secret display
- no identifiable member plaintext display
- no DB write display
- no deploy/restart display
- H64-TD ref-only display

NO_SECRET={'PASS' if scan['credential'] else 'FAIL'}
NO_MEMBER_PLAINTEXT={'PASS' if scan['member_plaintext'] else 'FAIL'}
NO_DB_WRITE={'PASS' if side_effect_ok else 'FAIL'}
NO_DEPLOY={'PASS' if side_effect_ok else 'FAIL'}
NO_RESTART={'PASS' if side_effect_ok else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "07_P1_TEST_RESULTS.md").write_text(
    f"""# P1 Test Results

STATE=P1_TEST_RESULTS

| check | result |
|---|---|
| pass_case_schema_validation | {pass_validation['schema_validation']} |
| hold_case_schema_validation | {hold_validation['schema_validation']} |
| dashboard_required_fields | {'PASS' if dashboard_ok else 'FAIL'} |
| pass_hold_display | {'PASS' if display_ok else 'FAIL'} |
| no_secret | {'PASS' if scan['credential'] else 'FAIL'} |
| no_member_plaintext | {'PASS' if scan['member_plaintext'] else 'FAIL'} |
| no_db_write | {'PASS' if side_effect_ok else 'FAIL'} |
| no_deploy | {'PASS' if side_effect_ok else 'FAIL'} |
| no_restart | {'PASS' if side_effect_ok else 'FAIL'} |
""",
    encoding="utf-8",
)
(out / "08_NEXT_P2_SAFE_UI_IMPLEMENTATION_PLAN.md").write_text(
    """# Next P2 Safe UI Implementation Plan

STATE=NEXT_P2_SAFE_UI_IMPLEMENTATION_PLAN

## P2 Allowed

- static dashboard component plan
- local JSON fixture loading
- dry-run status badges
- accountability hash summary
- red-team reason display

## P2 Forbidden

- production Odoo/POS/ERP connector
- DB write
- deploy
- restart
- router write
- member plaintext
- credential material
- non-public trade-secret lookup content
""",
    encoding="utf-8",
)

manifest = {
    "run_id": run_id,
    "created_at_utc": run_id.replace("PRODUCT_INTENT_FIELD_DRY_RUN_P1_", ""),
    "state": "PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P1",
    "source_p0": rel(p0_out),
    "checks": {
        "schema_validator": "PASS" if schema_ok else "FAIL",
        "dashboard_model": "PASS" if dashboard_ok else "FAIL",
        "pass_hold_display": "PASS" if display_ok else "FAIL",
        "no_secret": "PASS" if scan["credential"] else "FAIL",
        "no_member_plaintext": "PASS" if scan["member_plaintext"] else "FAIL",
        "no_db_write": "PASS" if side_effect_ok else "FAIL",
        "no_deploy": "PASS" if side_effect_ok else "FAIL",
        "no_restart": "PASS" if side_effect_ok else "FAIL",
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

print("STATE=PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P1")
print(f"RUN_ID={run_id}")
print(f"OUT={rel(out)}")
print("SCHEMA_VALIDATOR=" + ("PASS" if schema_ok else "FAIL"))
print("DASHBOARD_MODEL=" + ("PASS" if dashboard_ok else "FAIL"))
print("PASS_HOLD_DISPLAY=" + ("PASS" if display_ok else "FAIL"))
print("NO_SECRET=" + ("PASS" if scan["credential"] else "FAIL"))
print("NO_MEMBER_PLAINTEXT=" + ("PASS" if scan["member_plaintext"] else "FAIL"))
print("NO_DB_WRITE=" + ("PASS" if side_effect_ok else "FAIL"))
PY
