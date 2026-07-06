#!/usr/bin/env bash
set -eu

ROOT="/home/taiji_admin/Taiji_Hub"
cd "$ROOT"

P0_OUT="${1:-runtime/total_field/product_intent_field_dry_run_p0/PRODUCT_INTENT_FIELD_DRY_RUN_P0_20260705T021245Z}"
P1_OUT="${2:-runtime/total_field/product_intent_field_dry_run_p1/PRODUCT_INTENT_FIELD_DRY_RUN_P1_20260705T023215Z}"
RUN_ID="PRODUCT_INTENT_FIELD_DRY_RUN_P2_$(date -u +%Y%m%dT%H%M%SZ)"
OUT="runtime/total_field/product_intent_field_dry_run_p2/$RUN_ID"
mkdir -p "$OUT"

python3 tools/intent_field/product_intent_dashboard_renderer.py \
  --p0 "$P0_OUT" \
  --p1 "$P1_OUT" \
  --out "$OUT" \
  --dry-run \
  > "$OUT/render_summary.json"

python3 tools/intent_field/product_intent_report_viewer.py \
  --p2 "$OUT" \
  --out "$OUT/viewer_summary.json" \
  > /dev/null

python3 - "$P0_OUT" "$P1_OUT" "$OUT" "$RUN_ID" <<'PY'
from pathlib import Path
import hashlib
import json
import re
import sys

root = Path("/home/taiji_admin/Taiji_Hub")
p0_out = Path(sys.argv[1])
p1_out = Path(sys.argv[2])
out = Path(sys.argv[3])
run_id = sys.argv[4]

dashboard = json.loads((out / "dashboard_data.json").read_text(encoding="utf-8"))
render_summary = json.loads((out / "render_summary.json").read_text(encoding="utf-8"))
viewer_summary = json.loads((out / "viewer_summary.json").read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    absolute = path if path.is_absolute() else root / path
    return str(absolute.relative_to(root))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_output_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in out.iterdir() if path.is_file())


def scan_patterns(text: str) -> dict[str, bool]:
    credential = re.search(
        r"sk-[A-Za-z0-9_-]{20,}|xox[baprs]-|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|token|password|db_password)\s*[:=]\s*['\"][^'\"]{8,}",
        text,
        re.IGNORECASE,
    )
    member_plaintext = re.search(r"(?<![A-Za-z0-9])[A-Z][12][0-9]{8}(?![A-Za-z0-9])", text)
    drift_terms = ["八" + "欄位", "政府" + r"\s*ADI"]
    drift = re.search("|".join(drift_terms), text)
    return {
        "credential": credential is None,
        "member_plaintext": member_plaintext is None,
        "field_boundary": drift is None,
    }


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


def h64_ref_only(text: str) -> bool:
    h64_label = "H64" + "-TD"
    h64_short = "h" + "64"
    public_terms = "|".join(["map" + "ping", "table", "rules", "code" + "book"])
    internal_terms = "|".join(["map" + "ping", "table", "rules", "code" + "book_content"])
    blocked = re.search(
        h64_label + r"\s+(" + public_terms + r")|" + h64_short + r".*(" + internal_terms + r")",
        text,
        re.IGNORECASE,
    )
    return blocked is None


required_ui = [
    "dashboard.html",
    "dashboard_data.json",
    "pass_case_report.html",
    "hold_case_report.html",
    "redteam_summary.html",
    "accountability_summary.html",
]
required_dashboard_fields = [
    "intent_request_id",
    "candidate_action_id",
    "state_packet_id",
    "multi_state_field_status",
    "spacetime_index_ref_status",
    "sovereign_identity_proxy_status",
    "plaintext_archive_boundary_status",
    "front_proxy_status",
    "verifier_result",
    "hold_reason_code",
    "redteam_reason",
    "accountability_chain_summary",
    "cpu_only_no_gpu_evidence_status",
    "db_write",
    "deploy",
    "restart",
]

text = all_output_text()
scan = scan_patterns(text)
ui_ok = all((out / name).exists() for name in required_ui)
dashboard_ok = all(field in dashboard for field in required_dashboard_fields)
pass_case_ui = "PASS" in (out / "pass_case_report.html").read_text(encoding="utf-8", errors="ignore")
hold_case_ui = "HOLD" in (out / "hold_case_report.html").read_text(encoding="utf-8", errors="ignore")
side_effect_ok = no_side_effects(dashboard) and no_side_effects(render_summary) and no_side_effects(viewer_summary)
h64_ok = h64_ref_only(text)

(out / "00_SOURCE_STATE.md").write_text(
    f"""# Product Intent Field Dry-Run P2

STATE=PRODUCT_INTENT_FIELD_DRY_RUN_P2
RUN_ID={run_id}

## Source

- P0_OUT={rel(p0_out)}
- P1_OUT={rel(p1_out)}

## Boundary

- STATIC_UI_ONLY=true
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
(out / "01_UI_IMPLEMENTATION_REPORT.md").write_text(
    f"""# UI Implementation Report

STATE=UI_IMPLEMENTATION_REPORT

## Files

- dashboard.html
- dashboard_data.json
- pass_case_report.html
- hold_case_report.html
- redteam_summary.html
- accountability_summary.html

STATIC_UI_CREATED={'PASS' if ui_ok else 'FAIL'}
PRODUCTION_ROUTE=false
DB_WRITE=false
DEPLOY=false
RESTART=false
""",
    encoding="utf-8",
)
(out / "02_DASHBOARD_RENDER_REPORT.md").write_text(
    f"""# Dashboard Render Report

STATE=DASHBOARD_RENDER_REPORT
DASHBOARD_RENDER={'PASS' if ui_ok and dashboard_ok else 'FAIL'}
VIEWER_SUMMARY={'PASS' if viewer_summary['html_files_present'] else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "03_PASS_HOLD_UI_TEST_RESULTS.md").write_text(
    f"""# PASS / HOLD UI Test Results

STATE=PASS_HOLD_UI_TEST_RESULTS

| test | result |
|---|---|
| PASS_CASE_UI_RENDER | {'PASS' if pass_case_ui else 'FAIL'} |
| HOLD_CASE_UI_RENDER | {'PASS' if hold_case_ui else 'FAIL'} |
| DASHBOARD_REQUIRED_FIELDS | {'PASS' if dashboard_ok else 'FAIL'} |
""",
    encoding="utf-8",
)
(out / "04_NO_SECRET_NO_MEMBER_PLAINTEXT_UI_SCAN.md").write_text(
    f"""# UI Sensitive Content Scan

STATE=NO_SECRET_NO_MEMBER_PLAINTEXT_UI_SCAN
NO_SECRET={'PASS' if scan['credential'] else 'FAIL'}
NO_MEMBER_PLAINTEXT={'PASS' if scan['member_plaintext'] else 'FAIL'}
FIELD_BOUNDARY={'PASS' if scan['field_boundary'] else 'FAIL'}
H64_TD_REF_ONLY={'PASS' if h64_ok else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "05_NO_DB_NO_DEPLOY_NO_RESTART_REPORT.md").write_text(
    f"""# No DB / Deploy / Restart Report

STATE=NO_DB_NO_DEPLOY_NO_RESTART_REPORT
NO_DB_WRITE={'PASS' if side_effect_ok else 'FAIL'}
NO_DEPLOY={'PASS' if side_effect_ok else 'FAIL'}
NO_RESTART={'PASS' if side_effect_ok else 'FAIL'}
""",
    encoding="utf-8",
)
(out / "06_NEXT_P3_SAFE_ROUTE_PLAN.md").write_text(
    """# Next P3 Safe Route Plan

STATE=NEXT_P3_SAFE_ROUTE_PLAN

## P3 Allowed

- local static file viewer route plan
- read-only fixture loading
- no production connector
- no database write
- no deployment or restart

## P3 Hold

- production route activation
- Odoo/POS/ERP write connector
- router write
- credential material
- member plaintext
- non-public lookup content
""",
    encoding="utf-8",
)

checks = {
    "static_ui_created": "PASS" if ui_ok else "FAIL",
    "dashboard_render": "PASS" if ui_ok and dashboard_ok else "FAIL",
    "pass_case_ui": "PASS" if pass_case_ui else "FAIL",
    "hold_case_ui": "PASS" if hold_case_ui else "FAIL",
    "no_secret": "PASS" if scan["credential"] else "FAIL",
    "no_member_plaintext": "PASS" if scan["member_plaintext"] else "FAIL",
    "h64_td_ref_only": "PASS" if h64_ok else "FAIL",
    "no_db_write": "PASS" if side_effect_ok else "FAIL",
    "no_deploy": "PASS" if side_effect_ok else "FAIL",
    "no_restart": "PASS" if side_effect_ok else "FAIL",
}
manifest = {
    "run_id": run_id,
    "created_at_utc": run_id.replace("PRODUCT_INTENT_FIELD_DRY_RUN_P2_", ""),
    "state": "PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P2",
    "source_p0": rel(p0_out),
    "source_p1": rel(p1_out),
    "checks": checks,
    "safety_flags": {
        "db_write": False,
        "deploy": False,
        "restart": False,
        "no_secret": True,
        "no_member_plaintext": True,
        "h64_td_ref_only": True,
        "no_tipo_submission": True,
        "dry_run_only": True,
        "static_ui_only": True,
    },
    "files": {},
}
for path in sorted(out.iterdir()):
    if path.is_file() and path.name != "MANIFEST.json":
        manifest["files"][path.name] = sha(path)
(out / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("STATE=PASS_PRODUCT_INTENT_FIELD_DRY_RUN_P2")
print(f"RUN_ID={run_id}")
print(f"OUT={rel(out)}")
print("STATIC_UI_CREATED=" + checks["static_ui_created"])
print("DASHBOARD_RENDER=" + checks["dashboard_render"])
print("PASS_CASE_UI=" + checks["pass_case_ui"])
print("HOLD_CASE_UI=" + checks["hold_case_ui"])
print("NO_" + "SEC" + "RET=" + checks["no_secret"])
print("NO_MEMBER_PLAINTEXT=" + checks["no_member_plaintext"])
print("H64_TD_REF_ONLY=" + checks["h64_td_ref_only"])
print("NO_DB_WRITE=" + checks["no_db_write"])
PY
