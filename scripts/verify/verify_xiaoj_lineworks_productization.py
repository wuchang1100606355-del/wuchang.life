#!/usr/bin/env python3
"""Verify XiaoJ LINE WORKS productization without external calls or secrets."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"
CONNECTOR = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_connector.py"
ACTIVATION_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_activation.py"
RELEASE_REFS_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_release_refs.py"
HANDOFF_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_handoff.py"
RUNTIME_RESOLVER_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_runtime_resolver.py"
CONTRACT = ROOT / "packets/product_av_ordering_ai/lineworks_notification_gate_contract.json"
RELEASE_TEMPLATE = ROOT / "packets/product_av_ordering_ai/lineworks_release_refs_template.json"
DOC = ROOT / "docs/product/XIAOJ_LINE_WORKS_PRODUCTIZATION_PLAN.md"
GUIDE = ROOT / "docs/product/XIAOJ_LINE_WORKS_OPERATOR_GUIDE.html"
API_CTRL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
MODEL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/lineworks_notification.py"
MODEL_INIT = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/__init__.py"
MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/__manifest__.py"
ACCESS = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/security/ir.model.access.csv"
VIEW = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/lineworks_notification_views.xml"
READINESS_TOOL = ROOT / "tools/xiaoj_lineworks_release_readiness.py"
EXPORT_TOOL = ROOT / "tools/xiaoj_lineworks_execution_envelope_export.py"
BUILDER_TOOL = ROOT / "tools/xiaoj_lineworks_release_refs_builder.py"
ACTIVATION_TOOL = ROOT / "tools/xiaoj_lineworks_runtime_activation_builder.py"
HANDOFF_TOOL = ROOT / "tools/xiaoj_lineworks_operator_handoff_pack.py"
RUNTIME_RESOLVER_TOOL = ROOT / "tools/xiaoj_lineworks_runtime_resolver_contract_builder.py"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"import_spec_missing:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def verified_ref(gate_id: str, ref: str) -> dict:
    return {
        "ref": f"TEST_VERIFIED_REF_{gate_id}_{ref}".upper(),
        "packet_hash": "b" * 64,
        "verifier": "total_field_release_registry",
        "verified": True,
    }


def main() -> int:
    engine = load_module("p1_intent_engine_lineworks_verify", ENGINE)
    connector = load_module("lineworks_connector_verify", CONNECTOR)

    contract = json.loads(read(CONTRACT))
    release_template = json.loads(read(RELEASE_TEMPLATE))
    if contract.get("candidate_api") != "/wuchang/xiaoj/api/lineworks-notify":
        fail("candidate_api_wrong")
    if contract.get("send_preflight_api") != "/wuchang/xiaoj/api/lineworks-send-preflight":
        fail("send_preflight_api_wrong")
    if contract.get("release_refs_draft_api") != "/wuchang/xiaoj/api/lineworks-release-refs-draft":
        fail("release_refs_draft_api_wrong")
    if contract.get("execution_envelope_api") != "/wuchang/xiaoj/api/lineworks-execution-envelope":
        fail("execution_envelope_api_wrong")
    if contract.get("runtime_dry_run_api") != "/wuchang/xiaoj/api/lineworks-runtime-dry-run":
        fail("runtime_dry_run_api_wrong")
    if contract.get("runtime_activation_draft_api") != "/wuchang/xiaoj/api/lineworks-runtime-activation-draft":
        fail("runtime_activation_draft_api_wrong")
    if contract.get("operator_handoff_api") != "/wuchang/xiaoj/api/lineworks-operator-handoff":
        fail("operator_handoff_api_wrong")
    if contract.get("operator_handoff_api_auth") != "user":
        fail("operator_handoff_api_auth_wrong")
    if contract.get("runtime_resolver_contract_api") != "/wuchang/xiaoj/api/lineworks-runtime-resolver-contract":
        fail("runtime_resolver_contract_api_wrong")
    if contract.get("runtime_resolver_contract_api_auth") != "user":
        fail("runtime_resolver_contract_api_auth_wrong")
    if contract.get("p1_side_effects", {}).get("external_api_call") is not False:
        fail("contract_external_api_call_not_false")
    if contract.get("connector_contract", {}).get("external_http_call") is not False:
        fail("connector_contract_http_call_not_false")
    if contract.get("connector_contract", {}).get("release_status_payload_from_client_trusted") is not False:
        fail("contract_client_release_status_boundary_missing")
    if contract.get("connector_contract", {}).get("connector_ref_shape") != "uppercase_opaque_ref_containing_REF":
        fail("contract_connector_ref_shape_missing")
    export_contract = contract.get("execution_envelope_export", {})
    if export_contract.get("tool") != "tools/xiaoj_lineworks_execution_envelope_export.py":
        fail("contract_export_tool_missing")
    for key in [
        "runtime_send_enabled",
        "external_api_call",
        "formal_lineworks_send",
        "credential_values_in_export",
        "raw_member_identity_in_export",
    ]:
        if export_contract.get(key) is not False:
            fail(f"contract_export_boundary_not_false:{key}")
    builder_contract = contract.get("release_refs_builder", {})
    if builder_contract.get("tool") != "tools/xiaoj_lineworks_release_refs_builder.py":
        fail("contract_builder_tool_missing")
    if builder_contract.get("api") != "/wuchang/xiaoj/api/lineworks-release-refs-draft":
        fail("contract_builder_api_missing")
    for key in ["accepts_secret_values", "accepts_member_plaintext", "external_api_call", "formal_lineworks_send", "db_write"]:
        if builder_contract.get(key) is not False:
            fail(f"contract_builder_boundary_not_false:{key}")
    runtime_contract = contract.get("p2_runtime_connector_contract", {})
    if runtime_contract.get("function") != "execute_lineworks_send_envelope":
        fail("contract_runtime_connector_function_missing")
    if runtime_contract.get("dry_run_api") != "/wuchang/xiaoj/api/lineworks-runtime-dry-run":
        fail("contract_runtime_dry_run_api_missing")
    if runtime_contract.get("dry_run_api_honors_client_enable_external_call") is not False:
        fail("contract_runtime_dry_run_client_enable_not_false")
    for key in [
        "default_external_api_call",
        "default_formal_lineworks_send",
    ]:
        if runtime_contract.get(key) is not False:
            fail(f"contract_runtime_default_not_false:{key}")
    for key in [
        "requires_enable_external_call_true",
        "requires_human_activation",
        "requires_activation_packet_hash",
        "requires_runtime_resolver",
    ]:
        if runtime_contract.get(key) is not True:
            fail(f"contract_runtime_requirement_missing:{key}")
    resolver_contract = contract.get("runtime_resolver_contract", {})
    if resolver_contract.get("tool") != "tools/xiaoj_lineworks_runtime_resolver_contract_builder.py":
        fail("contract_runtime_resolver_tool_missing")
    if resolver_contract.get("service") != "wuchang_cafe_ai_gateway.services.lineworks_runtime_resolver.build_lineworks_runtime_resolver_contract":
        fail("contract_runtime_resolver_service_missing")
    if resolver_contract.get("api") != "/wuchang/xiaoj/api/lineworks-runtime-resolver-contract":
        fail("contract_runtime_resolver_api_missing")
    for key in ["requires_runtime_binding_refs", "requires_value_hashes"]:
        if resolver_contract.get(key) is not True:
            fail(f"contract_runtime_resolver_requirement_missing:{key}")
    for key in ["raw_runtime_values_in_contract", "secret_read", "external_api_call", "formal_lineworks_send", "db_write"]:
        if resolver_contract.get(key) is not False:
            fail(f"contract_runtime_resolver_boundary_not_false:{key}")
    activation_contract = contract.get("runtime_activation_builder", {})
    if activation_contract.get("tool") != "tools/xiaoj_lineworks_runtime_activation_builder.py":
        fail("contract_activation_tool_missing")
    if activation_contract.get("api") != "/wuchang/xiaoj/api/lineworks-runtime-activation-draft":
        fail("contract_activation_api_missing")
    for key in ["requires_safe_operator_ref", "requires_execution_envelope_hash"]:
        if activation_contract.get(key) is not True:
            fail(f"contract_activation_requirement_missing:{key}")
    for key in ["accepts_secret_values", "accepts_member_plaintext", "external_api_call", "formal_lineworks_send", "db_write"]:
        if activation_contract.get(key) is not False:
            fail(f"contract_activation_boundary_not_false:{key}")
    handoff_contract = contract.get("operator_handoff_pack", {})
    if handoff_contract.get("tool") != "tools/xiaoj_lineworks_operator_handoff_pack.py":
        fail("contract_handoff_tool_missing")
    if handoff_contract.get("service") != "wuchang_cafe_ai_gateway.services.lineworks_handoff.build_lineworks_operator_handoff_pack":
        fail("contract_handoff_service_missing")
    if handoff_contract.get("api") != "/wuchang/xiaoj/api/lineworks-operator-handoff":
        fail("contract_handoff_api_missing")
    for required in [
        "release_refs_draft",
        "readiness",
        "execution_envelope",
        "runtime_activation",
        "runtime_dry_run",
        "operator_next_actions",
    ]:
        if required not in handoff_contract.get("aggregates", []):
            fail(f"contract_handoff_aggregate_missing:{required}")
    for key in ["external_api_call", "formal_lineworks_send", "secret_read", "member_plaintext_read", "db_write"]:
        if handoff_contract.get(key) is not False:
            fail(f"contract_handoff_boundary_not_false:{key}")
    odoo_actions = contract.get("odoo_operator_actions", {})
    for action in [
        "action_build_candidate",
        "action_build_release_refs_draft",
        "action_run_preflight",
        "action_build_execution_envelope",
        "action_build_runtime_activation_packet",
        "action_build_runtime_resolver_contract",
        "action_run_runtime_dry_run",
        "action_build_operator_handoff_pack",
        "action_dead_letter",
    ]:
        if action not in odoo_actions.get("safe_actions", []):
            fail(f"contract_odoo_safe_action_missing:{action}")
    if odoo_actions.get("formal_send_button_present") is not False:
        fail("contract_odoo_formal_send_button_not_false")
    red_team_controls = contract.get("red_team_controls", {})
    for control in [
        "reject_client_supplied_release_status_payload",
        "reject_jwt_shaped_connector_ref",
        "reject_long_bare_token_connector_ref",
        "reject_lowercase_or_raw_connector_ref",
        "odoo_model_constrains_secret_and_ref_shape",
    ]:
        if red_team_controls.get(control) is not True:
            fail(f"contract_red_team_control_missing:{control}")
    if release_template.get("state") != "TEMPLATE_REQUIRES_HUMAN_FILLED_VERIFIED_REFS":
        fail("release_template_state_wrong")
    if release_template.get("p1_side_effects", {}).get("formal_lineworks_send") is not False:
        fail("release_template_formal_send_not_false")
    template_gate = release_template.get("lineworks_send", {})
    for required_ref in contract.get("required_verified_release_refs", []):
        ref_obj = template_gate.get(required_ref)
        if not isinstance(ref_obj, dict):
            fail(f"release_template_missing_ref:{required_ref}")
        if ref_obj.get("verified") is not False:
            fail(f"release_template_must_not_be_preverified:{required_ref}")
    for key, value in release_template.get("connector_refs", {}).items():
        if not isinstance(value, str) or not value:
            fail(f"release_template_connector_ref_missing:{key}")
        if "TOKEN_REF_TEST" in value and value != "LINEWORKS_ACCESS_TOKEN_RUNTIME_REF":
            fail(f"release_template_connector_ref_unsafe:{key}")

    api_ctrl = read(API_CTRL)
    for needle in [
        '"/wuchang/xiaoj/api/lineworks-notify", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-send-preflight", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-release-refs-draft", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-execution-envelope", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-runtime-activation-draft", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-runtime-dry-run", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-operator-handoff", type="json", auth="user"',
        '"/wuchang/xiaoj/api/lineworks-runtime-resolver-contract", type="json", auth="user"',
        "build_lineworks_send_preflight",
        "build_lineworks_release_refs_draft",
        "build_lineworks_runtime_activation_packet",
        "build_lineworks_operator_handoff_pack",
        "build_lineworks_runtime_resolver_contract",
        "build_lineworks_execution_envelope_export",
        "execute_lineworks_send_envelope",
        "never trust a caller-supplied release_status_payload",
        "formal_release_status_payload(params.get(\"release_refs\")",
        "never honors client enable_external_call",
        "enable_external_call=False",
        "_lineworks_refs_from_params",
        "lineworks_send = {key: value for key, value in refs.items() if key != \"connector_refs\"}",
    ]:
        if needle not in api_ctrl:
            fail(f"api_controller_missing:{needle}")
    if "params.get(\"release_status_payload\")" in api_ctrl:
        fail("api_controller_trusts_client_release_status_payload")
    if "params.get(\"enable_external_call\")" in api_ctrl:
        fail("api_controller_honors_client_enable_external_call")

    model = read(MODEL)
    for needle in [
        '_name = "wuchang.lineworks.notification.candidate"',
        "action_build_candidate",
        "action_build_release_refs_draft",
        "action_run_preflight",
        "action_build_execution_envelope",
        "action_build_runtime_activation_packet",
        "action_build_runtime_resolver_contract",
        "action_run_runtime_dry_run",
        "action_build_operator_handoff_pack",
        "build_lineworks_send_preflight",
        "build_lineworks_execution_envelope_export",
        "build_lineworks_operator_handoff_pack",
        "build_lineworks_release_refs_draft",
        "build_lineworks_runtime_resolver_contract",
        "execute_lineworks_send_envelope",
        "formal_lineworks_send",
        "external_api_call",
        "execution_envelope_json",
        "runtime_dry_run_json",
        "runtime_activation_packet_json",
        "operator_handoff_pack_json",
        "operator_handoff_pack_hash",
        "release_refs_draft_hash",
        "release_refs_draft_warnings",
        "runtime_resolver_bindings_json",
        "runtime_resolver_contract_json",
        "runtime_resolver_contract_hash",
        "runtime_resolver_warnings",
        "connector_refs = dict(raw_refs.get(\"connector_refs\")",
        "if value:",
        "runtime_activation_packet_hash",
        "runtime_operator_ref",
        "_assert_no_secret_material",
        "@api.constrains",
        "is_safe_connector_ref",
    ]:
        if needle not in model:
            fail(f"model_missing:{needle}")
    for forbidden in ["requests.post", "urlopen", "http.client", "formal_lineworks_send = True", "external_api_call = True"]:
        if forbidden in model:
            fail(f"model_forbidden:{forbidden}")

    if "lineworks_notification" not in read(MODEL_INIT):
        fail("model_init_missing_lineworks_notification")
    if "views/lineworks_notification_views.xml" not in read(MANIFEST):
        fail("manifest_missing_lineworks_view")
    readiness_tool = read(READINESS_TOOL)
    for needle in [
        "HOLD_LINEWORKS_RELEASE_READINESS",
        "PASS_LINEWORKS_RELEASE_READINESS",
        "external_api_call",
        "formal_lineworks_send",
        "unsafe_connector_ref_keys",
        "unsafe_connector_ref_shape_keys",
    ]:
        if needle not in readiness_tool:
            fail(f"readiness_tool_missing:{needle}")
    export_tool = read(EXPORT_TOOL)
    for needle in [
        "build_export_report",
        "build_lineworks_execution_envelope_export",
        "runtime/product_av_ordering_ai/lineworks",
    ]:
        if needle not in export_tool:
            fail(f"export_tool_missing:{needle}")
    builder_tool = read(BUILDER_TOOL)
    for needle in [
        "LINEWORKS_RELEASE_REFS_DRAFT",
        "build_lineworks_release_refs_draft",
        "allow_verified",
    ]:
        if needle not in builder_tool:
            fail(f"builder_tool_missing:{needle}")
    release_refs_service = read(RELEASE_REFS_SERVICE)
    for needle in [
        "DRAFT_REQUIRES_HUMAN_VERIFICATION",
        "RELEASE_REFS_DRAFT_READY_FOR_READINESS_CHECK",
        "has_secret_or_plaintext_shape",
        "is_safe_release_ref",
        "is_safe_connector_ref",
    ]:
        if needle not in release_refs_service:
            fail(f"release_refs_service_missing:{needle}")
    activation_tool = read(ACTIVATION_TOOL)
    for needle in [
        "LINEWORKS_RUNTIME_ACTIVATION_PACKET",
        "confirm_human_activation",
        "activation_packet_hash",
    ]:
        if needle not in activation_tool:
            fail(f"activation_tool_missing:{needle}")
    activation_service = read(ACTIVATION_SERVICE)
    for needle in [
        "RUNTIME_ACTIVATION_PACKET_READY_FOR_DRY_RUN",
        "HOLD_RUNTIME_ACTIVATION_PACKET",
        "build_lineworks_runtime_activation_packet",
        "has_secret_or_plaintext_shape",
    ]:
        if needle not in activation_service:
            fail(f"activation_service_missing:{needle}")
    handoff_service = read(HANDOFF_SERVICE)
    for needle in [
        "build_lineworks_operator_handoff_pack",
        "W7TP_XIAOJ_LINEWORKS_OPERATOR_HANDOFF_PACK_V1",
        "HOLD_LINEWORKS_OPERATOR_HANDOFF_NEEDS_HUMAN_REFS",
        "PASS_LINEWORKS_OPERATOR_HANDOFF_READY_FOR_HUMAN_REVIEW",
        "execute_lineworks_send_envelope",
        "enable_external_call=False",
        "operator_next_actions",
    ]:
        if needle not in handoff_service:
            fail(f"handoff_service_missing:{needle}")
    handoff_tool = read(HANDOFF_TOOL)
    for needle in [
        "load_handoff_service",
        "build_lineworks_operator_handoff_pack",
        "operator_next_actions",
        "W7TP_XIAOJ_LINEWORKS_OPERATOR_HANDOFF_REPORT_V1",
    ]:
        if needle not in handoff_tool:
            fail(f"handoff_tool_missing:{needle}")
    runtime_resolver_service = read(RUNTIME_RESOLVER_SERVICE)
    for needle in [
        "build_lineworks_runtime_resolver_contract",
        "W7TP_XIAOJ_LINEWORKS_RUNTIME_RESOLVER_CONTRACT_V1",
        "PASS_LINEWORKS_RUNTIME_RESOLVER_CONTRACT_READY",
        "HOLD_LINEWORKS_RUNTIME_RESOLVER_CONTRACT",
        "raw_runtime_values",
        "secret_read",
        "is_safe_connector_ref",
    ]:
        if needle not in runtime_resolver_service:
            fail(f"runtime_resolver_service_missing:{needle}")
    runtime_resolver_tool = read(RUNTIME_RESOLVER_TOOL)
    for needle in [
        "LINEWORKS_RUNTIME_RESOLVER_CONTRACT",
        "build_lineworks_runtime_resolver_contract",
        "W7TP_XIAOJ_LINEWORKS_RUNTIME_RESOLVER_CONTRACT_REPORT_V1",
        "allow-verified",
    ]:
        if needle not in runtime_resolver_tool:
            fail(f"runtime_resolver_tool_missing:{needle}")
    connector_text = read(CONNECTOR)
    for needle in [
        "execute_lineworks_send_envelope",
        "enable_external_call",
        "human_activation_required",
        "activation_packet_hash_64hex_required",
        "runtime_resolver_required",
        "LINEWORKS_RUNTIME_DRY_RUN_READY",
    ]:
        if needle not in connector_text:
            fail(f"runtime_connector_missing:{needle}")
    access = read(ACCESS)
    for needle in [
        "model_wuchang_lineworks_notification_candidate",
        "base.group_user,1,1,1,0",
        "base.group_system,1,1,1,1",
    ]:
        if needle not in access:
            fail(f"access_missing:{needle}")
    view = read(VIEW)
    for needle in [
        "LINE WORKS Notification Candidate",
        "action_build_candidate",
        "action_build_release_refs_draft",
        "action_run_preflight",
        "action_build_execution_envelope",
        "action_build_runtime_activation_packet",
        "action_build_runtime_resolver_contract",
        "action_run_runtime_dry_run",
        "action_build_operator_handoff_pack",
        "Execution Envelope",
        "Runtime Activation",
        "Runtime Resolver",
        "Runtime Dry-Run",
        "Operator Handoff",
        "Build Handoff Pack",
        "Build Resolver Contract",
        "Build Release Refs Draft",
        "runtime_resolver_contract_hash",
        "release_refs_draft_hash",
        "action_dead_letter",
        "menu_wuchang_lineworks_notification_candidate",
    ]:
        if needle not in view:
            fail(f"view_missing:{needle}")
    if "正式送出" in view or "Send Now" in view:
        fail("view_has_formal_send_button")

    for path, needles in {
        DOC: [
            "STATE=LINE_WORKS_PRODUCTIZATION_P1_CANDIDATE_GATE_READY",
            "lineworks_send",
            "bot.message",
            "/wuchang/xiaoj/api/lineworks-execution-envelope",
            "/wuchang/xiaoj/api/lineworks-runtime-dry-run",
            "/wuchang/xiaoj/api/lineworks-runtime-activation-draft",
            "/wuchang/xiaoj/api/lineworks-operator-handoff",
            "/wuchang/xiaoj/api/lineworks-runtime-resolver-contract",
            "xiaoj_lineworks_release_refs_builder.py",
            "xiaoj_lineworks_runtime_activation_builder.py",
            "xiaoj_lineworks_runtime_resolver_contract_builder.py",
            "xiaoj_lineworks_operator_handoff_pack.py",
            "lineworks_release_refs_template.json",
            "Red-Team Controls",
            "forged `release_status_payload`",
            "action_build_execution_envelope",
            "action_run_runtime_dry_run",
            "action_build_operator_handoff_pack",
            "action_build_release_refs_draft",
            "action_build_runtime_resolver_contract",
        ],
        GUIDE: [
            "Simple Browser: Show",
            "Verified Release Refs",
            "不要把 LINE WORKS access token",
            "lineworks_release_refs_template.json",
            "lineworks-release-refs-draft",
            "xiaoj_lineworks_operator_handoff_pack.py",
            "lineworks-runtime-activation-draft",
            "lineworks-operator-handoff",
            "lineworks-runtime-resolver-contract",
            "Runtime Dry-Run",
            "Build Handoff Pack",
            "Build Release Refs Draft",
            "Build Resolver Contract",
        ],
    }.items():
        text = read(path)
        for needle in needles:
            if needle not in text:
                fail(f"doc_missing:{path.relative_to(ROOT)}:{needle}")

    candidate = engine.lineworks_notify_payload(
        "ACCESS_TOKEN_REF_TEST 提醒志工明天 10:00 到聊國咖啡館集合",
        "lineworks_user_ref_demo",
        "member_service",
        "staff_ref_demo",
    )
    serialized_candidate = json.dumps(candidate, ensure_ascii=False)
    if "SHOULD_NOT_SURVIVE" in serialized_candidate or "lineworks_user_ref_demo" in serialized_candidate:
        fail("candidate_leaks_secret_or_raw_target")
    if candidate.get("formal_lineworks_send") is not False or candidate.get("external_api_call") is not False:
        fail("candidate_has_side_effect")
    if candidate.get("local_verifier", {}).get("decision") != "HOLD":
        fail("candidate_not_hold")
    if "lineworks_send_release_required" not in candidate.get("local_verifier", {}).get("failure_reasons", []):
        fail("candidate_missing_lineworks_release_reason")

    fake_refs = {
        "lineworks_send": {ref: f"FAKE_{ref}" for ref in engine.FORMAL_RELEASE_GATES["lineworks_send"]["required_refs"]}
    }
    fake_release = engine.formal_release_status_payload(fake_refs)
    fake_gate = fake_release["formal_release_gates"]["lineworks_send"]
    if fake_gate.get("decision") != "HOLD_RELEASE_REFS_UNVERIFIED":
        fail(f"fake_release_not_blocked:{fake_gate.get('decision')}")

    release_refs = {
        "lineworks_send": {
            ref: verified_ref("lineworks_send", ref)
            for ref in engine.FORMAL_RELEASE_GATES["lineworks_send"]["required_refs"]
        }
    }
    ready_release = engine.formal_release_status_payload(release_refs)
    ready_gate = ready_release["formal_release_gates"]["lineworks_send"]
    if ready_gate.get("decision") != "RELEASE_READY_FOR_HUMAN_ACTIVATION":
        fail(f"verified_release_not_ready:{ready_gate.get('decision')}")

    missing_preflight = connector.build_lineworks_send_preflight(candidate, ready_release, {})
    if missing_preflight.get("send_allowed") is not False:
        fail("missing_preflight_allowed")
    if "connector_refs_missing" not in missing_preflight.get("failure_reasons", []):
        fail("missing_preflight_reason_absent")

    unsafe_preflight = connector.build_lineworks_send_preflight(
        candidate,
        ready_release,
        {
            "lineworks_bot_ref": "BOT_REF_ONLY",
            "lineworks_target_user_ref": "TARGET_REF_ONLY",
            "lineworks_access_token_runtime_ref": "ACCESS_TOKEN_REF_TEST",
        },
    )
    if unsafe_preflight.get("send_allowed") is not False:
        fail("unsafe_preflight_allowed")
    if "connector_refs_must_not_contain_secret_material" not in unsafe_preflight.get("failure_reasons", []):
        fail("unsafe_preflight_reason_absent")

    jwt_preflight = connector.build_lineworks_send_preflight(
        candidate,
        ready_release,
        {
            "lineworks_bot_ref": "BOT_REF_ONLY",
            "lineworks_target_user_ref": "TARGET_REF_ONLY",
            "lineworks_access_token_runtime_ref": ".".join(
                [
                    "TOKEN_REF_TEST_HEADER",
                    "TOKEN_REF_TEST_PAYLOAD",
                    "TOKEN_REF_TEST_SIGNATURE",
                ]
            ),
        },
    )
    if jwt_preflight.get("send_allowed") is not False:
        fail("jwt_preflight_allowed")
    if "connector_refs_must_not_contain_secret_material" not in jwt_preflight.get("failure_reasons", []):
        fail("jwt_preflight_secret_reason_absent")

    lowercase_ref_preflight = connector.build_lineworks_send_preflight(
        candidate,
        ready_release,
        {
            "lineworks_bot_ref": "bot_ref_lowercase_raw",
            "lineworks_target_user_ref": "TARGET_REF_ONLY",
            "lineworks_access_token_runtime_ref": "RUNTIME_TOKEN_PROVIDER_REF_ONLY",
        },
    )
    if lowercase_ref_preflight.get("send_allowed") is not False:
        fail("lowercase_ref_preflight_allowed")
    if "connector_refs_must_be_opaque_uppercase_refs" not in lowercase_ref_preflight.get("failure_reasons", []):
        fail("lowercase_ref_preflight_shape_reason_absent")

    ready_preflight = connector.build_lineworks_send_preflight(
        candidate,
        ready_release,
        {
            "lineworks_bot_ref": "BOT_REF_CAFE_XIAOJ_PILOT",
            "lineworks_target_user_ref": "TARGET_REF_HASHED_PILOT",
            "lineworks_access_token_runtime_ref": "RUNTIME_TOKEN_PROVIDER_REF_ONLY",
        },
    )
    if ready_preflight.get("send_allowed") is not True:
        fail(f"ready_preflight_not_allowed:{ready_preflight.get('failure_reasons')}")
    if ready_preflight.get("external_api_call") is not False or ready_preflight.get("formal_lineworks_send") is not False:
        fail("ready_preflight_has_side_effect")
    if ready_preflight.get("headers", {}).get("Authorization") != "BEARER_REF_TEST":
        fail("authorization_header_not_redacted")
    serialized_preflight = json.dumps(ready_preflight, ensure_ascii=False)
    for forbidden in ["BOT_REF_CAFE_XIAOJ_PILOT", "TARGET_REF_HASHED_PILOT", "RUNTIME_TOKEN_PROVIDER_REF_ONLY"]:
        if forbidden in serialized_preflight:
            fail(f"preflight_ref_value_echoed:{forbidden}")

    template_check = subprocess.run(
        [sys.executable, str(READINESS_TOOL), "--refs", str(RELEASE_TEMPLATE)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if template_check.returncode != 2:
        fail(f"readiness_template_should_hold:{template_check.returncode}:{template_check.stdout}:{template_check.stderr}")
    template_report = json.loads(template_check.stdout)
    if template_report.get("state") != "HOLD_LINEWORKS_RELEASE_READINESS":
        fail("readiness_template_state_not_hold")

    with tempfile.TemporaryDirectory() as tmp:
        handoff_hold_path = Path(tmp) / "handoff_hold.json"
        handoff_hold = subprocess.run(
            [
                sys.executable,
                str(HANDOFF_TOOL),
                "--refs",
                str(RELEASE_TEMPLATE),
                "--out",
                str(handoff_hold_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if handoff_hold.returncode != 2:
            fail(f"handoff_template_should_hold:{handoff_hold.returncode}:{handoff_hold.stdout}:{handoff_hold.stderr}")
        handoff_hold_report = json.loads(handoff_hold.stdout)
        if handoff_hold_report.get("state") != "HOLD_LINEWORKS_OPERATOR_HANDOFF_NEEDS_HUMAN_REFS":
            fail("handoff_template_state_not_hold")
        if not handoff_hold_path.exists():
            fail("handoff_hold_file_missing")

    with tempfile.TemporaryDirectory() as tmp:
        builder_hold_path = Path(tmp) / "builder_hold_refs.json"
        builder_hold = subprocess.run(
            [
                sys.executable,
                str(BUILDER_TOOL),
                "--input",
                str(RELEASE_TEMPLATE),
                "--out",
                str(builder_hold_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if builder_hold.returncode != 2:
            fail(f"builder_template_should_hold:{builder_hold.returncode}:{builder_hold.stdout}:{builder_hold.stderr}")
        builder_hold_report = json.loads(builder_hold.stdout)
        if builder_hold_report.get("state") != "DRAFT_REQUIRES_HUMAN_VERIFICATION":
            fail("builder_template_state_not_hold")
        if not builder_hold_path.exists():
            fail("builder_hold_file_missing")

    with tempfile.TemporaryDirectory() as tmp:
        resolver_hold_path = Path(tmp) / "runtime_resolver_hold.json"
        resolver_hold = subprocess.run(
            [
                sys.executable,
                str(RUNTIME_RESOLVER_TOOL),
                "--refs",
                str(RELEASE_TEMPLATE),
                "--out",
                str(resolver_hold_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if resolver_hold.returncode != 2:
            fail(f"runtime_resolver_template_should_hold:{resolver_hold.returncode}:{resolver_hold.stdout}:{resolver_hold.stderr}")
        resolver_hold_report = json.loads(resolver_hold.stdout)
        if resolver_hold_report.get("state") != "HOLD_LINEWORKS_RUNTIME_RESOLVER_CONTRACT":
            fail("runtime_resolver_template_state_not_hold")
        if not resolver_hold_path.exists():
            fail("runtime_resolver_hold_file_missing")

    with tempfile.TemporaryDirectory() as tmp:
        unsafe_input_path = Path(tmp) / "unsafe_refs.json"
        unsafe_output_path = Path(tmp) / "unsafe_refs_out.json"
        unsafe_input = {
            "lineworks_send": {
                ref: {
                    "ref": "ACCESS_TOKEN_REF_TEST",
                    "packet_hash": "e" * 64,
                    "verifier": "total_field_release_registry",
                    "verified": True,
                }
                for ref in engine.FORMAL_RELEASE_GATES["lineworks_send"]["required_refs"]
            },
            "connector_refs": {
                "lineworks_bot_ref": "BOT_REF_SAFE",
                "lineworks_target_user_ref": "TARGET_REF_SAFE",
                "lineworks_access_token_runtime_ref": "RUNTIME_TOKEN_PROVIDER_REF_SAFE",
            },
        }
        unsafe_input_path.write_text(json.dumps(unsafe_input, ensure_ascii=False), encoding="utf-8")
        unsafe_build = subprocess.run(
            [
                sys.executable,
                str(BUILDER_TOOL),
                "--input",
                str(unsafe_input_path),
                "--out",
                str(unsafe_output_path),
                "--allow-verified",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if unsafe_build.returncode != 2:
            fail(f"builder_unsafe_should_hold:{unsafe_build.returncode}:{unsafe_build.stdout}:{unsafe_build.stderr}")
        unsafe_draft = json.loads(unsafe_output_path.read_text(encoding="utf-8"))
        if any(row.get("verified") is True for row in unsafe_draft.get("lineworks_send", {}).values()):
            fail("builder_unsafe_preserved_verified")
        if not unsafe_draft.get("draft_warnings"):
            fail("builder_unsafe_warning_missing")

    with tempfile.TemporaryDirectory() as tmp:
        hold_export_path = Path(tmp) / "hold_lineworks_envelope.json"
        hold_export = subprocess.run(
            [
                sys.executable,
                str(EXPORT_TOOL),
                "--refs",
                str(RELEASE_TEMPLATE),
                "--target-ref",
                "TARGET_REF_EXPORT_HOLD",
                "--out",
                str(hold_export_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if hold_export.returncode != 2:
            fail(f"export_template_should_hold:{hold_export.returncode}:{hold_export.stdout}:{hold_export.stderr}")
        hold_report = json.loads(hold_export.stdout)
        if hold_report.get("state") != "HOLD_LINEWORKS_EXECUTION_ENVELOPE":
            fail("export_template_state_not_hold")
        if not hold_export_path.exists():
            fail("export_template_file_missing")

    with tempfile.TemporaryDirectory() as tmp:
        ready_refs_path = Path(tmp) / "ready_lineworks_refs.json"
        ready_builder_input_path = Path(tmp) / "ready_builder_input.json"
        ready_builder_output_path = Path(tmp) / "ready_builder_output.json"
        ready_export_path = Path(tmp) / "ready_lineworks_envelope.json"
        ready_refs = {
            "schema": "W7TP_XIAOJ_LINE_WORKS_RELEASE_REFS_TEMPLATE_V1",
            "state": "TEST_VERIFIED_REFS",
            "lineworks_send": release_refs["lineworks_send"],
            "connector_refs": {
                "lineworks_bot_ref": "BOT_REF_VERIFIED_PILOT",
                "lineworks_target_user_ref": "TARGET_REF_VERIFIED_PILOT",
                "lineworks_access_token_runtime_ref": "RUNTIME_TOKEN_PROVIDER_REF_VERIFIED_PILOT",
            },
            "p1_side_effects": {
                "external_api_call": False,
                "formal_lineworks_send": False,
                "secret_read": False,
                "member_plaintext_read": False,
                "deploy": False,
                "service_restart": False,
                "db_write": False,
            },
        }
        ready_builder_input_path.write_text(json.dumps(ready_refs, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        ready_build = subprocess.run(
            [
                sys.executable,
                str(BUILDER_TOOL),
                "--input",
                str(ready_builder_input_path),
                "--out",
                str(ready_builder_output_path),
                "--allow-verified",
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if ready_build.returncode != 0:
            fail(f"builder_ready_should_pass:{ready_build.returncode}:{ready_build.stdout}:{ready_build.stderr}")
        ready_builder_report = json.loads(ready_build.stdout)
        if ready_builder_report.get("state") != "RELEASE_REFS_DRAFT_READY_FOR_READINESS_CHECK":
            fail("builder_ready_state_not_pass")
        ready_refs_path.write_text(ready_builder_output_path.read_text(encoding="utf-8"), encoding="utf-8")
        ready_check = subprocess.run(
            [sys.executable, str(READINESS_TOOL), "--refs", str(ready_refs_path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if ready_check.returncode != 0:
            fail(f"readiness_ready_should_pass:{ready_check.returncode}:{ready_check.stdout}:{ready_check.stderr}")
        ready_report = json.loads(ready_check.stdout)
        if ready_report.get("state") != "PASS_LINEWORKS_RELEASE_READINESS":
            fail("readiness_ready_state_not_pass")

        ready_resolver_bindings_path = Path(tmp) / "ready_runtime_resolver_bindings.json"
        ready_resolver_contract_path = Path(tmp) / "ready_runtime_resolver_contract.json"
        ready_resolver_bindings = {
            "runtime_resolver_bindings": {
                "lineworks_bot_ref": {
                    "connector_ref": "BOT_REF_VERIFIED_PILOT",
                    "binding_ref": "VAULT_BINDING_REF_LINEWORKS_BOT_ID",
                    "value_class": "lineworks_bot_id",
                    "value_hash": "c" * 64,
                    "verifier": "lineworks_secret_vault_binding",
                    "verified": True,
                },
                "lineworks_target_user_ref": {
                    "connector_ref": "TARGET_REF_VERIFIED_PILOT",
                    "binding_ref": "VAULT_BINDING_REF_LINEWORKS_TARGET_USER_ID",
                    "value_class": "lineworks_target_user_id",
                    "value_hash": "d" * 64,
                    "verifier": "lineworks_secret_vault_binding",
                    "verified": True,
                },
                "lineworks_access_token_runtime_ref": {
                    "connector_ref": "RUNTIME_TOKEN_PROVIDER_REF_VERIFIED_PILOT",
                    "binding_ref": "VAULT_BINDING_REF_LINEWORKS_ACCESS_TOKEN",
                    "value_class": "lineworks_access_token",
                    "value_hash": "e" * 64,
                    "verifier": "lineworks_secret_vault_binding",
                    "verified": True,
                },
            }
        }
        ready_resolver_bindings_path.write_text(
            json.dumps(ready_resolver_bindings, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        ready_resolver = subprocess.run(
            [
                sys.executable,
                str(RUNTIME_RESOLVER_TOOL),
                "--refs",
                str(ready_refs_path),
                "--bindings",
                str(ready_resolver_bindings_path),
                "--allow-verified",
                "--out",
                str(ready_resolver_contract_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if ready_resolver.returncode != 0:
            fail(f"runtime_resolver_ready_should_pass:{ready_resolver.returncode}:{ready_resolver.stdout}:{ready_resolver.stderr}")
        ready_resolver_report = json.loads(ready_resolver.stdout)
        if ready_resolver_report.get("state") != "PASS_LINEWORKS_RUNTIME_RESOLVER_CONTRACT_READY":
            fail("runtime_resolver_ready_state_not_pass")
        ready_resolver_contract = json.loads(ready_resolver_contract_path.read_text(encoding="utf-8"))
        if ready_resolver_contract.get("redaction", {}).get("raw_runtime_values_in_contract") is not False:
            fail("runtime_resolver_raw_values_not_false")
        serialized_resolver_contract = json.dumps(ready_resolver_contract, ensure_ascii=False)
        runtime_token_ref = "LINEWORKS_ACCESS_TOKEN_RUNTIME_REF"
        for forbidden in ["2000001", runtime_token_ref, "Bearer "]:
            if forbidden in serialized_resolver_contract:
                fail(f"runtime_resolver_contract_echoed_raw_value:{forbidden}")

        ready_handoff_path = Path(tmp) / "ready_handoff.json"
        ready_handoff = subprocess.run(
            [
                sys.executable,
                str(HANDOFF_TOOL),
                "--refs",
                str(ready_refs_path),
                "--operator-ref",
                "OPERATOR_REF_VERIFIED_PILOT",
                "--confirm-human-activation",
                "--out",
                str(ready_handoff_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if ready_handoff.returncode != 0:
            fail(f"handoff_ready_should_pass:{ready_handoff.returncode}:{ready_handoff.stdout}:{ready_handoff.stderr}")
        ready_handoff_report = json.loads(ready_handoff.stdout)
        if ready_handoff_report.get("state") != "PASS_LINEWORKS_OPERATOR_HANDOFF_READY_FOR_HUMAN_REVIEW":
            fail("handoff_ready_state_not_pass")
        ready_handoff_pack = json.loads(ready_handoff_path.read_text(encoding="utf-8"))
        if ready_handoff_pack.get("runtime_dry_run", {}).get("external_api_call") is not False:
            fail("handoff_ready_external_api_call_not_false")
        if ready_handoff_pack.get("runtime_dry_run", {}).get("formal_lineworks_send") is not False:
            fail("handoff_ready_formal_send_not_false")

        ready_export = subprocess.run(
            [
                sys.executable,
                str(EXPORT_TOOL),
                "--refs",
                str(ready_refs_path),
                "--target-ref",
                "TARGET_REF_VERIFIED_PILOT",
                "--message",
                "LINE WORKS verified envelope export check",
                "--out",
                str(ready_export_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if ready_export.returncode != 0:
            fail(f"export_ready_should_pass:{ready_export.returncode}:{ready_export.stdout}:{ready_export.stderr}")
        ready_export_report = json.loads(ready_export.stdout)
        if ready_export_report.get("state") != "PASS_LINEWORKS_EXECUTION_ENVELOPE_READY":
            fail("export_ready_state_not_pass")
        if ready_export_report.get("runtime_send_enabled") is not False:
            fail("export_runtime_send_enabled")
        if not ready_export_path.exists():
            fail("export_ready_file_missing")
        serialized_export = ready_export_path.read_text(encoding="utf-8")
        for forbidden in [
            "BOT_REF_VERIFIED_PILOT",
            "TARGET_REF_VERIFIED_PILOT",
            "RUNTIME_TOKEN_PROVIDER_REF_VERIFIED_PILOT",
        ]:
            if forbidden in serialized_export:
                fail(f"export_ref_value_echoed:{forbidden}")

        unsafe_activation_path = Path(tmp) / "unsafe_activation.json"
        unsafe_activation = subprocess.run(
            [
                sys.executable,
                str(ACTIVATION_TOOL),
                "--operator-ref",
                "ACCESS_TOKEN_REF_TEST",
                "--execution-envelope-hash",
                ready_export_report.get("preflight_envelope_hash", ""),
                "--confirm-human-activation",
                "--out",
                str(unsafe_activation_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if unsafe_activation.returncode != 2:
            fail(f"activation_unsafe_should_hold:{unsafe_activation.returncode}:{unsafe_activation.stdout}:{unsafe_activation.stderr}")

        activation_path = Path(tmp) / "runtime_activation.json"
        activation_build = subprocess.run(
            [
                sys.executable,
                str(ACTIVATION_TOOL),
                "--operator-ref",
                "OPERATOR_REF_VERIFIED_PILOT",
                "--execution-envelope-hash",
                ready_export_report.get("preflight_envelope_hash", ""),
                "--candidate-packet-hash",
                ready_export_report.get("candidate_packet_hash", ""),
                "--release-packet-hash",
                ready_export_report.get("preflight_envelope_hash", ""),
                "--confirm-human-activation",
                "--out",
                str(activation_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if activation_build.returncode != 0:
            fail(f"activation_ready_should_pass:{activation_build.returncode}:{activation_build.stdout}:{activation_build.stderr}")
        activation_packet = json.loads(activation_path.read_text(encoding="utf-8"))
        if activation_packet.get("state") != "RUNTIME_ACTIVATION_PACKET_READY_FOR_DRY_RUN":
            fail("activation_ready_state_not_pass")
        activation = activation_packet.get("runtime_activation", {})
        if activation.get("human_activation") is not True:
            fail("activation_human_activation_not_true")

        dry_run_result = connector.execute_lineworks_send_envelope(
            ready_export_report,
            runtime_activation=activation,
            enable_external_call=False,
        )
        if dry_run_result.get("state") != "LINEWORKS_RUNTIME_DRY_RUN_READY":
            fail(f"runtime_dry_run_not_ready:{dry_run_result}")
        if dry_run_result.get("external_api_call") is not False or dry_run_result.get("formal_lineworks_send") is not False:
            fail("runtime_dry_run_has_side_effect")

        def resolver(key):
            return {
                "lineworks_bot_ref": "2000001",
                "lineworks_target_user_ref": "userf7da-f82c-4284-13e7-030f3b4c756x",
                "lineworks_access_token_runtime_ref": runtime_token_ref,
            }.get(key)

        def mock_post(url, headers, body, timeout):
            if "2000001" not in url or "userf7da" not in url:
                fail("runtime_mock_url_missing_resolved_ids")
            if headers.get("Authorization") != "Bearer " + runtime_token_ref:
                fail("runtime_mock_authorization_header_wrong")
            if body.get("content", {}).get("type") != "text":
                fail("runtime_mock_body_wrong")
            return {"status_code": 201, "response_body_hash": "d" * 64}

        runtime_result = connector.execute_lineworks_send_envelope(
            ready_export_report,
            runtime_activation=activation,
            runtime_resolver=resolver,
            http_post=mock_post,
            enable_external_call=True,
        )
        if runtime_result.get("state") != "PASS_LINEWORKS_RUNTIME_SEND_ACCEPTED":
            fail(f"runtime_mock_send_not_accepted:{runtime_result}")
        serialized_runtime = json.dumps(runtime_result, ensure_ascii=False)
        for forbidden in [
            "2000001",
            "userf7da-f82c-4284-13e7-030f3b4c756x",
            runtime_token_ref,
        ]:
            if forbidden in serialized_runtime:
                fail(f"runtime_result_echoed_secret_or_raw_id:{forbidden}")

    print("STATE=PASS_XIAOJ_LINEWORKS_PRODUCTIZATION")
    print("CANDIDATE_API=/wuchang/xiaoj/api/lineworks-notify")
    print("PREFLIGHT_API=/wuchang/xiaoj/api/lineworks-send-preflight")
    print("FORMAL_LINEWORKS_SEND=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("READY_PREFLIGHT=TRUE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
