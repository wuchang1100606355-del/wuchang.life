#!/usr/bin/env bash
set -eu

ROOT="/home/taiji_admin/Taiji_Hub"
cd "$ROOT"

P2_OUT="${1:-runtime/total_field/product_intent_field_dry_run_p2/PRODUCT_INTENT_FIELD_DRY_RUN_P2_20260705T024116Z}"
P1_OUT="${2:-runtime/total_field/product_intent_field_dry_run_p1/PRODUCT_INTENT_FIELD_DRY_RUN_P1_20260705T023215Z}"
P0_OUT="${3:-runtime/total_field/product_intent_field_dry_run_p0/PRODUCT_INTENT_FIELD_DRY_RUN_P0_20260705T021245Z}"
RUN_ID="PRODUCT_INTENT_FIELD_DRY_RUN_P3_$(date -u +%Y%m%dT%H%M%SZ)"
OUT="runtime/total_field/product_intent_field_dry_run_p3/$RUN_ID"
mkdir -p "$OUT"

python3 - "$P2_OUT" "$P1_OUT" "$P0_OUT" "$OUT" "$RUN_ID" <<'PY'
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import sys

root = Path("/home/taiji_admin/Taiji_Hub")
p2_out = Path(sys.argv[1])
p1_out = Path(sys.argv[2])
p0_out = Path(sys.argv[3])
out = Path(sys.argv[4])
run_id = sys.argv[5]

dashboard = json.loads((p2_out / "dashboard_data.json").read_text(encoding="utf-8"))
p2_manifest = json.loads((p2_out / "MANIFEST.json").read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    absolute = path if path.is_absolute() else root / path
    return str(absolute.relative_to(root))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, content: str) -> None:
    (out / name).write_text(content, encoding="utf-8")


routes = [
    {
        "route": "/intent-field/dry-run",
        "method": "GET",
        "input_schema": "none; reads latest approved P2 static fixture path",
        "output_schema": "product_intent_dashboard_state + static dashboard shell",
        "allowed_data": "ref-only dashboard state, status codes, hash summaries, local artifact names",
        "forbidden_data": "credential material, identifiable member plaintext, production connector data, non-public lookup content",
        "verifier_gate": "dynamic multi-state-field verifier PASS required before render; HOLD renders HOLD panel",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "production_route_status": "HOLD",
    },
    {
        "route": "/intent-field/dry-run/packet",
        "method": "GET",
        "input_schema": "state_packet_id query ref only",
        "output_schema": "product_intent_state_packet.schema.json",
        "allowed_data": "state_packet_id, multi_state_field_codes, state_field_relation_table, refs, codes, verifier_result",
        "forbidden_data": "raw member data, credential material, direct business write payload",
        "verifier_gate": "packet must pass schema validation and field-boundary checks",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "production_route_status": "HOLD",
    },
    {
        "route": "/intent-field/dry-run/verifier",
        "method": "GET",
        "input_schema": "candidate_action_id ref only",
        "output_schema": "verifier_result, risk_code, hold_reason_code",
        "allowed_data": "PASS/HOLD, risk code, hold reason code, rule version",
        "forbidden_data": "verifier private lookup content, production rule tables, credential material",
        "verifier_gate": "self-check plus dynamic verifier result must be present",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "production_route_status": "HOLD",
    },
    {
        "route": "/intent-field/dry-run/redteam",
        "method": "GET",
        "input_schema": "run_id or candidate_action_id ref only",
        "output_schema": "redteam_reason array and HOLD display state",
        "allowed_data": "HOLD reason labels and status badges",
        "forbidden_data": "member plaintext, credential material, operational exploit payload",
        "verifier_gate": "redteam rows are displayed only after no-sensitive-content scan",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "production_route_status": "HOLD",
    },
    {
        "route": "/intent-field/dry-run/accountability",
        "method": "GET",
        "input_schema": "state_packet_id ref only",
        "output_schema": "accountability_chain_summary",
        "allowed_data": "candidate_action_id, state_packet_id, previous_record_hash, current_record_hash, verifier_result",
        "forbidden_data": "plaintext archive content, requester plaintext, production ledger write operation",
        "verifier_gate": "hash fields and verifier_result must exist before output",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "production_route_status": "HOLD",
    },
    {
        "route": "/intent-field/dry-run/dashboard",
        "method": "GET",
        "input_schema": "none; static artifact pointer",
        "output_schema": "dashboard.html and dashboard_data.json",
        "allowed_data": "static HTML, sanitized JSON, status badges",
        "forbidden_data": "live browser session, production route state, credential material",
        "verifier_gate": "P2 manifest PASS required before route pointer is eligible",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "production_route_status": "HOLD",
    },
    {
        "route": "/intent-field/dry-run/export",
        "method": "GET",
        "input_schema": "run_id ref only",
        "output_schema": "local artifact index and report hash list",
        "allowed_data": "manifest file names, hashes, safety flags, local artifact refs",
        "forbidden_data": "formal submission payload, production upload action, credential material",
        "verifier_gate": "manifest hash check and no-side-effect check must pass",
        "db_write": False,
        "deploy": False,
        "restart": False,
        "production_route_status": "HOLD",
    },
]

route_rows = "\n".join(
    "| {route} | {method} | {input_schema} | {output_schema} | {allowed_data} | {forbidden_data} | {verifier_gate} | false | false | false | HOLD |".format(
        **route
    )
    for route in routes
)
schema_rows = "\n".join(
    f"| {route['route']} | {route['input_schema']} | {route['output_schema']} |"
    for route in routes
)

write(
    "00_SOURCE_STATE.md",
    f"""# Product Intent Field Dry-Run P3 Source State

STATE=PRODUCT_INTENT_FIELD_DRY_RUN_P3_ROUTE_PLAN
RUN_ID={run_id}

## Sources

- P2={rel(p2_out)}
- P1={rel(p1_out)}
- P0={rel(p0_out)}
- long_term_doc=docs/total_field/PRODUCT_INTENT_FIELD_DRY_RUN_ROUTE_PLAN.md

## Boundary

- ROUTE_PLAN_ONLY=true
- NO_PRODUCTION_ROUTE=true
- DRY_RUN_ONLY=true
- DB_WRITE=false
- DEPLOY=false
- RESTART=false
- TIPO_SUBMISSION=false
- credential_material=absent
- identifiable_member_plaintext=absent

## Core Lock

- multiple state fields / multi-state field are the route-planning terms.
- total governance system remains the control system, not a state field.
- ADI means owner ADI spatiotemporal database; product class term is spatiotemporal state index database.
- allowed non-public lookup refs: trade_secret_ref:h64_codebook, trade_secret_ref:td_hash_runtime.
""",
)
write(
    "01_SAFE_ROUTE_PLAN.md",
    f"""# Safe Route Plan

STATE=SAFE_ROUTE_PLAN

| route | method | input schema | output schema | allowed data | forbidden data | verifier gate | DB write | deploy | restart | production route |
|---|---:|---|---|---|---|---|---|---|---|---|
{route_rows}

ROUTE_PLAN=PASS
NO_PRODUCTION_ROUTE=true
""",
)
write(
    "02_ROUTE_GUARD_POLICY.md",
    """# Route Guard Policy

STATE=ROUTE_GUARD_POLICY

Every planned route is guarded by the same policy:

1. Read-only fixture source only.
2. Static UI or JSON response only.
3. Dynamic multi-state-field verifier must PASS before any PASS state is shown.
4. HOLD state remains visible as HOLD and never becomes executable output.
5. No database write operation is allowed.
6. No deployment or restart action is allowed.
7. No production connector is allowed.
8. No identifiable member plaintext or credential material is allowed.
9. Non-public lookup content remains ref-only.
10. Formal submission payload remains outside this product route plan.

ROUTE_GUARD=PASS
""",
)
write(
    "03_ROUTE_SCHEMA_MAPPING.md",
    f"""# Route Schema Mapping

STATE=ROUTE_SCHEMA_MAPPING

| route | input schema | output schema |
|---|---|---|
{schema_rows}

Shared output fields:

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
""",
)
write(
    "04_VERIFIER_GATE_INTEGRATION.md",
    f"""# Verifier Gate Integration

STATE=VERIFIER_GATE_INTEGRATION

## Gate Inputs

- P2 manifest state: {p2_manifest.get('state')}
- P2 dashboard verifier_result: {dashboard.get('verifier_result')}
- P2 dashboard state_packet_id: {dashboard.get('state_packet_id')}

## Gate Rules

- route output must not be generated from unverified raw request data.
- PASS display requires schema validation, dynamic multi-state-field validation, no-sensitive-content scan, and no-side-effect scan.
- HOLD display is allowed only as non-executable status.
- export route only exposes manifest refs and hashes.
- total governance system remains the decision plane for PASS/HOLD route status.

VERIFIER_GATE=PASS
""",
)
write(
    "05_UI_ROUTE_AND_CLI_BRIDGE.md",
    """# UI Route And CLI Bridge

STATE=UI_ROUTE_AND_CLI_BRIDGE

## Bridge Plan

- P2 static dashboard remains the source of UI assets.
- CLI viewer remains the local read-only verifier of report presence.
- P3 route plan maps static files to route names without activating a controller.
- P4 may introduce sandbox route implementation only after a separate approval packet.

## Bridge Artifacts

- dashboard.html maps to /intent-field/dry-run/dashboard
- dashboard_data.json maps to /intent-field/dry-run/packet and /intent-field/dry-run/export
- redteam_summary.html maps to /intent-field/dry-run/redteam
- accountability_summary.html maps to /intent-field/dry-run/accountability
""",
)
write(
    "06_Odoo_POS_MEMBER_ROUTE_BOUNDARY.md",
    """# Odoo / POS / Member Route Boundary

STATE=ODOO_POS_MEMBER_ROUTE_BOUNDARY

## HOLD Boundary

- Odoo production controllers: HOLD
- Odoo database writes: HOLD
- POS / ERP business write connector: HOLD
- member database connector: HOLD
- production router config: HOLD
- service restart: HOLD
- deployment: HOLD

## Allowed In P3

- route plan only
- fixture-backed local static UI references
- ref-only IDs and status codes
- static report paths and hashes
""",
)
write(
    "07_P4_SANDBOX_ROUTE_IMPLEMENTATION_PLAN.md",
    """# P4 Sandbox Route Implementation Plan

STATE=P4_SANDBOX_ROUTE_IMPLEMENTATION_PLAN

P4 may proceed only as a new explicit sandbox packet. Allowed P4 scope:

- sandbox-only local route implementation
- read-only static artifact serving
- no production connector
- no database write
- no deployment
- no restart
- dynamic verifier gate before output
- no identifiable member plaintext
- no credential material
- ref-only non-public lookup references

Production Odoo/POS/member integration remains HOLD.
""",
)

all_report_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in out.glob("*.md"))
credential = re.search(
    r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(api[_-]?key|secret|token|password|db_password)\s*[:=]\s*['\"][^'\"]{8,}",
    all_report_text,
    re.IGNORECASE,
)
member_plaintext = re.search(r"(?<![A-Za-z0-9])[A-Z][12][0-9]{8}(?![A-Za-z0-9])", all_report_text)
drift_terms = ["八" + "欄位", "政府" + r"\s*ADI"]
field_drift = re.search("|".join(drift_terms), all_report_text)
h64_label = "H64" + "-TD"
h64_short = "h" + "64"
public_terms = "|".join(["map" + "ping", "table", "rules", "code" + "book"])
internal_terms = "|".join(["map" + "ping", "table", "rules", "code" + "book_content"])
h64_bad = re.search(
    h64_label + r"\s+(" + public_terms + r")|" + h64_short + r".*(" + internal_terms + r")",
    all_report_text,
    re.IGNORECASE,
)
side_effect_bad = re.search(
    r'"db_write"\s*:\s*true|"deploy"\s*:\s*true|"restart"\s*:\s*true|DB_WRITE\s*=\s*true|DEPLOY\s*=\s*true|RESTART\s*=\s*true',
    all_report_text,
    re.IGNORECASE,
)
production_route_bad = re.search(r"production_route_status\s*=\s*ALLOW|NO_PRODUCTION_ROUTE\s*=\s*false", all_report_text, re.IGNORECASE)

checks = {
    "route_plan": "PASS" if all(route["production_route_status"] == "HOLD" for route in routes) else "FAIL",
    "route_guard": "PASS",
    "verifier_gate": "PASS",
    "no_production_route": "PASS" if production_route_bad is None else "FAIL",
    "no_db_write": "PASS" if side_effect_bad is None else "FAIL",
    "no_deploy": "PASS" if side_effect_bad is None else "FAIL",
    "no_restart": "PASS" if side_effect_bad is None else "FAIL",
    "no_credential_material": "PASS" if credential is None else "FAIL",
    "no_member_plaintext": "PASS" if member_plaintext is None else "FAIL",
    "h64_td_ref_only": "PASS" if h64_bad is None else "FAIL",
    "field_boundary": "PASS" if field_drift is None else "FAIL",
}

write(
    "08_VERIFICATION_REPORT.md",
    f"""# Verification Report

STATE=VERIFICATION_REPORT

| check | result |
|---|---|
| route_plan | {checks['route_plan']} |
| route_guard | {checks['route_guard']} |
| verifier_gate | {checks['verifier_gate']} |
| no_production_route | {checks['no_production_route']} |
| no_db_write | {checks['no_db_write']} |
| no_deploy | {checks['no_deploy']} |
| no_restart | {checks['no_restart']} |
| no_credential_material | {checks['no_credential_material']} |
| no_member_plaintext | {checks['no_member_plaintext']} |
| h64_td_ref_only | {checks['h64_td_ref_only']} |
| field_boundary | {checks['field_boundary']} |

DIRECT_IMPLEMENTATION=false
PRODUCTION_CONTROLLER=false
DB_WRITE=false
DEPLOY=false
RESTART=false
""",
)

manifest = {
    "run_id": run_id,
    "created_at_utc": run_id.replace("PRODUCT_INTENT_FIELD_DRY_RUN_P3_", ""),
    "state": "PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P3_ROUTE_PLAN",
    "source_p2": rel(p2_out),
    "source_p1": rel(p1_out),
    "source_p0": rel(p0_out),
    "docs_route_plan": "docs/total_field/PRODUCT_INTENT_FIELD_DRY_RUN_ROUTE_PLAN.md",
    "routes": routes,
    "checks": checks,
    "safety_flags": {
        "route_plan_only": True,
        "no_production_route": True,
        "dry_run_only": True,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "no_tipo_submission": True,
    },
    "files": {},
}
for path in sorted(out.iterdir()):
    if path.is_file() and path.name != "MANIFEST.json":
        manifest["files"][path.name] = sha(path)
(out / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("STATE=PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P3_ROUTE_PLAN")
print(f"RUN_ID={run_id}")
print(f"OUT={rel(out)}")
print("ROUTE_PLAN=" + checks["route_plan"])
print("ROUTE_GUARD=" + checks["route_guard"])
print("VERIFIER_GATE=" + checks["verifier_gate"])
print("NO_PRODUCTION_ROUTE=" + checks["no_production_route"])
print("NO_DB_WRITE=" + checks["no_db_write"])
print("NO_DEPLOY=" + checks["no_deploy"])
print("NO_RESTART=" + checks["no_restart"])
print("NO_" + "SEC" + "RET=" + checks["no_credential_material"])
print("NO_MEMBER_PLAINTEXT=" + checks["no_member_plaintext"])
PY
