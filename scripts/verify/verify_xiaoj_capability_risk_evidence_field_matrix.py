#!/usr/bin/env python3
"""Verify XiaoJ capability risk evidence-field matrix and contract."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/capability_risk_evidence_field_contract.json"
DOC = ROOT / "docs/product/XIAOJ_CAPABILITY_RISK_EVIDENCE_FIELD_MATRIX.md"
EXPECTED_SCHEMA = "W7TP_CAPABILITY_RISK_EVIDENCE_FIELD_CONTRACT_V1"
EXPECTED_STATE = "P1_RISK_EVIDENCE_FIELD_MATRIX_READY_P2_RELEASE_HOLD"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print("STATE=HOLD_XIAOJ_CAPABILITY_RISK_EVIDENCE_FIELD_MATRIX")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_text(path: Path, needles: list[str]) -> str:
    text = read(path)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def require_false(mapping: dict, keys: list[str], scope: str) -> None:
    for key in keys:
        if mapping.get(key) is not False:
            fail(f"{scope}_not_false:{key}")


def main() -> int:
    contract = json.loads(read(CONTRACT))
    if contract.get("schema") != EXPECTED_SCHEMA:
        fail("contract_schema_wrong")
    if contract.get("state") != EXPECTED_STATE:
        fail("contract_state_wrong")

    boundary = contract.get("authority_boundary", {})
    required_true = [
        "capability_governance_core",
        "cloud_model_candidate_only",
        "local_discrete_verifier_is_authority",
        "owner_admin_approval_required_for_release",
        "real_claim_requires_evidence_ref",
        "execution_claim_requires_local_gate",
    ]
    for key in required_true:
        if boundary.get(key) is not True:
            fail(f"authority_boundary_not_true:{key}")
    required_false = [
        "output_governance_only",
        "external_candidate_execute_allowed",
        "cloud_can_mark_real_verified",
        "cloud_can_mark_executable_authorized",
    ]
    require_false(boundary, required_false, "authority_boundary")
    if boundary.get("execution_permission_model") != "EXECUTE_REQUEST_ONLY":
        fail("execution_permission_model_wrong")

    required_fields = set(contract.get("required_evidence_fields", []))
    for field in [
        "risk_code",
        "risk_level",
        "intent_field_hash",
        "packet_hash",
        "candidate_hash",
        "evidence_ref",
        "evidence_hash",
        "local_lookup_ref",
        "local_reconstruction_hash",
        "total_field_query_hash",
        "verifier_policy_ref",
        "verifier_state",
        "failure_reasons",
        "approval_ref",
        "release_condition_ref",
        "seal_hash",
        "ttl",
        "nonce",
        "route_key",
    ]:
        if field not in required_fields:
            fail(f"required_evidence_field_missing:{field}")

    hold_conditions = set(contract.get("global_hold_conditions", []))
    for condition in [
        "evidence_ref_missing",
        "evidence_hash_missing",
        "packet_hash_missing",
        "total_field_query_hash_missing",
        "local_reconstruction_hash_missing",
        "owner_approval_ref_missing_for_release",
        "ttl_or_nonce_missing",
        "danger_flags_present",
        "secret_material_detected",
        "member_or_resident_plaintext_detected",
        "cloud_candidate_attempted_execute",
    ]:
        if condition not in hold_conditions:
            fail(f"hold_condition_missing:{condition}")

    controls = contract.get("risk_controls", [])
    if not isinstance(controls, list) or len(controls) < 12:
        fail("risk_controls_count_too_low")
    control_by_id = {item.get("risk_id"): item for item in controls}
    expected_ids = {
        "cloud_candidate_overreach",
        "missing_evidence_anchor",
        "total_field_subfield_danger",
        "member_personal_data_local_return",
        "delegate_rotation_revocation",
        "sovereign_xiaoj_claim_activation",
        "formal_pos_order",
        "formal_payment",
        "lineworks_formal_send",
        "property_management_action",
        "llm_hallucination_boundary",
        "secret_material_exposure",
    }
    if set(control_by_id) != expected_ids:
        fail(f"risk_control_ids_wrong:{sorted(control_by_id)}")

    for risk_id, item in control_by_id.items():
        for key in [
            "surface",
            "risk_code",
            "required_evidence_fields",
            "missing_policy",
            "authorized_output",
            "forbidden_output",
            "local_verifier_failure_reasons",
        ]:
            if not item.get(key):
                fail(f"risk_control_missing:{risk_id}:{key}")
        if item.get("authorized_output") == "EXECUTE":
            fail(f"risk_control_authorizes_execute:{risk_id}")
        if not str(item.get("risk_code", "")).startswith("RISK_"):
            fail(f"risk_code_prefix_wrong:{risk_id}")
        if not str(item.get("missing_policy", "")).startswith("HOLD_"):
            fail(f"missing_policy_not_hold:{risk_id}")
        required_for_item = item.get("required_evidence_fields", [])
        if not isinstance(required_for_item, list) or len(required_for_item) < 5:
            fail(f"risk_control_required_fields_too_few:{risk_id}")
        if not any(field in required_for_item for field in ["evidence_hash", "evidence_ref", "evidence_chain_hash"]):
            fail(f"risk_control_no_evidence_anchor:{risk_id}")
        reasons = item.get("local_verifier_failure_reasons", [])
        if not isinstance(reasons, list) or not reasons:
            fail(f"risk_control_no_failure_reasons:{risk_id}")

    if control_by_id["cloud_candidate_overreach"].get("authorized_output") != "EXECUTE_REQUEST_ONLY":
        fail("cloud_candidate_output_not_execute_request_only")
    if control_by_id["missing_evidence_anchor"].get("authorized_output") != "HOLD":
        fail("missing_evidence_anchor_not_hold")
    if "total_field_subfield_danger_flags" not in control_by_id["total_field_subfield_danger"].get("local_verifier_failure_reasons", []):
        fail("total_field_danger_failure_reason_missing")
    if "member_plaintext_detected" not in control_by_id["member_personal_data_local_return"].get("local_verifier_failure_reasons", []):
        fail("member_pii_plaintext_guard_missing")
    if "resident_plaintext_detected" not in control_by_id["property_management_action"].get("local_verifier_failure_reasons", []):
        fail("resident_plaintext_guard_missing")
    if "lineworks_send_release_required" not in control_by_id["lineworks_formal_send"].get("local_verifier_failure_reasons", []):
        fail("lineworks_release_reason_missing")

    disclosure = contract.get("disclosure_boundary", {})
    for key in ["public_disclosure_allowed", "abstract_public_only", "trade_secret_only"]:
        if not isinstance(disclosure.get(key), list) or not disclosure.get(key):
            fail(f"disclosure_boundary_missing:{key}")
    for secret in [
        "WHY_IT_RUNS",
        "complete lookup table",
        "private weights",
        "complete routing table",
        "router password",
        "API key",
        "token",
        "member plaintext",
        "resident plaintext",
        "raw audio",
        "raw video",
    ]:
        if secret not in disclosure.get("trade_secret_only", []):
            fail(f"trade_secret_boundary_missing:{secret}")

    side_effects = contract.get("p1_side_effects", {})
    require_false(
        side_effects,
        [
            "external_api_call",
            "model_invocation",
            "formal_lineworks_send",
            "formal_line_message_send",
            "formal_member_registration",
            "formal_db_write",
            "db_write",
            "formal_pos_write",
            "payment_capture",
            "secret_read",
            "raw_api_key_read",
            "raw_api_key_saved",
            "member_plaintext_read",
            "resident_plaintext_read",
            "member_plaintext_to_prompt",
            "resident_plaintext_to_prompt",
            "raw_audio_saved",
            "raw_video_saved",
            "deploy",
            "service_restart",
        ],
        "p1_side_effect",
    )

    doc = require_text(
        DOC,
        [
            "STATE=P1_RISK_EVIDENCE_FIELD_MATRIX_READY_P2_RELEASE_HOLD",
            "本系統治理 capability（能力），不是只治理 output（輸出）。",
            "EXECUTE_REQUEST（執行請求）",
            "不得直接產生 EXECUTE（執行）",
            "local reconstruction（本地重構）",
            "local discrete verifier（本地離散驗證器）",
            "owner/admin approval ref（所有者 / 管理者核准引用）",
            "Member personal data return（會員個資回本機）",
            "Delegate rotation（代理身分輪替）",
            "Sovereign XiaoJ claim（主權小J領用）",
            "Formal POS order（正式 POS 下單）",
            "Formal payment（正式付款）",
            "LINE WORKS formal send（LINE WORKS 正式送出）",
            "Property management action（物業管理動作）",
            "LLM hallucination boundary（大型語言模型幻覺邊界）",
            "Secret material exposure（秘密材料外洩）",
            "WHY_IT_RUNS（核心運作機理）",
        ],
    )
    if re.search(r"sk-[A-Za-z0-9_-]{10,}", doc):
        fail("secret_shaped_openai_key_in_doc")
    if re.search(r"AIza[0-9A-Za-z_-]{20,}", doc):
        fail("secret_shaped_google_key_in_doc")

    print("STATE=PASS_XIAOJ_CAPABILITY_RISK_EVIDENCE_FIELD_MATRIX")
    print("CAPABILITY_GOVERNANCE_CORE=TRUE")
    print("EXECUTION_PERMISSION_MODEL=EXECUTE_REQUEST_ONLY")
    print("CLOUD_MODEL_CANDIDATE_ONLY=TRUE")
    print("LOCAL_VERIFIER_AUTHORITY=TRUE")
    print("P1_SIDE_EFFECTS=FALSE")
    print("P2_RELEASE_HOLD=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
