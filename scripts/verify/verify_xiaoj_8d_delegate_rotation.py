#!/usr/bin/env python3
"""Verify XiaoJ 8D delegate rotation draft."""

from __future__ import annotations

from xiaoj_productization_console_verify_lib import (
    assert_packet_common,
    assert_rejects_plaintext,
    delegate_ready_refs,
    fail,
    require_common_artifacts,
)


HOLD_STATE = "HOLD_XIAOJ_8D_DELEGATE_ROTATION"


def main() -> int:
    service, contract = require_common_artifacts(
        "build_8d_delegate_rotation_draft",
        "/wuchang/xiaoj/api/8d-delegate-rotation-draft",
        "W7TP_8D_DELEGATE_ROTATION_DRAFT_V1",
        HOLD_STATE,
    )
    if "eightd_delegate_rotation_draft" not in contract.get("p2_gates", {}):
        fail("contract_delegate_rotation_gate_missing", HOLD_STATE)
    hold_packet = service.build_8d_delegate_rotation_draft(refs={})
    assert_packet_common(hold_packet, "W7TP_8D_DELEGATE_ROTATION_DRAFT_V1", HOLD_STATE)
    if hold_packet.get("state") != "HOLD_8D_DELEGATE_ROTATION_REFS_REQUIRED":
        fail("hold_state_wrong", HOLD_STATE)
    ready_packet = service.build_8d_delegate_rotation_draft(refs=delegate_ready_refs())
    assert_packet_common(ready_packet, "W7TP_8D_DELEGATE_ROTATION_DRAFT_V1", HOLD_STATE)
    if ready_packet.get("state") != "READY_FOR_HUMAN_REVIEW":
        fail("ready_state_wrong", HOLD_STATE)
    if ready_packet.get("old_delegate_revoked_by_default") is not False:
        fail("old_delegate_revoked_by_default_not_false", HOLD_STATE)
    if ready_packet.get("new_delegate_activated_by_default") is not False:
        fail("new_delegate_activated_by_default_not_false", HOLD_STATE)
    assert_rejects_plaintext(service.build_8d_delegate_rotation_draft, HOLD_STATE)
    print("STATE=PASS_XIAOJ_8D_DELEGATE_ROTATION")
    print("OLD_DELEGATE_REVOKED_BY_DEFAULT=FALSE")
    print("NEW_DELEGATE_ACTIVATED_BY_DEFAULT=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
