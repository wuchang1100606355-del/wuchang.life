from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.w7tp_d6_generative_transmission_verifier_v2_3 import (
    verify_d6_generative_transmission,
)
from tools.w7tp_differential_transfer_verifier_v1 import (
    apply_object_diff,
    verify_differential_transfer,
)
from tools.w7tp_transfer_packet_compatibility_v2_3 import classify_transfer_packet
from tools.w7tp_transfer_rule_common import append_only_json, object_sha256


REPO_ROOT = Path(__file__).resolve().parents[1]
OBSERVED_AT = "2026-09-14T00:00:00Z"


def lookup_table() -> dict:
    return {
        "LOOKUP_TABLE_ID": "fixture:discrete-state-transition",
        "LOOKUP_TABLE_VERSION": "1",
        "ENTRIES": {"7:10": 13},
    }


def transition_rule() -> dict:
    return {
        "DISCRETE_TRANSITION_RULE_ID": "TARGET_BASE_PLUS_MINIMUM_REQUIRED_INDEX_DELTA_V1",
        "OPERATION": "TARGET_BASE_PLUS_MINIMUM_REQUIRED_INDEX_DELTA",
        "NUMERIC_DOMAIN": "INTEGER",
    }


def target_snapshot() -> dict:
    return {
        "TARGET_IDENTITY": "target-node",
        "SNAPSHOT_REFERENCE": "snapshot:target-node:fixture:1",
        "TARGET_BASE_INTEGER_INDEX": 10,
        "RECONSTRUCTION_COORDINATE": "adi:target-node:fixture:13",
        "TARGET_ONLY_STATE": {"must_remain": "unchanged"},
    }


def d6_packet(carrier: str = "REFERENCE_ONLY") -> dict:
    table = lookup_table()
    rule = transition_rule()
    return {
        "PACKET_TYPE": "D6_GENERATIVE_TRANSMISSION_PACKET",
        "CAPABILITY_ID": "D6_GENERATIVE_TRANSMISSION",
        "PRIMARY_OPERATION": "D6_GENERATIVE_TRANSMISSION",
        "CARRIER": carrier,
        "SOURCE_IDENTITY": "source-node",
        "TARGET_IDENTITY": "target-node",
        "CANONICAL_IDENTITY": "W7TP / 8D ADI V2.3",
        "TARGET_FIELD_SNAPSHOT_REFERENCE": "snapshot:target-node:fixture:1",
        "SOURCE_STATE_INTEGER_INDEX": 7,
        "TARGET_BASE_INTEGER_INDEX": 10,
        "EXPECTED_TARGET_STATE_INTEGER_INDEX": 13,
        "MINIMUM_REQUIRED_INDEX_DELTA": 3,
        "LOOKUP_TABLE_ID": table["LOOKUP_TABLE_ID"],
        "LOOKUP_TABLE_VERSION": table["LOOKUP_TABLE_VERSION"],
        "LOOKUP_TABLE_DIGEST": object_sha256(table),
        "DISCRETE_TRANSITION_RULE_ID": rule["DISCRETE_TRANSITION_RULE_ID"],
        "DISCRETE_TRANSITION_RULE_DIGEST": object_sha256(rule),
        "REFERENCES": ["fixture:source", "fixture:target"],
        "RECONSTRUCTION_COORDINATE": "adi:target-node:fixture:13",
        "RECONSTRUCTION_RULES": ["TARGET_NATIVE_INTEGER_LOOKUP"],
        "VERIFICATION_RULES": ["EXPECTED_TARGET_STATE_INTEGER_INDEX_MATCH"],
        "RECEIVER_IDENTITY": "target-node",
        "RUNTIME_BOUNDARY": "REPOSITORY_RULE_ONLY_NO_LIVE_EFFECT",
        "NONCE": "fixture-nonce-1",
        "LOGICAL_TIME": 100,
        "TTL": 10,
        "EVIDENCE_DESTINATION": "fixture:d4-evidence",
    }


def run_d6(packet: dict, **kwargs) -> dict:
    return verify_d6_generative_transmission(
        packet,
        target_field_snapshot=kwargs.pop("snapshot", target_snapshot()),
        lookup_table=kwargs.pop("table", lookup_table()),
        transition_rule=kwargs.pop("rule", transition_rule()),
        current_logical_time=kwargs.pop("current_logical_time", 105),
        observed_at=OBSERVED_AT,
        **kwargs,
    )


def differential_fixture() -> tuple[dict, dict, dict, dict]:
    base = {"shared": 1, "target_only": "preserve"}
    payload = {"set": {"shared": 2}, "delete": []}
    target = {"shared": 2, "target_only": "preserve"}
    packet = {
        "PACKET_TYPE": "DIFFERENTIAL_TRANSFER_PACKET",
        "CAPABILITY_ID": "DIFFERENTIAL_TRANSFER",
        "BASE_OBJECT_IDENTITY": "source-node",
        "BASE_OBJECT_DIGEST": object_sha256(base),
        "TARGET_OBJECT_IDENTITY": "target-node",
        "EXPECTED_TARGET_DIGEST": object_sha256(target),
        "DIFF_PAYLOAD_DIGEST": object_sha256(payload),
        "DIFF_ALGORITHM_ID": "JSON_TOP_LEVEL_SET_DELETE_V1",
        "APPLY_BOUNDARY": ["shared"],
        "VERIFICATION_RULE": "SHA256_TARGET_MATCH",
    }
    return packet, base, payload, target


class TransferRuleBindingTests(unittest.TestCase):
    def test_01_valid_integer_lookup_is_deterministic(self) -> None:
        result = run_d6(d6_packet())
        self.assertEqual(result["TARGET_STATE_INTEGER_INDEX"], 13)
        self.assertEqual(
            result["D6_INTEGER_RECONSTRUCTION_EVIDENCE"]["RESULT"],
            "CANDIDATE_RECONSTRUCTION_VERIFIED",
        )

    def test_02_same_input_has_same_integer_output(self) -> None:
        first = run_d6(d6_packet())
        second = run_d6(d6_packet())
        self.assertEqual(first["TARGET_STATE_INTEGER_INDEX"], second["TARGET_STATE_INTEGER_INDEX"])
        self.assertEqual(
            first["D6_INTEGER_RECONSTRUCTION_EVIDENCE"],
            second["D6_INTEGER_RECONSTRUCTION_EVIDENCE"],
        )

    def test_03_non_integer_index_is_rejected(self) -> None:
        packet = d6_packet()
        packet["SOURCE_STATE_INTEGER_INDEX"] = "7"
        self.assertEqual(run_d6(packet)["STATE"], "HOLD_INTEGER_INDEX_DOMAIN_INVALID")

    def test_04_lookup_table_digest_mismatch_holds(self) -> None:
        packet = d6_packet()
        packet["LOOKUP_TABLE_DIGEST"] = "0" * 64
        self.assertEqual(run_d6(packet)["STATE"], "HOLD_LOOKUP_TABLE_DIGEST_MISMATCH")

    def test_05_target_base_index_mismatch_holds(self) -> None:
        packet = d6_packet()
        packet["TARGET_BASE_INTEGER_INDEX"] = 9
        self.assertEqual(run_d6(packet)["STATE"], "HOLD_TARGET_BASE_INDEX_MISMATCH")

    def test_06_differential_success_emits_d4_only(self) -> None:
        packet, base, payload, _ = differential_fixture()
        result = verify_differential_transfer(
            packet,
            observed_base_identity="source-node",
            base_object=base,
            diff_payload=payload,
            observed_at=OBSERVED_AT,
        )
        self.assertEqual(
            set(result),
            {"RECONSTRUCTED_OBJECT_DIGEST", "DELTA_APPLY_RECEIPT", "CARRIER_RESULT"},
        )
        receipt = result["DELTA_APPLY_RECEIPT"]
        self.assertEqual(receipt["EVIDENCE_SCOPE"], "D4_EVIDENCE_ONLY")
        self.assertEqual(receipt["AUTHORITY_SCOPE"], "NONE")

    def test_07_differential_base_digest_mismatch_holds(self) -> None:
        packet, base, payload, _ = differential_fixture()
        packet["BASE_OBJECT_DIGEST"] = "0" * 64
        result = verify_differential_transfer(
            packet,
            observed_base_identity="source-node",
            base_object=base,
            diff_payload=payload,
            observed_at=OBSERVED_AT,
        )
        self.assertEqual(result["CARRIER_RESULT"], "HOLD")
        self.assertEqual(
            result["DELTA_APPLY_RECEIPT"]["OUTPUT_DIGESTS"]["HOLD_STATE"],
            "HOLD_DELTA_BASE_MISMATCH",
        )

    def test_08_d6_accepts_reference_only_carrier(self) -> None:
        result = run_d6(d6_packet("REFERENCE_ONLY"))
        self.assertEqual(result["TARGET_STATE_INTEGER_INDEX"], 13)
        self.assertFalse(result["D6_PASS"])

    def test_09_d6_accepts_verified_differential_carrier(self) -> None:
        diff_packet, base, payload, _ = differential_fixture()
        carrier_result = verify_differential_transfer(
            diff_packet,
            observed_base_identity="source-node",
            base_object=base,
            diff_payload=payload,
            observed_at=OBSERVED_AT,
        )
        result = run_d6(
            d6_packet("DIFFERENTIAL_TRANSFER"),
            carrier_result=carrier_result,
        )
        self.assertEqual(result["TARGET_STATE_INTEGER_INDEX"], 13)

    def test_10_carrier_success_never_creates_d6_pass(self) -> None:
        diff_packet, base, payload, _ = differential_fixture()
        carrier_result = verify_differential_transfer(
            diff_packet,
            observed_base_identity="source-node",
            base_object=base,
            diff_payload=payload,
            observed_at=OBSERVED_AT,
        )
        result = run_d6(d6_packet("DIFFERENTIAL_TRANSFER"), carrier_result=carrier_result)
        self.assertEqual(carrier_result["CARRIER_RESULT"], "SUCCESS")
        self.assertFalse(result["D6_PASS"])
        self.assertFalse(result["TARGET_PASS"])

    def test_11_missing_joint_d1_d8_has_no_formal_effect(self) -> None:
        result = run_d6(d6_packet())
        self.assertEqual(result["STATE"], "HOLD_D1_D8_JOINT_VERIFICATION_REQUIRED")
        self.assertEqual(result["RUNTIME_EFFECT"], "NONE")

    def test_12_missing_total_field_decision_has_no_live_effect(self) -> None:
        joint_receipt = {
            "RECEIPT_TYPE": "D1_D8_JOINT_VERIFICATION_RECEIPT",
            "DIMENSIONS": {f"D{number}": "VERIFIED" for number in range(1, 9)},
            "JOINTLY_CLOSED": True,
            "RESULT": "VERIFIED",
        }
        result = run_d6(d6_packet(), d1_d8_receipt=joint_receipt)
        self.assertEqual(result["STATE"], "HOLD_TOTAL_FIELD_AUTHORITY_REQUIRED")
        self.assertEqual(result["TOTAL_FIELD_DECISION"], "NOT_PERFORMED")
        self.assertEqual(result["RUNTIME_EFFECT"], "NONE")

    def test_13_ambiguous_legacy_packet_types_are_quarantined(self) -> None:
        for packet_type in ("TRANSFER_PACKET", "DELTA_PACKET", "GENERATIVE_DELTA"):
            with self.subTest(packet_type=packet_type):
                result = classify_transfer_packet({"PACKET_TYPE": packet_type})
                self.assertEqual(result["ROUTE"], "QUARANTINE")
                self.assertEqual(result["STATE"], "HOLD_AMBIGUOUS_TRANSFER_SEMANTICS")
        binding = json.loads(
            (REPO_ROOT / "configs/w7tp/generative_differential_transfer_binding_v2_3.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(set(binding["capability_bindings"]), {
            "D6_GENERATIVE_TRANSMISSION", "DIFFERENTIAL_TRANSFER"
        })

    def test_14_replay_expiry_and_coordinate_drift_hold(self) -> None:
        self.assertEqual(
            run_d6(d6_packet(), seen_nonces={"fixture-nonce-1"})["STATE"],
            "HOLD_REPLAY_DETECTED",
        )
        self.assertEqual(
            run_d6(d6_packet(), current_logical_time=111)["STATE"],
            "HOLD_PACKET_EXPIRED",
        )
        drifted = target_snapshot()
        drifted["SNAPSHOT_REFERENCE"] = "snapshot:drifted"
        self.assertEqual(
            run_d6(d6_packet(), snapshot=drifted)["STATE"],
            "HOLD_COORDINATE_DRIFT",
        )

    def test_15_target_only_state_is_preserved(self) -> None:
        packet, base, payload, target = differential_fixture()
        before = copy.deepcopy(base)
        reconstructed = apply_object_diff(base, payload, packet["APPLY_BOUNDARY"])
        self.assertEqual(base, before)
        self.assertEqual(reconstructed, target)
        self.assertEqual(reconstructed["target_only"], "preserve")
        for schema_path in (
            "schemas/8d/d6_generative_transmission_packet_v2_3.schema.json",
            "schemas/8d/differential_transfer_packet_v1.schema.json",
            "schemas/8d/d6_integer_reconstruction_evidence_v2_3.schema.json",
            "schemas/8d/delta_apply_receipt_v1.schema.json",
        ):
            Draft202012Validator.check_schema(
                json.loads((REPO_ROOT / schema_path).read_text(encoding="utf-8"))
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            receipt_path = Path(temp_dir) / "receipt.json"
            append_only_json(receipt_path, {"RESULT": "FIRST_WRITE"})
            with self.assertRaises(FileExistsError):
                append_only_json(receipt_path, {"RESULT": "OVERWRITE_FORBIDDEN"})


if __name__ == "__main__":
    unittest.main()
