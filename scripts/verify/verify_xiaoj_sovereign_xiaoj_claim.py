#!/usr/bin/env python3
"""Verify XiaoJ sovereign XiaoJ claim draft."""

from __future__ import annotations

from xiaoj_productization_console_verify_lib import (
    assert_packet_common,
    assert_rejects_plaintext,
    fail,
    require_common_artifacts,
    sovereign_xiaoj_ready_refs,
)


HOLD_STATE = "HOLD_XIAOJ_SOVEREIGN_XIAOJ_CLAIM"


def main() -> int:
    service, contract = require_common_artifacts(
        "build_sovereign_xiaoj_claim_draft",
        "/wuchang/xiaoj/api/sovereign-xiaoj-claim-draft",
        "W7TP_SOVEREIGN_XIAOJ_CLAIM_DRAFT_V1",
        HOLD_STATE,
    )
    if "sovereign_xiaoj_claim_draft" not in contract.get("p2_gates", {}):
        fail("contract_sovereign_claim_gate_missing", HOLD_STATE)
    hold_packet = service.build_sovereign_xiaoj_claim_draft(refs={})
    assert_packet_common(hold_packet, "W7TP_SOVEREIGN_XIAOJ_CLAIM_DRAFT_V1", HOLD_STATE)
    if hold_packet.get("state") != "HOLD_SOVEREIGN_XIAOJ_CLAIM_REFS_REQUIRED":
        fail("hold_state_wrong", HOLD_STATE)
    ready_packet = service.build_sovereign_xiaoj_claim_draft(refs=sovereign_xiaoj_ready_refs())
    assert_packet_common(ready_packet, "W7TP_SOVEREIGN_XIAOJ_CLAIM_DRAFT_V1", HOLD_STATE)
    if ready_packet.get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("ready_state_wrong", HOLD_STATE)
    if ready_packet.get("claim_activated_by_default") is not False:
        fail("claim_activated_by_default_not_false", HOLD_STATE)
    if ready_packet.get("device_bound_by_default") is not False:
        fail("device_bound_by_default_not_false", HOLD_STATE)
    assert_rejects_plaintext(service.build_sovereign_xiaoj_claim_draft, HOLD_STATE)
    print("STATE=PASS_XIAOJ_SOVEREIGN_XIAOJ_CLAIM")
    print("CLAIM_ACTIVATED_BY_DEFAULT=FALSE")
    print("DEVICE_BOUND_BY_DEFAULT=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
