from __future__ import annotations

import copy
import unittest

from tools.total_field.w7tp_operation_capability_cell_candidate import (
    OperationCapabilityHold,
    load_packet,
    reconstruct_composite_capability,
    validate_operation_packet,
)


class OperationCapabilityCellCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = load_packet()

    def test_current_nvr_router_packet_validates(self) -> None:
        result = validate_operation_packet(self.packet)
        self.assertEqual(result["state"], "PASS_OPERATION_CAPABILITY_CELL_PACKET_VALIDATED")
        self.assertEqual(result["cell_count"], 2)

    def test_reconstructs_composite_without_executing_effect(self) -> None:
        result = reconstruct_composite_capability(self.packet)["composite"]
        self.assertEqual(result["state"], "PASS_COMPOSITE_OPERATION_CAPABILITY_RECONSTRUCTED_CANDIDATE")
        self.assertEqual(set(result["capability_ids"]), {"NVR_CONFIG_READ", "ROUTER_NAT_OBSERVE"})
        self.assertEqual(result["effect_mode"], "READ_ONLY")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["effect_authorized"])
        self.assertTrue(result["total_field_verify_required"])
        self.assertEqual(len(result["composite_sha256"]), 64)

    def test_write_escalation_fails_closed(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["cell_model"]["cells"][0]["effect_mode"] = "WRITE"
        with self.assertRaisesRegex(OperationCapabilityHold, "HOLD_OPERATION_CELL_EFFECT_OR_EVIDENCE_INVALID"):
            validate_operation_packet(packet)

    def test_d8_escalation_fails_closed(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["d8"]["authority"] = "PROVIDER"
        with self.assertRaisesRegex(OperationCapabilityHold, "HOLD_OPERATION_PACKET_D8_AUTHORITY_WALL_INVALID"):
            validate_operation_packet(packet)

    def test_unbound_relation_fails_closed(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["cell_model"]["relations"][0]["to"] = "cell:UNKNOWN"
        with self.assertRaisesRegex(OperationCapabilityHold, "HOLD_OPERATION_CELL_RELATION_INVALID"):
            validate_operation_packet(packet)


if __name__ == "__main__":
    unittest.main()
