#!/usr/bin/env python3
"""Verify XiaoJ local personal data return packet draft."""

from __future__ import annotations

from xiaoj_productization_console_verify_lib import (
    assert_packet_common,
    assert_rejects_plaintext,
    fail,
    local_pii_ready_refs,
    require_common_artifacts,
)


HOLD_STATE = "HOLD_XIAOJ_LOCAL_PERSONAL_DATA_RETURN_PACKET"


def main() -> int:
    service, contract = require_common_artifacts(
        "build_local_personal_data_return_packet",
        "/wuchang/xiaoj/api/local-personal-data-return-packet",
        "W7TP_LOCAL_PERSONAL_DATA_RETURN_PACKET_V1",
        HOLD_STATE,
    )
    if "local_personal_data_return_packet" not in contract.get("p2_gates", {}):
        fail("contract_local_pii_gate_missing", HOLD_STATE)
    hold_packet = service.build_local_personal_data_return_packet(refs={})
    assert_packet_common(hold_packet, "W7TP_LOCAL_PERSONAL_DATA_RETURN_PACKET_V1", HOLD_STATE)
    if hold_packet.get("state") != "HOLD_ENCRYPTED_LOCAL_VAULT_REF_REQUIRED":
        fail("hold_state_wrong", HOLD_STATE)
    ready_packet = service.build_local_personal_data_return_packet(refs=local_pii_ready_refs())
    assert_packet_common(ready_packet, "W7TP_LOCAL_PERSONAL_DATA_RETURN_PACKET_V1", HOLD_STATE)
    if ready_packet.get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("ready_state_wrong", HOLD_STATE)
    if ready_packet.get("cloud_llm_receives_personal_data") is not False:
        fail("cloud_llm_receives_personal_data_not_false", HOLD_STATE)
    if ready_packet.get("prompt_contains_personal_data") is not False:
        fail("prompt_contains_personal_data_not_false", HOLD_STATE)
    assert_rejects_plaintext(service.build_local_personal_data_return_packet, HOLD_STATE)
    print("STATE=PASS_XIAOJ_LOCAL_PERSONAL_DATA_RETURN_PACKET")
    print("CLOUD_LLM_RECEIVES_PERSONAL_DATA=FALSE")
    print("PROMPT_CONTAINS_PERSONAL_DATA=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
