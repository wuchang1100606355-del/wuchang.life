"""Shared verifier helpers for XiaoJ productization console P1/P2 drafts."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/productization_console.py"
CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
CONTRACT = ROOT / "packets/product_av_ordering_ai/xiaoj_productization_console_contract.json"
GUIDE = ROOT / "docs/product/XIAOJ_PRODUCTIZATION_CONSOLE_GUIDE.md"

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{12,}",
    r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+",
    r"(?i)api[_ -]?key\s*[:=]\s*\S+",
    r"(?i)(channel|client|router|odoo|lineworks|line)[_-]?secret\s*[:=]\s*\S+",
    r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}",
    r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
    r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
    r"09\d{2}[- ]?\d{3}[- ]?\d{3}",
    r"\b[A-Z][12]\d{8}\b",
]


def fail(message: str, state: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print(f"STATE={state}")
    raise SystemExit(1)


def read(path: Path, hold_state: str) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}", hold_state)
    return path.read_text(encoding="utf-8")


def require(path: Path, needles: list[str], hold_state: str) -> str:
    text = read(path, hold_state)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}", hold_state)
    return text


def assert_no_secret_shape(text: str, label: str, hold_state: str) -> None:
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            fail(f"secret_shape_detected:{label}:{pattern}", hold_state)


def assert_false_map(values: dict, label: str, hold_state: str) -> None:
    if not isinstance(values, dict):
        fail(f"missing_false_map:{label}", hold_state)
    for key, value in values.items():
        if value is not False:
            fail(f"expected_false:{label}:{key}", hold_state)


def ensure_package_stub(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    elif not hasattr(module, "__path__"):
        module.__path__ = [str(path)]  # type: ignore[attr-defined]


def load_service(hold_state: str):
    ensure_package_stub("Taiji_Odoo", ROOT / "Taiji_Odoo")
    ensure_package_stub("Taiji_Odoo.addons", ROOT / "Taiji_Odoo/addons")
    ensure_package_stub("Taiji_Odoo.addons.wuchang_cafe_ai_gateway", ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway")
    ensure_package_stub(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services",
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services",
    )
    spec = importlib.util.spec_from_file_location(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services.productization_console",
        SERVICE,
    )
    if spec is None or spec.loader is None:
        fail("service_import_spec_missing", hold_state)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_common_artifacts(function_name: str, route: str, schema: str, hold_state: str) -> tuple[Any, dict]:
    service_text = require(
        SERVICE,
        [
            function_name,
            schema,
            "side_effects_false",
            "reject_secret_or_plaintext",
            "\"external_api_call\": False",
            "\"formal_db_write\": False",
            "\"raw_api_key_read\": False",
            "\"member_plaintext_read\": False",
            "\"resident_plaintext_read\": False",
        ],
        hold_state,
    )
    controller_text = require(
        CONTROLLER,
        [
            function_name,
            f"@http.route(\"{route}\", type=\"json\", auth=\"user\", csrf=False)",
        ],
        hold_state,
    )
    contract_text = require(
        CONTRACT,
        [
            "W7TP_XIAOJ_PRODUCTIZATION_CONSOLE_CONTRACT_V1",
            route,
            "gpt-5.4-mini",
            "gemini-2.5-flash-lite",
            "cloud_model_candidate_only",
            "plaintext_email_in_public_contract",
            "raw API key",
            "member plaintext",
            "resident plaintext",
        ],
        hold_state,
    )
    guide_text = require(
        GUIDE,
        [
            "STATE=P1_TOTAL_PRODUCT_CONSOLE_DRAFT_READY_P2_GATES_HOLD",
            route,
            "candidate / dry-run / preflight",
            "owner_admin_ref",
            "gpt-5.4-mini",
            "gemini-2.5-flash-lite",
            "external_api_call=false",
            "payment_capture=false",
        ],
        hold_state,
    )
    for label, text in [
        ("service", service_text),
        ("controller", controller_text),
        ("contract", contract_text),
        ("guide", guide_text),
    ]:
        assert_no_secret_shape(text, label, hold_state)
    contract = json.loads(contract_text)
    assert_false_map(contract.get("p1_side_effects", {}), "contract_side_effects", hold_state)
    if contract.get("api_auth") != "user":
        fail("contract_api_auth_wrong", hold_state)
    if contract.get("model_governance", {}).get("cloud_model_candidate_only") is not True:
        fail("contract_cloud_candidate_only_missing", hold_state)
    if contract.get("model_governance", {}).get("nano_architecture_decision_allowed") is not False:
        fail("contract_nano_boundary_missing", hold_state)
    return load_service(hold_state), contract


def assert_packet_common(packet: dict, schema: str, hold_state: str) -> None:
    if packet.get("schema") != schema:
        fail(f"packet_schema_wrong:{packet.get('schema')}", hold_state)
    assert_false_map(packet.get("side_effects", {}), "packet_side_effects", hold_state)
    assert_no_secret_shape(json.dumps(packet, ensure_ascii=False, sort_keys=True), "packet", hold_state)


def assert_rejects_plaintext(func, hold_state: str) -> None:
    try:
        func(refs={"owner_admin_ref": "owner@example.com"})
    except ValueError:
        return
    fail("plaintext_email_not_rejected", hold_state)


def member_llm_ready_refs() -> dict:
    return {
        "member_ref": "MEMBER_READY_REF",
        "model_ref": "MODEL_READY_REF",
        "quota_ref": "QUOTA_READY_REF",
        "consent_ref": "CONSENT_READY_REF",
        "truth_boundary_ref": "TRUTH_BOUNDARY_READY_REF",
        "gemini_key_ref": "GEMINI_KEY_READY_REF",
        "release_packet_hash": "a" * 64,
    }


def local_pii_ready_refs() -> dict:
    return {
        "member_ref": "MEMBER_READY_REF",
        "consent_ref": "CONSENT_READY_REF",
        "local_vault_ref": "LOCAL_VAULT_READY_REF",
        "encrypted_payload_hash": "b" * 64,
    }


def delegate_ready_refs() -> dict:
    return {
        "old_packet_ref": "OLD_PACKET_READY_REF",
        "new_packet_ref": "NEW_PACKET_READY_REF",
        "revocation_ref": "REVOCATION_READY_REF",
        "owner_admin_or_quorum_ref": "OWNER_ADMIN_QUORUM_READY_REF",
        "evidence_chain_hash": "c" * 64,
    }


def sovereign_xiaoj_ready_refs() -> dict:
    return {
        "member_ref": "MEMBER_READY_REF",
        "xiaoj_instance_ref": "XIAOJ_INSTANCE_READY_REF",
        "device_ref": "DEVICE_READY_REF",
        "claim_packet_hash": "d" * 64,
        "revocation_ref": "REVOCATION_READY_REF",
        "transfer_policy_ref": "TRANSFER_POLICY_READY_REF",
    }
