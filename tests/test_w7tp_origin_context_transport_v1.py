from __future__ import annotations

import copy
import unittest
from pathlib import Path

from products.eight_dimensional_generative_memory import (
    w7tp_endpoint_rule_handshake_v1 as handshake,
)
from tools import w7tp_origin_context_transport_v1 as transport


ROOT = Path(__file__).resolve().parents[1]


def receiver_handshake():
    return handshake.observe_endpoint_rule_capability(
        root=ROOT,
        node_ref="MSI",
        state_root=None,
    )


class OriginContextTransportTests(unittest.TestCase):
    def test_large_repetitive_context_uses_shared_rule_and_reconstructs(self) -> None:
        payload = {
            "state": "PASS_TOTAL_FIELD_DYNAMIC_CONTEXT",
            "context_ref": "context:test:large",
            "state_projection": {"body": "A" * 200000},
            "evidence_refs": ["evidence:test"],
        }
        delivery = transport.build_transport(
            payload,
            receiver_handshake(),
            root=ROOT,
            source_state_root=ROOT,
        )
        self.assertEqual(delivery["mode"], "SHARED_RULE_ORIGIN_CELL")
        self.assertFalse(delivery["authority"]["canonical"])
        self.assertFalse(delivery["authority"]["execution_authorized"])
        rebuilt = transport.reconstruct_transport(delivery, root=ROOT)
        self.assertEqual(rebuilt, payload)

    def test_small_context_can_choose_full_transfer_and_reconstructs(self) -> None:
        payload = {
            "state": "PASS_TOTAL_FIELD_DYNAMIC_CONTEXT",
            "context_ref": "context:test:small",
            "state_projection": {"value": 1},
            "evidence_refs": ["evidence:test"],
        }
        delivery = transport.build_transport(
            payload,
            receiver_handshake(),
            root=ROOT,
            source_state_root=ROOT,
        )
        self.assertEqual(delivery["mode"], "FULL_TRANSFER")
        rebuilt = transport.reconstruct_transport(delivery, root=ROOT)
        self.assertEqual(rebuilt, payload)

    def test_receiver_handshake_drift_fails_closed(self) -> None:
        payload = {
            "state": "PASS_TOTAL_FIELD_DYNAMIC_CONTEXT",
            "context_ref": "context:test:drift",
            "state_projection": {"body": "B" * 200000},
            "evidence_refs": ["evidence:test"],
        }
        delivery = transport.build_transport(
            payload,
            receiver_handshake(),
            root=ROOT,
            source_state_root=ROOT,
        )
        self.assertEqual(delivery["mode"], "SHARED_RULE_ORIGIN_CELL")
        tampered = copy.deepcopy(delivery)
        tampered["receiver_handshake_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            transport.ContextTransportHold,
            "HOLD_CONTEXT_RECEIVER_HANDSHAKE_DRIFT",
        ):
            transport.reconstruct_transport(tampered, root=ROOT)

    def test_packet_tamper_fails_before_model_visible_context(self) -> None:
        payload = {
            "state": "PASS_TOTAL_FIELD_DYNAMIC_CONTEXT",
            "context_ref": "context:test:tamper",
            "state_projection": {"body": "C" * 200000},
            "evidence_refs": ["evidence:test"],
        }
        delivery = transport.build_transport(
            payload,
            receiver_handshake(),
            root=ROOT,
            source_state_root=ROOT,
        )
        self.assertEqual(delivery["mode"], "SHARED_RULE_ORIGIN_CELL")
        tampered = copy.deepcopy(delivery)
        tampered["packet"]["packet_sha256"] = "0" * 64
        with self.assertRaises(transport.ContextTransportHold):
            transport.reconstruct_transport(tampered, root=ROOT)


if __name__ == "__main__":
    unittest.main()
