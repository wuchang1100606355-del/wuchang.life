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
from tools.w7tp_d6_file_reconstruction_v2_3 import (
    build_file_d6_bundle,
    load_packet_from_dual_storage,
    reconstruct_file_to_mmap_stream,
    sha256_bytes,
)
from tools.w7tp_differential_transfer_verifier_v1 import (
    apply_object_diff,
    verify_differential_transfer,
)
from tools.w7tp_transfer_packet_compatibility_v2_3 import classify_transfer_packet
from tools.w7tp_transfer_rule_common import RuleHold, append_only_json, object_sha256


REPO_ROOT = Path(__file__).resolve().parents[1]
OBSERVED_AT = "2026-09-14T00:00:00Z"


def joint_state_field() -> dict:
    return {
        "SEMANTICS": "8_IN_1_SINGLE_STATE_FIELD",
        "REPRESENTATION": "ONE_IMMUTABLE_PACKET_STATE_WITH_EIGHT_COUPLED_PROJECTIONS",
        "PROJECTIONS": {
            "D1": {"INTENT_REFERENCE": "intent:fixture"},
            "D2": {"TARGET_STATE_REFERENCE": "state:fixture:13"},
            "D3": {"RECONSTRUCTION_COORDINATE": "adi:target-node:fixture:13"},
            "D4": {"EVIDENCE_DESTINATION": "fixture:d4-evidence"},
            "D5": {"EXECUTION_SCOPE": "REPOSITORY_RULE_ONLY_NO_LIVE_EFFECT"},
            "D6": {"RECONSTRUCTION_RULE": "TARGET_NATIVE_INTEGER_LOOKUP"},
            "D7": {"MISMATCH_ACTION": "HOLD_WHOLE_STATE_FIELD"},
            "D8": {"AUTHORITY_SCOPE": "NONE"},
        },
        "COUPLING_GRAPH": {
            "D1": ["D2", "D5", "D8"],
            "D2": ["D3", "D4", "D6", "D7"],
            "D3": ["D2", "D4", "D6"],
            "D4": ["D2", "D5", "D7", "D8"],
            "D5": ["D2", "D4", "D6", "D7"],
            "D6": ["D2", "D3", "D4", "D8"],
            "D7": ["D5", "D6", "D8"],
            "D8": ["D1", "D2", "D4", "D7"],
        },
        "CROSS_DIMENSION_CONSTRAINTS": [
            "D1_D2_TARGET_BOUND",
            "D2_D3_BASE_COORDINATE_BOUND",
            "D3_D4_HASH_EVIDENCE_BOUND",
            "D4_D5_EXECUTION_GATED",
            "D5_D6_RECONSTRUCTION_ONLY",
            "D6_D7_MISMATCH_HOLDS",
            "D7_D8_NO_AUTHORITY_ESCALATION",
            "D8_D1_SCOPE_BOUND",
        ],
        "JOINT_STATE_TRANSITION": "CURRENT_8D_FIELD_TO_RECONSTRUCTED_TARGET_8D_FIELD",
        "CLOSURE_RULE": "ALL_EIGHT_PROJECTIONS_AND_TARGET_EFFECT_REOBSERVED",
        "FAIL_CLOSED_RULE": "ANY_MISMATCH_HOLDS_WHOLE_STATE_FIELD",
    }


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
        "OPERATION_PROFILE": "INTEGER_STATE_INDEX",
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
        "JOINT_STATE_FIELD": joint_state_field(),
        "MODEL_ORGAN": {
            "LOCAL_LLM_ORGAN_REFERENCE": "model:local:fixture",
            "ROLE": "PASSIVE_REPLACEABLE_REASONING_GENERATION_ORGAN",
            "DYNAMIC_CONTEXT_REFERENCE": "context:dynamic:fixture",
            "AUTHORITY": "NONE",
        },
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


def file_reconstruction_bundle() -> tuple[dict, bytes, bytes]:
    previous_base = b"AAAABBBBAAAACCCC"
    target = b"AAAAXXXXCCCCBBBB"
    bundle = build_file_d6_bundle(
        target=target,
        previous_base=previous_base,
        block_size=4,
        source_identity="source-node",
        target_identity="target-node",
        target_snapshot_reference="snapshot:target-node:file:1",
        reconstruction_coordinate="adi:target-node:file:1",
        design_file_reference="design:file:fixture",
        target_base_reference="state:target-node:file:base:1",
        output_relative_path="reconstructed/fixture.bin",
        local_packet_reference="packet:local:fixture",
        cloud_packet_reference="packet:cloud:fixture",
        local_llm_organ_reference="model:local:fixture",
        dynamic_context_reference="context:dynamic:fixture",
        nonce="file-fixture-nonce-1",
        logical_time=100,
        ttl=10,
        evidence_destination="evidence:file:fixture",
    )
    return bundle, previous_base, target


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
        packet = d6_packet()
        joint_receipt = {
            "RECEIPT_TYPE": "D1_D8_JOINT_VERIFICATION_RECEIPT",
            "DIMENSIONS": {f"D{number}": "VERIFIED" for number in range(1, 9)},
            "JOINTLY_CLOSED": True,
            "RESULT": "VERIFIED",
            "PACKET_DIGEST": object_sha256(packet),
            "JOINT_STATE_DIGEST": object_sha256(packet["JOINT_STATE_FIELD"]),
        }
        result = run_d6(packet, d1_d8_receipt=joint_receipt)
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

    def test_16_split_or_unclosed_8d_packet_holds(self) -> None:
        packet = d6_packet()
        packet["JOINT_STATE_FIELD"]["COUPLING_GRAPH"]["D8"] = ["D8"]
        self.assertEqual(run_d6(packet)["STATE"], "HOLD_D1_D8_COUPLING_NOT_CLOSED")

    def test_17_joint_receipt_must_bind_packet_and_joint_state(self) -> None:
        packet = d6_packet()
        receipt = {
            "RECEIPT_TYPE": "D1_D8_JOINT_VERIFICATION_RECEIPT",
            "DIMENSIONS": {f"D{number}": "VERIFIED" for number in range(1, 9)},
            "JOINTLY_CLOSED": True,
            "RESULT": "VERIFIED",
            "PACKET_DIGEST": "0" * 64,
            "JOINT_STATE_DIGEST": object_sha256(packet["JOINT_STATE_FIELD"]),
        }
        result = run_d6(packet, d1_d8_receipt=receipt)
        self.assertEqual(result["STATE"], "HOLD_D1_D8_JOINT_VERIFICATION_REQUIRED")

    def test_18_file_reconstruction_is_ephemeral_and_exact(self) -> None:
        bundle, previous_base, target = file_reconstruction_bundle()
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base.bin"
            base_path.write_bytes(previous_base)
            events = []
            result = reconstruct_file_to_mmap_stream(
                bundle["PACKET"],
                target_field_snapshot=bundle["TARGET_FIELD_SNAPSHOT"],
                lookup_table=bundle["LOOKUP_TABLE"],
                transition_rule_document=bundle["TRANSITION_RULE"],
                previous_base_path=base_path,
                current_logical_time=105,
                event_sink=events.append,
                segment_bytes=4,
                observed_at=OBSERVED_AT,
            )
        self.assertEqual(result["RECONSTRUCTED_FILE_SHA256"], sha256_bytes(target))
        self.assertEqual(result["EVENTS"], events)
        self.assertFalse(result["RAW_BYTES_EMITTED"])
        self.assertFalse(result["PERSISTENT_FILE_WRITTEN"])
        self.assertFalse(result["D6_PASS"])
        self.assertFalse(result["END_TO_END_PASS"])

    def test_19_file_reconstruction_rejects_wrong_target_base(self) -> None:
        bundle, previous_base, _ = file_reconstruction_bundle()
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir) / "base.bin"
            base_path.write_bytes(b"Z" * len(previous_base))
            with self.assertRaisesRegex(RuleHold, "HOLD_TARGET_BASE_HASH_MISMATCH"):
                reconstruct_file_to_mmap_stream(
                    bundle["PACKET"],
                    target_field_snapshot=bundle["TARGET_FIELD_SNAPSHOT"],
                    lookup_table=bundle["LOOKUP_TABLE"],
                    transition_rule_document=bundle["TRANSITION_RULE"],
                    previous_base_path=base_path,
                    current_logical_time=105,
                    observed_at=OBSERVED_AT,
                )

    def test_20_dual_storage_is_digest_bound_and_local_first(self) -> None:
        bundle, _, _ = file_reconstruction_bundle()
        packet_bytes = bundle["PACKET_BYTES"]
        expected_sha256 = sha256_bytes(packet_bytes)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local_path = root / "local.packet"
            cloud_path = root / "cloud.packet"
            cloud_path.write_bytes(packet_bytes)
            packet, source = load_packet_from_dual_storage(
                local_packet_path=local_path,
                cloud_packet_path=cloud_path,
                expected_sha256=expected_sha256,
            )
            self.assertEqual(source, "CLOUD")
            self.assertEqual(packet, bundle["PACKET"])
            local_path.write_bytes(packet_bytes)
            cloud_path.write_bytes(b"tampered")
            packet, source = load_packet_from_dual_storage(
                local_packet_path=local_path,
                cloud_packet_path=cloud_path,
                expected_sha256=expected_sha256,
            )
            self.assertEqual(source, "LOCAL")
            self.assertEqual(packet, bundle["PACKET"])


if __name__ == "__main__":
    unittest.main()
