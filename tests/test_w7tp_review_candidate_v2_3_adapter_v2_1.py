from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from tools.total_field import w7tp_review_candidate_v2_3_adapter_v2_1 as adapter
from tools.total_field.w7tp_canonical_v2_1_legacy_adapter import (
    ContractViolation,
    InMemoryReplayGuard,
    validate_v2_1_packet,
)


ROOT = Path(__file__).resolve().parents[1]
LEGACY_TEST_PATH = ROOT / "tests/test_w7tp_review_candidate_v2_3_adapter.py"


def _load_legacy_test_module():
    spec = importlib.util.spec_from_file_location(
        "w7tp_legacy_adapter_test_fixture",
        LEGACY_TEST_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("legacy adapter test fixture is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewCandidateV23AdapterV21Tests(unittest.TestCase):
    def setUp(self) -> None:
        legacy_module = _load_legacy_test_module()
        self.legacy_case = legacy_module.ReviewCandidateV23AdapterTests(
            methodName="test_adapter_builds_schema_valid_l3_candidate_without_authority"
        )
        self.legacy_case.setUp()
        self.source_bytes = bytes(self.legacy_case.source_bytes)
        self.legacy_request = deepcopy(self.legacy_case.request)
        self.now = self.legacy_case.now
        self.workspace = self.legacy_case.workspace
        self.request = self._successor_request()

    def tearDown(self) -> None:
        self.legacy_case.tearDown()

    def _successor_request(self) -> dict:
        request = {
            "adapter_contract_version": adapter.ADAPTER_CONTRACT_VERSION,
            "legacy_request_schema_ref": (
                "schemas/field/"
                "w7tp_review_candidate_v2_3_adapter_request_v1.schema.json"
            ),
            "legacy_request_self_sha256": self.legacy_request[
                "request_self_sha256"
            ],
            "source_packet_raw_sha256": self.legacy_request[
                "source_packet_raw_sha256"
            ],
            "source_packet_canonical_sha256": self.legacy_request[
                "source_packet_canonical_sha256"
            ],
            "canonical_binding": {
                "canonical_path": adapter.CANONICAL_REF,
                "canonical_sha256": adapter.CANONICAL_SHA256,
                "parent_path": adapter.PARENT_CANONICAL_REF,
                "parent_sha256": adapter.PARENT_CANONICAL_SHA256,
                "migration_mode": "APPEND_ONLY_SUCCESSOR",
            },
            "output_contract": {
                "packet_id": "W7TP_REVIEW_REQ_V2_1_20260722T120000Z",
                "namespace": "w7tp.review-candidate.v2-1",
                "logical_time": "2026-07-22T12:00:00Z",
                "nonce": "nonce_v2_1_20260722T120000Z_8f7d",
                "authority_ref": "authority:local-total-field",
                "key_version_ref": "key-version:local-authority:v1",
                "state_transition_ref": "transition:review-candidate:v2-to-v2-1",
                "previous_seal_ref": "seal:legacy-v2-adapter:validated",
                "total_field_verifier_ref": "verifier:total-field:v2-1",
                "evidence_refs": [
                    "evidence:legacy-v2-adapter:pass",
                    "evidence:founder-canonical-v2-1",
                ],
                "verification": {
                    "mode": "L3_CANDIDATE",
                    "candidate_only": True,
                    "authorization": "NONE",
                    "local_decision_machine_ref": "verifier:total-field:v2-1",
                },
                "protected_refs": [
                    {
                        "protected_type": "H64_TD",
                        "reference": "capability:h64-td:reference-only",
                    }
                ],
            },
            "request_self_hash_algorithm": (
                "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0"
            ),
            "request_self_sha256": "0" * 64,
        }
        return adapter.with_successor_request_self_hash(request)

    def adapt(self, **kwargs) -> dict:
        return adapter.adapt_review_candidate_v2_3_to_v2_1(
            self.source_bytes,
            self.legacy_request,
            self.request,
            workspace_root=self.workspace,
            now=self.now,
            **kwargs,
        )

    def test_request_schema_is_valid_and_accepts_successor_request(self) -> None:
        schema = json.loads(adapter.REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual(
            list(Draft202012Validator(schema).iter_errors(self.request)),
            [],
        )

    def test_builds_deterministic_v2_1_candidate_without_mutation(self) -> None:
        source_before = bytes(self.source_bytes)
        legacy_before = deepcopy(self.legacy_request)
        request_before = deepcopy(self.request)

        first = self.adapt()
        second = self.adapt()

        self.assertEqual(
            first["state"],
            "PASS_V2_1_ADAPTER_CONTRACT_RECONSTRUCTED_CANDIDATE",
        )
        self.assertEqual(first, second)
        self.assertEqual(self.source_bytes, source_before)
        self.assertEqual(self.legacy_request, legacy_before)
        self.assertEqual(self.request, request_before)
        packet = first["canonical_packet"]
        self.assertEqual(packet["canonical_id"], adapter.CANONICAL_ID)
        self.assertEqual(packet["version"], "2.1")
        self.assertEqual(
            packet["canonical_binding"]["parent_sha256"],
            adapter.PARENT_CANONICAL_SHA256,
        )
        self.assertTrue(packet["lineage"]["append_only"])
        self.assertEqual(
            list(packet["state_field"]["dimensions"]),
            list(adapter.CORE_DIMENSIONS),
        )
        validate_v2_1_packet(packet)
        self.assertTrue(adapter.verify_v2_1_packet_hash(packet))
        self.assertEqual(
            first["canonical_packet_sha256"],
            packet["envelope"]["canonical_json_sha256"],
        )
        tampered_payload = deepcopy(packet)
        tampered_payload["envelope"]["payload_sha256"] = "0" * 64
        self.assertFalse(adapter.verify_v2_1_packet_hash(tampered_payload))
        tampered_canonical = deepcopy(packet)
        tampered_canonical["envelope"]["canonical_json_sha256"] = "0" * 64
        self.assertFalse(adapter.verify_v2_1_packet_hash(tampered_canonical))
        self.assertFalse(first["authority_granted"])
        self.assertTrue(first["candidate_only"])

    def test_verification_modes_are_structurally_separate(self) -> None:
        cases = [
            {
                "mode": "L1_EXACT_BYTES",
                "raw_sha256": self.legacy_request["source_packet_raw_sha256"],
                "byte_length": len(self.source_bytes),
                "hash_scope_ref": "ref:source-packet:raw-bytes",
            },
            {
                "mode": "L2_EFFECT_EQUIVALENT",
                "effect_contract_ref": "ref:review-state:effect-contract",
                "comparison_fields": ["decision", "state", "risk"],
                "evidence_refs": ["evidence:effect-contract:fixture"],
            },
            {
                "mode": "L3_CANDIDATE",
                "candidate_only": True,
                "authorization": "NONE",
                "local_decision_machine_ref": "verifier:total-field:v2-1",
            },
        ]
        for verification in cases:
            with self.subTest(mode=verification["mode"]):
                self.request["output_contract"]["verification"] = verification
                self.request = adapter.with_successor_request_self_hash(self.request)
                result = self.adapt()
                self.assertTrue(result["state"].startswith("PASS_"))
                projected = result["canonical_packet"]["verification"]
                validate_v2_1_packet(result["canonical_packet"])
                if verification["mode"] == "L1_EXACT_BYTES":
                    self.assertEqual(projected["mode"], "L1_EXACT_BYTE")
                    self.assertEqual(projected["decision"], "HOLD")
                elif verification["mode"] == "L2_EFFECT_EQUIVALENT":
                    self.assertEqual(
                        projected["mode"],
                        "L2_EFFECT_EQUIVALENT",
                    )
                    self.assertEqual(projected["decision"], "HOLD")
                else:
                    self.assertEqual(projected["mode"], "L3_CANDIDATE")
                    self.assertFalse(projected["final_authority_granted"])

    def test_replay_and_non_append_only_logical_time_hold(self) -> None:
        replay_tuple = (
            "authority:local-total-field|w7tp.review-candidate.v2-1|"
            "nonce_v2_1_20260722T120000Z_8f7d"
        )
        replay = self.adapt(seen_nonces={replay_tuple})
        self.assertEqual(replay["reason_code"], "HOLD_REPLAY_DETECTED")

        self.request["output_contract"]["logical_time"] = "2026-07-22T00:00:00Z"
        self.request = adapter.with_successor_request_self_hash(self.request)
        stale = self.adapt()
        self.assertEqual(
            stale["reason_code"],
            "HOLD_LOGICAL_TIME_NOT_APPEND_ONLY",
        )

        self.request = self._successor_request()
        packet = self.adapt()["canonical_packet"]
        guard = InMemoryReplayGuard()
        guard.accept(packet)
        with self.assertRaises(ContractViolation):
            guard.accept(packet)

    def test_protected_material_must_remain_reference_only(self) -> None:
        self.request["output_contract"]["protected_refs"][0]["material"] = (
            "forbidden-inline-value"
        )
        self.request = adapter.with_successor_request_self_hash(self.request)
        result = self.adapt()
        self.assertEqual(
            result["reason_code"],
            "HOLD_V2_1_REQUEST_SCHEMA_INVALID",
        )
        self.assertIsNone(result["canonical_packet"])

    def test_legacy_v2_projection_remains_distinct_and_readable(self) -> None:
        legacy_result = self.legacy_case.adapt()
        successor_result = self.adapt()
        self.assertTrue(legacy_result["state"].startswith("PASS_"))
        self.assertEqual(legacy_result["canonical_packet"]["version"], "2.0.0")
        self.assertEqual(
            successor_result["canonical_packet"]["version"],
            "2.1",
        )
        self.assertNotEqual(
            legacy_result["canonical_packet_sha256"],
            successor_result["canonical_packet_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
