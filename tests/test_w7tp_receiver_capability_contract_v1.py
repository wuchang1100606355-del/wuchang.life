from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from products.eight_dimensional_generative_memory import (
    w7tp_receiver_capability_contract_v1 as contract_mod,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "tests/fixtures/w7tp_receiver_capability/"
    "us_20261003_receiver_evidence_minimal.json"
)
RECEIPT = (
    ROOT
    / "tests/fixtures/w7tp_receiver_capability/"
    "us_20261003_remote_receipt_minimal.json"
)
PACKET = (
    ROOT
    / "tests/fixtures/w7tp_receiver_capability/"
    "us_20261003_minimum_packet_binding_minimal.json"
)


class ReceiverCapabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        cls.packet = json.loads(PACKET.read_text(encoding="utf-8"))
        cls.contract = contract_mod.build_contract_from_cross_node_evidence(
            cls.evidence
        )

    def test_contract_preserves_candidate_authority_boundary(self) -> None:
        authority = self.contract["authority"]
        self.assertFalse(authority["canonical"])
        self.assertFalse(authority["formal_authority"])
        self.assertFalse(authority["global_canonical_promotion"])

    def test_current_taiji01_receiver_matches_historical_success_contract(self) -> None:
        observed = contract_mod.observe_local_receiver(
            node_ref="node:taiji01"
        )
        result = contract_mod.match_receiver_capability(
            self.contract,
            observed,
        )
        self.assertEqual(
            result["state"],
            "PASS_RECEIVER_CAPABILITY_MATCH",
        )
        self.assertEqual(result["equivalence_level"], "BYTE_EXACT")

    def test_historical_failed_runtime_is_rejected_before_materialization(self) -> None:
        observed = contract_mod.observe_local_receiver(
            node_ref="node:historical-us-runtime"
        )
        observed["runtime"]["python_version"] = "3.11.2"
        observed["runtime"]["sqlite_version"] = "3.40.1"
        with self.assertRaisesRegex(
            contract_mod.ReceiverCapabilityHold,
            "HOLD_RECEIVER_PYTHON_VERSION_MISMATCH",
        ):
            contract_mod.match_receiver_capability(
                self.contract,
                observed,
            )

    def test_sqlite_mismatch_fails_closed(self) -> None:
        observed = contract_mod.observe_local_receiver(
            node_ref="node:test"
        )
        observed["runtime"]["sqlite_version"] = "3.40.1"
        with self.assertRaisesRegex(
            contract_mod.ReceiverCapabilityHold,
            "HOLD_RECEIVER_SQLITE_VERSION_MISMATCH",
        ):
            contract_mod.match_receiver_capability(
                self.contract,
                observed,
            )

    def test_primitive_hash_mismatch_fails_closed(self) -> None:
        observed = contract_mod.observe_local_receiver(
            node_ref="node:test"
        )
        observed["primitive_binding"]["implementation_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            contract_mod.ReceiverCapabilityHold,
            "HOLD_RECEIVER_PRIMITIVE_HASH_MISMATCH",
        ):
            contract_mod.match_receiver_capability(
                self.contract,
                observed,
            )

    def test_success_receipt_satisfies_materialization_contract(self) -> None:
        result = contract_mod.verify_materialization_receipt(
            self.contract,
            self.receipt,
        )
        self.assertEqual(
            result["state"],
            "PASS_MATERIALIZATION_CONTRACT_VERIFIED",
        )

    def test_manifest_mismatch_is_not_effect_verified(self) -> None:
        receipt = copy.deepcopy(self.receipt)
        receipt["target_manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            contract_mod.ReceiverCapabilityHold,
            "HOLD_MATERIALIZATION_MANIFEST_MISMATCH",
        ):
            contract_mod.verify_materialization_receipt(
                self.contract,
                receipt,
            )

    def test_evidence_records_logical_equality_did_not_imply_byte_equality(self) -> None:
        counterexample = self.contract["historical_counterexample"]
        self.assertTrue(counterexample["logical_rows_equal"])
        self.assertEqual(
            counterexample["observed_state"],
            "HOLD_FINAL_MANIFEST_MISMATCH",
        )

    def test_receiver_bound_envelope_binds_packet_and_contract(self) -> None:
        envelope = contract_mod.build_receiver_bound_envelope(
            self.packet,
            self.contract,
        )
        self.assertEqual(
            envelope["packet_sha256"],
            self.packet["packet_sha256"],
        )
        self.assertEqual(
            envelope["receiver_contract_sha256"],
            self.contract["contract_sha256"],
        )
        self.assertEqual(envelope["equivalence_level"], "BYTE_EXACT")
        self.assertFalse(envelope["authority"]["canonical"])
        self.assertFalse(envelope["authority"]["execution_authorized"])

    def test_receiver_bound_envelope_rejects_wrong_rule(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["rule_binding"]["rule_ref"] = "local-rule:wrong"
        with self.assertRaisesRegex(
            contract_mod.ReceiverCapabilityHold,
            "HOLD_RECEIVER_BOUND_RULE_REF_MISMATCH",
        ):
            contract_mod.build_receiver_bound_envelope(
                packet,
                self.contract,
            )


if __name__ == "__main__":
    unittest.main()
