#!/usr/bin/env python3
"""Verify XiaoJ sovereign member LLM release gate draft."""

from __future__ import annotations

from xiaoj_productization_console_verify_lib import (
    assert_packet_common,
    assert_rejects_plaintext,
    fail,
    member_llm_ready_refs,
    require_common_artifacts,
)


HOLD_STATE = "HOLD_XIAOJ_MEMBER_LLM_RELEASE_GATE"


def main() -> int:
    service, contract = require_common_artifacts(
        "build_sovereign_member_llm_release_gate",
        "/wuchang/xiaoj/api/member-llm-release-gate",
        "W7TP_MEMBER_LLM_RELEASE_GATE_V1",
        HOLD_STATE,
    )
    if "member_llm_release_gate" not in contract.get("p2_gates", {}):
        fail("contract_member_llm_gate_missing", HOLD_STATE)
    hold_packet = service.build_sovereign_member_llm_release_gate(refs={})
    assert_packet_common(hold_packet, "W7TP_MEMBER_LLM_RELEASE_GATE_V1", HOLD_STATE)
    if hold_packet.get("state") != "HOLD_MEMBER_LLM_RELEASE_REFS_REQUIRED":
        fail("hold_state_wrong", HOLD_STATE)
    ready_packet = service.build_sovereign_member_llm_release_gate(refs=member_llm_ready_refs())
    assert_packet_common(ready_packet, "W7TP_MEMBER_LLM_RELEASE_GATE_V1", HOLD_STATE)
    if ready_packet.get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("ready_state_wrong", HOLD_STATE)
    if ready_packet.get("cloud_model_authority") is not False:
        fail("cloud_authority_not_false", HOLD_STATE)
    if ready_packet.get("raw_api_key_allowed") is not False:
        fail("raw_api_key_allowed_not_false", HOLD_STATE)
    if ready_packet.get("candidate_only") is not True:
        fail("candidate_only_missing", HOLD_STATE)
    assert_rejects_plaintext(service.build_sovereign_member_llm_release_gate, HOLD_STATE)
    print("STATE=PASS_XIAOJ_MEMBER_LLM_RELEASE_GATE")
    print("RAW_API_KEY_ALLOWED=FALSE")
    print("CLOUD_MODEL_AUTHORITY=FALSE")
    print("CANDIDATE_ONLY=TRUE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
