#!/usr/bin/env python3
"""Verify XiaoJ total productization console status draft."""

from __future__ import annotations

from xiaoj_productization_console_verify_lib import (
    assert_packet_common,
    assert_rejects_plaintext,
    delegate_ready_refs,
    fail,
    local_pii_ready_refs,
    member_llm_ready_refs,
    require_common_artifacts,
    sovereign_xiaoj_ready_refs,
)


HOLD_STATE = "HOLD_XIAOJ_TOTAL_PRODUCT_CONSOLE_STATUS"


def main() -> int:
    service, contract = require_common_artifacts(
        "build_xiaoj_total_product_console_status",
        "/wuchang/xiaoj/api/total-product-console-status",
        "W7TP_XIAOJ_TOTAL_PRODUCT_CONSOLE_STATUS_V1",
        HOLD_STATE,
    )
    if contract.get("state") != "P1_TOTAL_PRODUCT_CONSOLE_DRAFT_READY_P2_GATES_HOLD":
        fail("contract_state_wrong", HOLD_STATE)
    packet = service.build_xiaoj_total_product_console_status(refs={}, actor_ref="ACTOR_REF_VERIFY")
    assert_packet_common(packet, "W7TP_XIAOJ_TOTAL_PRODUCT_CONSOLE_STATUS_V1", HOLD_STATE)
    if packet.get("state") != "HOLD_P2_RELEASE_REFS_REQUIRED":
        fail("console_hold_state_wrong", HOLD_STATE)
    for product_line in [
        "merchant_branch_xiaoj",
        "association_total_field_member_service_xiaoj",
        "eightd_sovereign_member_system",
        "eightd_sovereign_resident_property_management",
    ]:
        if product_line not in packet.get("product_lines", []):
            fail(f"product_line_missing:{product_line}", HOLD_STATE)
    if packet.get("lineworks", {}).get("formal_send") is not False:
        fail("lineworks_formal_send_not_false", HOLD_STATE)
    if packet.get("low_cost_model_governance", {}).get("recommended_code_model") != "gpt-5.4-mini":
        fail("recommended_code_model_wrong", HOLD_STATE)
    if packet.get("low_cost_model_governance", {}).get("recommended_runtime_candidate_model") != "gemini-2.5-flash-lite":
        fail("recommended_runtime_model_wrong", HOLD_STATE)
    if packet.get("low_cost_model_governance", {}).get("nano_architecture_decision_allowed") is not False:
        fail("nano_architecture_boundary_missing", HOLD_STATE)
    if packet.get("production_activation_ready") is not False:
        fail("production_activation_ready_not_false", HOLD_STATE)
    refs_ready_for_p2_drafts = {
        "member_llm_refs": member_llm_ready_refs(),
        "local_personal_data_return_refs": local_pii_ready_refs(),
        "delegate_rotation_refs": delegate_ready_refs(),
        "sovereign_xiaoj_claim_refs": sovereign_xiaoj_ready_refs(),
    }
    p2_packet = service.build_xiaoj_total_product_console_status(
        refs=refs_ready_for_p2_drafts,
        actor_ref="ACTOR_REF_VERIFY",
    )
    assert_packet_common(p2_packet, "W7TP_XIAOJ_TOTAL_PRODUCT_CONSOLE_STATUS_V1", HOLD_STATE)
    if p2_packet.get("draft_packets", {}).get("member_llm_release_gate", {}).get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("member_llm_draft_not_ready", HOLD_STATE)
    if p2_packet.get("draft_packets", {}).get("local_personal_data_return_packet", {}).get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("local_pii_draft_not_ready", HOLD_STATE)
    if p2_packet.get("draft_packets", {}).get("delegate_rotation", {}).get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("delegate_rotation_draft_not_ready", HOLD_STATE)
    if p2_packet.get("draft_packets", {}).get("sovereign_xiaoj_claim", {}).get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("sovereign_claim_draft_not_ready", HOLD_STATE)
    assert_rejects_plaintext(service.build_xiaoj_total_product_console_status, HOLD_STATE)
    print("STATE=PASS_XIAOJ_TOTAL_PRODUCT_CONSOLE_STATUS")
    print("PRODUCTIZATION_CONSOLE_READY=TRUE")
    print("PRODUCTION_ACTIVATION_READY=FALSE")
    print("FORMAL_LINEWORKS_SEND=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
