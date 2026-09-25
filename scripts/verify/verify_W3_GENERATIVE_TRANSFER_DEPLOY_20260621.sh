#!/usr/bin/env bash
set -euo pipefail
cd /home/taiji_admin/Taiji_Hub

python3 -m json.tool "packets/deploy/generative_transfer/W3_GENERATIVE_TRANSFER_DEPLOY_20260621.json" >/dev/null
python3 -m json.tool "packets/review/total_field/W7TP_POS_DUAL_NODE_TOTAL_FIELD_REVIEW_20260621.json" >/dev/null
python3 -m json.tool "packets/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.json" >/dev/null

grep -q "STATE=W3_GENERATIVE_TRANSFER_DEPLOY_INDEXABLE" "docs/deploy/generative_transfer/W3_GENERATIVE_TRANSFER_DEPLOY_20260621.md"
grep -q "STATE=PRODUCT_MARKET_IMPROVEMENT_GATE" "docs/deploy/generative_transfer/W3_POS_MARKET_COMPETITIVENESS_IMPROVEMENT_20260621.md"
grep -q "STATE=MERCHANT_FACING_DRY_RUN_COPY" "docs/deploy/generative_transfer/W3_POS_MERCHANT_ONE_PAGE_20260621.md"
grep -q "STATE=CLOUD_COMPUTE_LABOR_ONLY_GATE" "docs/deploy/generative_transfer/W3_CLOUD_COMPUTE_RESILIENCE_20260621.md"
grep -q "STATE=USER_STANCE_HANDHOLD_GATE" "docs/deploy/generative_transfer/W3_USER_STANCE_TOTAL_FIELD_HANDHOLD_20260621.md"
grep -q "STATE=TARGET_PLAN_TOTAL_FIELD_HANDHOLD" "docs/deploy/generative_transfer/W3_POS_TARGET_PLAN_TOTAL_FIELD_HANDHOLD_20260621.md"
grep -q "w3_generative_transfer_deploy" "packets/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.json"
grep -q "W3 Generative Transfer Deploy" "docs/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.md"

python3 - <<'PY'
import json
import re
from pathlib import Path

import yaml

root = Path("/home/taiji_admin/Taiji_Hub")
schema_files = [
    "W7TP_FIELD_ATLAS/schemas/00_schema_index.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_total_field_review_packet.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_store_node_profile.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_8d_identity_code.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_gt8d_route_packet.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_spacetime_event.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_pos_order_candidate.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_service_entitlement.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_pos_market_gate.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_cloud_compute_resilience_gate.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_user_stance_integrity_gate.schema.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_dual_node_fixture.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_market_gate_fixture.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_competitor_objection_handler.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_cloud_compute_resilience_fixture.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_user_stance_integrity_fixture.yaml",
]
for rel in schema_files:
    yaml.safe_load((root / rel).read_text(encoding="utf-8"))

review = json.loads((root / "packets/review/total_field/W7TP_POS_DUAL_NODE_TOTAL_FIELD_REVIEW_20260621.json").read_text(encoding="utf-8"))
master = json.loads((root / "packets/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.json").read_text(encoding="utf-8"))
route_table = json.loads((root / "config/gt8d_lookup/route_table.json").read_text(encoding="utf-8"))
if "w3_generative_transfer_deploy" not in master.get("indexed", {}):
    raise SystemExit("master index missing w3_generative_transfer_deploy")
if "Dual Node POS / XiaoJ Display Compute Schema" not in master.get("next_w3_items", []):
    raise SystemExit("master index next_w3_items missing dual node schema item")
valid_route_codes = {
    "PATENT_ANALYSIS",
    "ODOO_POS_ACTION",
    "VOICE_INTERACTION",
    "API_ORCHESTRATION",
    "MEMBER_SERVICE",
    "CODE_GENERATION",
    "XIAOJ_DISPLAY_COMPUTE",
}
lookup_keys = []
for route in route_table["routes"]:
    if route["route_code"] not in valid_route_codes:
        raise SystemExit(f"unregistered route code in route table: {route}")
    lookup_keys.append(route["lookup_key"])
if len(lookup_keys) != len(set(lookup_keys)):
    raise SystemExit("duplicate lookup_key in route table")
for required_key in [
    "member.service.lineworks.notify.v1",
    "pos.local.reconstruct.v1",
    "xiaoj.display.compute.v1",
]:
    if required_key not in lookup_keys:
        raise SystemExit(f"missing required lookup key: {required_key}")

opinion = review["xiaoj_review_opinion"]
for key in [
    "recommendation",
    "reason",
    "safe_option",
    "risk_if_approved",
    "risk_if_rejected",
    "required_human_action",
]:
    if not opinion.get(key):
        raise SystemExit(f"missing review opinion field: {key}")
if opinion["recommendation"] != "approve_limited":
    raise SystemExit("review recommendation must remain approve_limited")

fixture = yaml.safe_load((root / "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_dual_node_fixture.yaml").read_text(encoding="utf-8"))
market_schema = yaml.safe_load((root / "W7TP_FIELD_ATLAS/schemas/w7tp_pos_market_gate.schema.yaml").read_text(encoding="utf-8"))
market_fixture = yaml.safe_load((root / "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_market_gate_fixture.yaml").read_text(encoding="utf-8"))
objection_fixture = yaml.safe_load((root / "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_competitor_objection_handler.yaml").read_text(encoding="utf-8"))
cloud_schema = yaml.safe_load((root / "W7TP_FIELD_ATLAS/schemas/w7tp_cloud_compute_resilience_gate.schema.yaml").read_text(encoding="utf-8"))
cloud_fixture = yaml.safe_load((root / "W7TP_FIELD_ATLAS/fixtures/w7tp_cloud_compute_resilience_fixture.yaml").read_text(encoding="utf-8"))
stance_schema = yaml.safe_load((root / "W7TP_FIELD_ATLAS/schemas/w7tp_user_stance_integrity_gate.schema.yaml").read_text(encoding="utf-8"))
stance_fixture = yaml.safe_load((root / "W7TP_FIELD_ATLAS/fixtures/w7tp_user_stance_integrity_fixture.yaml").read_text(encoding="utf-8"))
for packet in fixture["route_packets"]:
    if not packet.get("candidate_only") or not packet.get("local_reconstruction_required"):
        raise SystemExit(f"route packet is not candidate-only local reconstruction: {packet}")
for candidate in fixture["pos_order_candidates"]:
    if candidate.get("land_allowed") is not False:
        raise SystemExit("pos order candidate must not be land_allowed in dry-run")
events = fixture["spacetime_events"]
for prev, current in zip(events, events[1:]):
    if current["parent_hash"] != prev["event_hash"]:
        raise SystemExit(f"hash chain break at {current['event_id']}")
allowed_labels = {"FACT", "INFERENCE", "DESIGN_PROPOSAL", "NOT_YET_VERIFIED"}
for event in events:
    if event["claim_label"] not in allowed_labels:
        raise SystemExit(f"bad claim label: {event}")
if market_fixture["product_positioning"] != "Sovereign Edge POS Ops Layer for Odoo stores":
    raise SystemExit("market fixture product positioning drift")
for gate in market_schema["required_gates"]:
    if gate not in market_fixture["market_gates"]:
        raise SystemExit(f"market gate missing from fixture: {gate}")
competitors = market_fixture.get("competitor_matrix", [])
if len(competitors) < market_schema["required_competitors_min"]:
    raise SystemExit("competitor matrix does not meet minimum coverage")
competitor_names = {row.get("competitor") for row in competitors}
for required_competitor in {
    "Odoo POS",
    "Toast",
    "Square Restaurants",
    "Lightspeed",
    "Clover",
    "TouchBistro",
    "Shopify POS",
    "SpotOn",
    "Revel",
}:
    if required_competitor not in competitor_names:
        raise SystemExit(f"required competitor missing: {required_competitor}")
for row in competitors:
    for key in ["competitor", "strongest_market_proof", "w7tp_counter_position"]:
        if not row.get(key):
            raise SystemExit(f"competitor row missing {key}: {row}")
dialogue = market_fixture.get("total_field_dialogue", {})
for key in [
    "product_redteam_question",
    "total_field_response",
    "mutual_improvement",
    "follow_up_product_redteam_question",
    "follow_up_total_field_response",
]:
    if not dialogue.get(key):
        raise SystemExit(f"total field dialogue missing: {key}")
if market_fixture.get("merchant_one_page_ref") != "docs/deploy/generative_transfer/W3_POS_MERCHANT_ONE_PAGE_20260621.md":
    raise SystemExit("merchant one-page ref missing or drifted")
if market_fixture.get("objection_handler_ref") != "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_competitor_objection_handler.yaml":
    raise SystemExit("objection handler ref missing or drifted")
one_page_text = (root / market_fixture["merchant_one_page_ref"]).read_text(encoding="utf-8")
for required_phrase in [
    "AI 只能提出候選",
    "It does not replace",
    "It does not process payments",
    "Demo Stopline",
]:
    if required_phrase not in one_page_text:
        raise SystemExit(f"merchant one-page missing phrase: {required_phrase}")
objections = objection_fixture.get("objections", [])
if len(objections) < market_schema["required_objections_min"]:
    raise SystemExit("objection handler does not meet minimum coverage")
objection_names = {row.get("competitor") for row in objections}
if not competitor_names.issubset(objection_names):
    raise SystemExit("objection handler does not cover all competitor matrix entries")
for row in objections:
    for key in ["competitor", "objection", "response", "proof_required_before_demo"]:
        if not row.get(key):
            raise SystemExit(f"objection row missing {key}: {row}")
for metric in market_schema["required_roi_metrics"]:
    if metric not in market_fixture["roi_metrics"]:
        raise SystemExit(f"ROI metric missing from fixture: {metric}")
if market_fixture["demo_stopline"]["state"] != market_schema["stopline_state"]:
    raise SystemExit("market stopline mismatch")
for forbidden_claim in market_schema["forbidden_product_claims"]:
    if forbidden_claim not in market_fixture["demo_stopline"]["applies_to"]:
        raise SystemExit(f"forbidden product claim not covered by stopline: {forbidden_claim}")
for flag, expected in [
    ("cloud_trigger_allowed", True),
    ("cloud_labor_only", True),
    ("candidate_only", True),
    ("cloud_authority", False),
    ("cloud_memory_benefit", False),
    ("cloud_data_benefit", False),
    ("land_allowed", False),
]:
    if cloud_fixture.get(flag) is not expected:
        raise SystemExit(f"cloud resilience flag drift: {flag}")
for workload in cloud_schema["required_allowed_workloads"]:
    if workload not in cloud_fixture["allowed_cloud_workloads"]:
        raise SystemExit(f"cloud allowed workload missing: {workload}")
for workload in cloud_schema["forbidden_cloud_workloads"]:
    if workload not in cloud_fixture["forbidden_cloud_workloads"]:
        raise SystemExit(f"cloud forbidden workload missing: {workload}")
for control in cloud_schema["required_capacity_controls"]:
    if control not in cloud_fixture["capacity_controls"]:
        raise SystemExit(f"cloud capacity control missing: {control}")
if cloud_fixture["capacity_controls"]["max_candidate_ttl_seconds"] > 300:
    raise SystemExit("cloud candidate ttl exceeds dry-run ceiling")
if cloud_fixture["capacity_controls"]["max_retry_count"] > 2:
    raise SystemExit("cloud retry count exceeds dry-run ceiling")
if cloud_schema["stopline_state"] != "HOLD_CLOUD_COMPUTE_BOUNDARY":
    raise SystemExit("cloud stopline drift")
for key in [
    "readonly_total_field_query_first",
    "user_stance_priority",
    "cloud_codex_gpt_candidate_only",
    "taiji01_total_field_authority",
    "no_self_invented_fact",
    "unified_questions_required_on_gap",
]:
    if stance_fixture.get(key) is not True:
        raise SystemExit(f"user stance gate flag drift: {key}")
if set(stance_schema["required_output_labels"]) != set(stance_fixture["output_label_set"]):
    raise SystemExit("user stance output label set drift")
required_options = set(stance_schema["required_next_total_field_options"])
fixture_options = set(stance_fixture["next_total_field_query"]["options"])
if required_options != fixture_options:
    raise SystemExit("NEXT_TOTAL_FIELD_QUERY options drift")
if stance_fixture["unified_question_rule"]["scattered_assumptions_allowed"] is not False:
    raise SystemExit("scattered assumptions must remain forbidden")
for flag, expected in {
    "secret_read": False,
    "member_plaintext_read": False,
    "db_write": False,
    "service_restart": False,
    "deploy": False,
    "odoo_core_mutation": False,
    "production_lineworks_action": False,
    "google_token_validation": False,
}.items():
    if stance_fixture["safety_flags"].get(flag) is not expected:
        raise SystemExit(f"user stance safety flag drift: {flag}")
if not Path(stance_fixture["source_attachment"]).exists():
    raise SystemExit("source attachment for user stance gate missing")
if "HOLD_USER_STANCE_INTEGRITY" not in (root / "docs/deploy/generative_transfer/W3_USER_STANCE_TOTAL_FIELD_HANDHOLD_20260621.md").read_text(encoding="utf-8"):
    raise SystemExit("user stance stopline missing")
target_plan = (root / "docs/deploy/generative_transfer/W3_POS_TARGET_PLAN_TOTAL_FIELD_HANDHOLD_20260621.md").read_text(encoding="utf-8")
for section in [
    "## STATE",
    "## TOTAL_FIELD_FACTS",
    "## TOTAL_FIELD_GAPS",
    "## PRODUCT_TARGET_ARCHITECTURE",
    "## SCHEMA_TARGETS",
    "## MINIMUM_RUNNABLE_MODULES",
    "## AUTOGEN_PLAN",
    "## DO_NOT_DO",
    "## NEXT_TOTAL_FIELD_QUERY",
]:
    if section not in target_plan:
        raise SystemExit(f"target plan missing section: {section}")
for option in [
    "A. POS order_candidate API",
    "B. cashier_confirm gate",
    "C. kitchen_display",
    "D. spacetime_event wrapper",
    "E. Odoo sidecar candidate",
    "F. 8D identity binding skeleton",
    "G. GT8D route table POS expansion",
]:
    if option not in target_plan:
        raise SystemExit(f"target plan missing NEXT_TOTAL_FIELD_QUERY option: {option}")
for required_phrase in [
    "Cloud compute may be triggered only as bounded labor",
    "It has no authority",
    "SIMPLIFICATION_MISSED_ALERT: Not triggered",
    "NO_SECRET_READ",
    "NO_MEMBER_PLAINTEXT_READ",
]:
    if required_phrase not in target_plan:
        raise SystemExit(f"target plan missing required phrase: {required_phrase}")
if re.search(r"^(?!(?:FACT|INFERENCE|DESIGN_PROPOSAL|NOT_YET_VERIFIED|INFO_REQUIRED|SIMPLIFICATION_MISSED_ALERT):)[^-#\n][^\n]*(?:Target product|Core value|Store flow|Member service flow|Cloud labor flow)", target_plan, re.MULTILINE):
    raise SystemExit("target plan contains unlabeled product statement")

scan_files = [
    "docs/deploy/generative_transfer/W3_GENERATIVE_TRANSFER_DEPLOY_20260621.md",
    "docs/deploy/generative_transfer/W3_POS_MARKET_COMPETITIVENESS_IMPROVEMENT_20260621.md",
    "docs/deploy/generative_transfer/W3_POS_MERCHANT_ONE_PAGE_20260621.md",
    "docs/deploy/generative_transfer/W3_CLOUD_COMPUTE_RESILIENCE_20260621.md",
    "docs/deploy/generative_transfer/W3_USER_STANCE_TOTAL_FIELD_HANDHOLD_20260621.md",
    "docs/deploy/generative_transfer/W3_POS_TARGET_PLAN_TOTAL_FIELD_HANDHOLD_20260621.md",
    "docs/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.md",
    "packets/deploy/generative_transfer/W3_GENERATIVE_TRANSFER_DEPLOY_20260621.json",
    "packets/deploy/master_index/W3_MASTER_DEPLOY_INDEX_20260613_064840.json",
    "packets/review/total_field/W7TP_POS_DUAL_NODE_TOTAL_FIELD_REVIEW_20260621.json",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_dual_node_fixture.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_total_field_review_packet.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_store_node_profile.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_8d_identity_code.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_gt8d_route_packet.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_spacetime_event.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_pos_order_candidate.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_service_entitlement.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_pos_market_gate.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_cloud_compute_resilience_gate.schema.yaml",
    "W7TP_FIELD_ATLAS/schemas/w7tp_user_stance_integrity_gate.schema.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_market_gate_fixture.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_pos_competitor_objection_handler.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_cloud_compute_resilience_fixture.yaml",
    "W7TP_FIELD_ATLAS/fixtures/w7tp_user_stance_integrity_fixture.yaml",
    "config/gt8d_lookup/route_table.json",
    "runtime/gt8d_lookup/gt8d_route_resolver.py",
]
secret_patterns = [
    "login.tailscale.com/admin/invite",
    "access_token",
    "refresh_token",
    "client_secret",
    "private_key",
    "authorization: bearer",
    "tskey-",
    "sk-",
    "application_default_credentials.json",
]
for rel in scan_files:
    text = (root / rel).read_text(encoding="utf-8").lower()
    for pattern in secret_patterns:
        if pattern in text:
            raise SystemExit(f"secret/invite pattern found in {rel}: {pattern}")
    if re.search(r"fact\s*[:=][^\n]*(64[-_ ]?gua|64 ?卦|bitmask)", text):
        raise SystemExit(f"unverified ancient-math claim written as FACT in {rel}")
    if re.search(r"(64[-_ ]?gua|64 ?卦|bitmask)[^\n]*(implemented|actual cause|已實作|工程事實)", text):
        raise SystemExit(f"unverified ancient-math claim written as FACT in {rel}")
PY

route_output="$(python3 runtime/gt8d_lookup/gt8d_route_resolver.py --route "會員要用 LINE WORKS 通知，但雲端只回候選結果，本地還原")"
grep -q "LOOKUP_KEY=member.service.lineworks.notify.v1" <<<"$route_output"
grep -q "LOCAL_RECONSTRUCTION_REQUIRED=TRUE" <<<"$route_output"
grep -q "CLOUD_RETURN_EXPECTED=candidate_result_only" <<<"$route_output"

display_output="$(python3 runtime/gt8d_lookup/gt8d_route_resolver.py --route "小J影像要用 Linux 算力節點與 Chrome 客顯外接電視")"
grep -q "LOOKUP_KEY=xiaoj.display.compute.v1" <<<"$display_output"
grep -q "LOCAL_RECONSTRUCTION_REQUIRED=TRUE" <<<"$display_output"

sha256sum -c "docs/evidence/deploy/generative_transfer/W3_GENERATIVE_TRANSFER_DEPLOY_20260621.sha256"
echo "STATE=PASS_W3_GENERATIVE_TRANSFER_DEPLOY_20260621"
