#!/usr/bin/env python3
"""Verify XiaoJ LLM cost-saving model router P1 artifacts.

This verifier proves the cost-saving router is a candidate-only planning layer.
It must not call models, read API keys, write Odoo settings, or claim production
activation.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/llm_cost_saving_model_router.py"
TOOL = ROOT / "tools/xiaoj_llm_cost_saving_model_router.py"
CONTRACT = ROOT / "packets/product_av_ordering_ai/llm_cost_saving_model_router_contract.json"
RELEASE_SEQUENCE_CONTRACT = ROOT / "packets/product_av_ordering_ai/xiaoj_low_cost_model_release_sequence_contract.json"
GUIDE = ROOT / "docs/product/XIAOJ_LLM_COST_SAVING_MODEL_ROUTER_GUIDE.md"
READINESS_DOC = ROOT / "docs/product/XIAOJ_SOVEREIGN_MEMBER_LLM_READINESS_MATRIX.md"
CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{12,}",
    r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+",
    r"(?i)api[_ -]?key\s*[:=]\s*\S+",
    r"(?i)client_secret\s*[:=]\s*\S+",
    r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}",
    r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
    r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
    r"09\d{2}[- ]?\d{3}[- ]?\d{3}",
    r"\b[A-Z][12]\d{8}\b",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print("STATE=HOLD_XIAOJ_LLM_COST_SAVING_MODEL_ROUTER")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(path: Path, needles: list[str]) -> str:
    text = read(path)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def assert_no_secret_shape(text: str, label: str) -> None:
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            fail(f"secret_shape_detected:{label}:{pattern}")


def assert_false_map(values: dict, label: str) -> None:
    if not isinstance(values, dict):
        fail(f"missing_false_map:{label}")
    for key, value in values.items():
        if value is not False:
            fail(f"expected_false:{label}:{key}")


def load_service():
    spec = importlib.util.spec_from_file_location("llm_cost_saving_model_router_verify", SERVICE)
    if spec is None or spec.loader is None:
        fail("service_import_spec_missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def ready_refs() -> dict:
    return {
        "local_model_ref": "LOCAL_MODEL_READY_REF",
        "external_candidate_model_ref": "GEMINI_2_5_FLASH_LITE_MODEL_READY_REF",
        "gemini_key_ref_vault_binding": "GEMINI_KEY_VAULT_BINDING_READY_REF",
        "member_llm_release_ref": "MEMBER_LLM_RELEASE_READY_REF",
        "quota_policy_ref": "QUOTA_POLICY_READY_REF",
        "consent_policy_ref": "CONSENT_POLICY_READY_REF",
    }


def verify_packet(packet: dict, expected_state: str, expected_lane: str) -> None:
    if packet.get("schema") != "W7TP_XIAOJ_LLM_COST_SAVING_MODEL_ROUTER_CANDIDATE_V1":
        fail("packet_schema_wrong")
    if packet.get("state") != expected_state:
        fail(f"packet_state_wrong:{packet.get('state')}")
    if packet.get("selected_lane") != expected_lane:
        fail(f"packet_lane_wrong:{packet.get('selected_lane')}")
    if packet.get("runtime_model_changed") is not False:
        fail("packet_runtime_model_changed_not_false")
    if packet.get("authority_boundary", {}).get("local_discrete_verifier_is_authority") is not True:
        fail("packet_local_authority_missing")
    if packet.get("authority_boundary", {}).get("raw_api_key_to_model_router") is not False:
        fail("packet_raw_key_boundary_wrong")
    if packet.get("authority_boundary", {}).get("payment_pos_member_property_execution_by_llm") is not False:
        fail("packet_execution_boundary_wrong")
    if packet.get("model_role_policy", {}).get("nano_utility_only", {}).get("architecture_decision_allowed") is not False:
        fail("packet_nano_architecture_boundary_missing")
    if packet.get("price_snapshot", {}).get("models", {}).get("gemini-2.5-flash-lite", {}).get("output_per_1m_usd") != 0.40:
        fail("packet_gemini_price_snapshot_missing")
    if "add_member_llm_release_gate" not in packet.get("release_sequence", []):
        fail("packet_release_sequence_missing")
    assert_false_map(packet.get("side_effects", {}), "packet_side_effects")
    assert_no_secret_shape(json.dumps(packet, ensure_ascii=False, sort_keys=True), "packet")


def main() -> int:
    service_text = require(
        SERVICE,
        [
            "MODEL_ROLE_POLICY",
            "PRICE_SNAPSHOT",
            "RELEASE_SEQUENCE",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gemini-2.5-flash-lite",
            "\"runtime_model_changed\": False",
            "\"model_invocation\": False",
            "\"raw_api_key_read\": False",
            "\"llm_execution_authority\": False",
        ],
    )
    tool_text = require(
        TOOL,
        [
            "build_llm_cost_saving_model_router_candidate",
            "--allow-external-candidate",
            "--refs",
        ],
    )
    controller_text = require(
        CONTROLLER,
        [
            "build_llm_cost_saving_model_router_candidate",
            "\"xiaoj_llm_cost_saving_model_router_api\": \"HOLD_MODEL_ROUTE_REFS_REQUIRED\"",
            "@http.route(\"/wuchang/xiaoj/api/llm-cost-saving-model-router\", type=\"json\", auth=\"user\", csrf=False)",
        ],
    )
    contract_text = require(
        CONTRACT,
        [
            "W7TP_XIAOJ_LLM_COST_SAVING_MODEL_ROUTER_CONTRACT_V1",
            "P1_LLM_COST_SAVING_MODEL_ROUTER_READY",
            "/wuchang/xiaoj/api/llm-cost-saving-model-router",
            "gpt-5.5",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gemini-2.5-flash-lite",
            "cloud_model_candidate_only",
            "nano_architecture_decision_allowed",
            "add_member_llm_release_gate",
        ],
    )
    release_sequence_text = require(
        RELEASE_SEQUENCE_CONTRACT,
        [
            "W7TP_XIAOJ_LOW_COST_MODEL_RELEASE_SEQUENCE_CONTRACT_V1",
            "P1_RELEASE_SEQUENCE_FIXED_P2_GATES_HOLD",
            "gemini_key_ref_vault_binding",
            "member_llm_release_gate",
            "local_personal_data_return_packet",
            "8d_delegate_rotation_and_revocation",
            "sovereign_xiaoj_claim_activation",
            "formal_pos_member_payment_release",
        ],
    )
    guide_text = require(
        GUIDE,
        [
            "STATE=P1_LLM_COST_SAVING_MODEL_ROUTER_READY",
            "gpt-5.5",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gemini-2.5-flash-lite",
            "POST /wuchang/xiaoj/api/llm-cost-saving-model-router",
            "tools/xiaoj_llm_cost_saving_model_router.py",
            "external_api_call=false",
            "runtime_model_changed=false",
        ],
    )
    readiness_text = require(
        READINESS_DOC,
        [
            "低成本模型路由與後續落地順序",
            "P1_LLM_COST_SAVING_MODEL_ROUTER_READY",
            "scripts/verify/verify_xiaoj_llm_cost_saving_model_router.py",
            "gpt-5.4-mini",
            "gemini-2.5-flash-lite",
            "cheap model output is always candidate-only",
            "nano is not allowed to make architecture decisions",
        ],
    )

    for label, text in [
        ("service", service_text),
        ("tool", tool_text),
        ("controller", controller_text),
        ("contract", contract_text),
        ("release_sequence_contract", release_sequence_text),
        ("guide", guide_text),
        ("readiness_doc", readiness_text),
    ]:
        assert_no_secret_shape(text, label)

    contract = json.loads(contract_text)
    if contract.get("runtime_model_changed") is not False:
        fail("contract_runtime_model_changed_not_false")
    if contract.get("raw_api_key_accepted") is not False:
        fail("contract_raw_key_accepted_not_false")
    if contract.get("raw_member_plaintext_accepted") is not False:
        fail("contract_member_plaintext_accepted_not_false")
    if contract.get("gemini_runtime_authority") is not False:
        fail("contract_gemini_authority_not_false")
    if contract.get("cloud_model_candidate_only") is not True:
        fail("contract_cloud_candidate_only_missing")
    if contract.get("nano_architecture_decision_allowed") is not False:
        fail("contract_nano_boundary_missing")
    assert_false_map(contract.get("p1_side_effects", {}), "contract_side_effects")

    release_contract = json.loads(release_sequence_text)
    if release_contract.get("state") != "P1_RELEASE_SEQUENCE_FIXED_P2_GATES_HOLD":
        fail("release_sequence_state_wrong")
    if release_contract.get("authority_boundary", {}).get("cloud_model_candidate_only") is not True:
        fail("release_sequence_cloud_candidate_boundary_missing")
    assert_false_map(release_contract.get("p1_side_effects", {}), "release_sequence_side_effects")

    service = load_service()
    hold_packet = service.build_llm_cost_saving_model_router_candidate(
        task_intent="影音人形服務生候選互動",
        task_surface="av_humanoid_service",
        refs={},
        allow_external_candidate=True,
    )
    verify_packet(hold_packet, "HOLD_MODEL_ROUTE_REFS_REQUIRED", "LOCAL_FALLBACK_HOLD_EXTERNAL_REFS")

    ready_packet = service.build_llm_cost_saving_model_router_candidate(
        task_intent="影音人形服務生候選互動",
        task_surface="av_humanoid_service",
        refs=ready_refs(),
        allow_external_candidate=True,
    )
    verify_packet(ready_packet, "READY_FOR_HUMAN_MODEL_ROUTE_REVIEW", "CLOUD_CANDIDATE_WITH_LOCAL_AUTHORITY")
    if ready_packet.get("selected_model_ref") != "GEMINI_2_5_FLASH_LITE_MODEL_READY_REF":
        fail("ready_packet_external_model_ref_wrong")

    authority_packet = service.build_llm_cost_saving_model_router_candidate(
        task_intent="正式付款",
        task_surface="payment_execution",
        refs=ready_refs(),
        allow_external_candidate=True,
    )
    verify_packet(authority_packet, "READY_FOR_HUMAN_MODEL_ROUTE_REVIEW", "LOCAL_AUTHORITY_ONLY")
    if authority_packet.get("selected_model_ref") != "LOCAL_DISCRETE_AUTHORITY_CORE_REF":
        fail("authority_packet_model_ref_wrong")

    with tempfile.TemporaryDirectory() as tmp_name:
        refs_path = Path(tmp_name) / "refs.json"
        refs_path.write_text(json.dumps(ready_refs(), ensure_ascii=False, indent=2), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--intent",
                "商家社群候選文案",
                "--surface",
                "merchant_social_management",
                "--refs",
                str(refs_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            fail(f"tool_returncode:{proc.returncode}:{proc.stdout}:{proc.stderr}")
        cli_packet = json.loads(proc.stdout)
        verify_packet(cli_packet, "READY_FOR_HUMAN_MODEL_ROUTE_REVIEW", "LOCAL_FIRST")

    print("STATE=PASS_XIAOJ_LLM_COST_SAVING_MODEL_ROUTER")
    print("MODEL_ROUTER_READY=TRUE")
    print("RECOMMENDED_CODE_MODEL=gpt-5.4-mini")
    print("RECOMMENDED_RUNTIME_CANDIDATE_MODEL=gemini-2.5-flash-lite")
    print("NANO_ARCHITECTURE_DECISION_ALLOWED=FALSE")
    print("RUNTIME_MODEL_CHANGED=FALSE")
    print("RAW_API_KEY_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
