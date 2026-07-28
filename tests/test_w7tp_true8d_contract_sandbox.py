#!/usr/bin/env python3
"""Targeted P2 contract, shadow, fault, and authority tests."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field.w7tp_true8d_contract_sandbox import (
    COMMON_INPUT_FIELDS,
    CONSUMERS,
    D8_FIELDS,
    FIELD_IDS,
    HARD_RISK_CODES,
    PROFILES,
    ContractSandboxError,
    ACTIVE_CANONICAL_SCHEMA_REF,
    ACTIVE_CONTRACT_VERSION,
    LEGACY_CANONICAL_SCHEMA_REF,
    LEGACY_CONTRACT_VERSION,
    build_p2_evidence,
    canonical_sha256,
    run_shadow_case,
    validate_common_input,
    validate_field_output,
    validate_projection_contract,
    validate_resource_budget,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/field/w7tp_true8d_projection_contract_v2_1.schema.json"
LEGACY_SCHEMA_PATH = ROOT / "schemas/field/w7tp_true8d_projection_contract_v2.schema.json"
FIXTURE_PATH = ROOT / "tests/fixtures/w7tp_true8d_p2_shadow_vectors.json"


class True8DContractSandboxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.legacy_schema = json.loads(LEGACY_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        Draft202012Validator.check_schema(cls.legacy_schema)

    def test_five_profiles_by_seven_consumers_pass_read_only(self) -> None:
        evidence = build_p2_evidence("TEST_P2")
        self.assertEqual(len(evidence["profile_results"]), 35)
        self.assertTrue(evidence["target_compatibility_pass"])
        self.assertEqual(set(evidence["five_profile_results"]), set(PROFILES))
        self.assertTrue(all(value == "PASS" for value in evidence["five_profile_results"].values()))
        for result in evidence["profile_results"]:
            self.assertTrue(result["semantic_result_equivalent"])
            self.assertTrue(result["total_state_hash_equivalent"])
            self.assertEqual(result["fixed_point_status"], "REACHED")
            self.assertEqual(result["fixed_point_rounds"], 2)
            self.assertIsNone(result["d8_final_decision"])
            self.assertFalse(result["commit_applied"])
            self.assertFalse(result["seal_applied"])
            self.assertEqual(result["side_effect_count"], 0)
            self.assertEqual(result["authority_increase_count"], 0)
            self.assertEqual(result["profile_mutation_count"], 0)

    def test_same_input_same_output_hash(self) -> None:
        first = run_shadow_case("CAFE_POS", "POS")
        second = run_shadow_case("CAFE_POS", "POS")
        self.assertEqual(first["input_hash"], second["input_hash"])
        self.assertEqual(first["output_hash"], second["output_hash"])
        self.assertEqual(first["field_vector_hash"], second["field_vector_hash"])

    def test_unknown_scene_holds_without_side_effect(self) -> None:
        result = run_shadow_case("UNKNOWN", "COMMUNITY")
        self.assertEqual(result["state"], "HOLD_UNKNOWN_SCENE")
        self.assertEqual(result["side_effect_count"], 0)

    def test_machine_input_rejects_missing_extra_float_and_identity_mismatch(self) -> None:
        route = json.loads((ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json").read_text(encoding="utf-8"))["routes"]["GENERIC"]
        from tools.total_field.w7tp_true8d_contract_sandbox import _common
        valid = _common("D1", "GENERIC", "INTENT", route)
        self.assertEqual(tuple(valid), COMMON_INPUT_FIELDS)
        cases = []
        missing = copy.deepcopy(valid); missing.pop("snapshot_id"); cases.append((missing, "D1", "HOLD_FIELD_INPUT_MISSING"))
        extra = copy.deepcopy(valid); extra["extra"] = 1; cases.append((extra, "D1", "HOLD_FIELD_INPUT_EXTRA"))
        floating = copy.deepcopy(valid); floating["logical_time"] = 1.5; cases.append((floating, "D1", "HOLD_FIELD_FLOAT_FORBIDDEN"))
        mismatch = copy.deepcopy(valid); mismatch["field_id"] = "D2"; cases.append((mismatch, "D1", "QUARANTINE_FIELD_IDENTITY_MISMATCH"))
        for value, field_id, code in cases:
            with self.subTest(code=code), self.assertRaises(ContractSandboxError) as caught:
                validate_common_input(value, field_id)
            self.assertEqual(caught.exception.code, code)

    def test_d7_hard_risk_cannot_be_downgraded(self) -> None:
        for risk in HARD_RISK_CODES:
            with self.subTest(risk=risk):
                with self.assertRaises(ContractSandboxError) as caught:
                    validate_field_output("D7", {"risk_codes": [risk], "risk_level": "HARD", "disposition": "HOLD", "blocking_evidence_refs": ["evidence:redacted"]})
                self.assertEqual(caught.exception.code, "BLOCK_D7_HARD_RISK_PRECEDENCE")
                accepted = validate_field_output("D7", {"risk_codes": [risk], "risk_level": "HARD", "disposition": "BLOCK", "blocking_evidence_refs": ["evidence:redacted"]})
                self.assertEqual(accepted["disposition"], "BLOCK")

    def test_d8_exact_canonical_fields_and_no_authority(self) -> None:
        case = run_shadow_case("ASSOCIATION", "INTENT")
        self.assertIsNone(case["d8_final_decision"])
        self.assertEqual(tuple(D8_FIELDS), ("packet_id", "authority_ref", "version", "ttl_seconds", "nonce", "sha256", "verifier_ref", "seal_policy"))
        output = {"packet_id": "packet:test", "authority_ref": "TOTAL_FIELD_CORE_UNDER_FOUNDER_AUTHORITY", "version": "2.1", "ttl_seconds": 1, "nonce": "nonce:test", "sha256": "0" * 64, "verifier_ref": "verifier:test", "seal_policy": "NO_COMMIT_NO_SEAL_READ_ONLY_SHADOW"}
        self.assertEqual(tuple(validate_field_output("D8", output)), D8_FIELDS)
        output["final_decision"] = "ALLOW"
        with self.assertRaises(ContractSandboxError):
            validate_field_output("D8", output)

    def test_integer_resource_budget_arithmetic(self) -> None:
        result = validate_resource_budget()
        self.assertEqual(result["projection_totals"], self.fixture["resource_totals"])
        self.assertEqual(result["total_ceiling"], self.fixture["total_ceiling"])
        self.assertEqual(result["container_start_count"], 0)

    def test_profile_set_and_matrix_fixture_are_locked(self) -> None:
        self.assertEqual(tuple(self.fixture["profiles"]), PROFILES)
        self.assertEqual(tuple(self.fixture["consumers"]), CONSUMERS)
        self.assertEqual(canonical_sha256(self.fixture["profiles"]), self.fixture["expected_profile_set_sha256"])
        self.assertEqual(self.fixture["expected_case_count"], len(PROFILES) * len(CONSUMERS))

    def test_schema_accepts_generated_d8_contract(self) -> None:
        from tools.total_field.w7tp_true8d_contract_sandbox import _common
        route = json.loads((ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json").read_text(encoding="utf-8"))["routes"]["GENERIC"]
        common = _common("D8", "GENERIC", "INTENT", route)
        output = {"packet_id": "packet:test", "authority_ref": "TOTAL_FIELD_CORE_UNDER_FOUNDER_AUTHORITY", "version": "2.1", "ttl_seconds": 1, "nonce": "nonce:test", "sha256": "0" * 64, "verifier_ref": "verifier:test", "seal_policy": "NO_COMMIT_NO_SEAL_READ_ONLY_SHADOW"}
        self.assertEqual(list(Draft202012Validator(self.schema).iter_errors({"common_input": common, "output": output})), [])
        self.assertEqual(
            validate_projection_contract(common, output),
            {"common_input": common, "output": output},
        )

    def test_explicit_v2_input_remains_legacy_schema_compatible(self) -> None:
        from tools.total_field.w7tp_true8d_contract_sandbox import _common
        route = json.loads((ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json").read_text(encoding="utf-8"))["routes"]["GENERIC"]
        common = _common("D8", "GENERIC", "INTENT", route)
        common["contract_version"] = LEGACY_CONTRACT_VERSION
        common["canonical_schema_ref"] = LEGACY_CANONICAL_SCHEMA_REF
        output = {"packet_id": "packet:legacy", "authority_ref": "TOTAL_FIELD_CORE_UNDER_FOUNDER_AUTHORITY", "version": "2.0", "ttl_seconds": 1, "nonce": "nonce:legacy", "sha256": "0" * 64, "verifier_ref": "verifier:legacy", "seal_policy": "NO_COMMIT_NO_SEAL_READ_ONLY_SHADOW"}
        self.assertEqual(
            list(
                Draft202012Validator(self.legacy_schema).iter_errors(
                    {"common_input": common, "output": output}
                )
            ),
            [],
        )
        self.assertEqual(
            validate_projection_contract(common, output),
            {"common_input": common, "output": output},
        )
        self.assertEqual(ACTIVE_CONTRACT_VERSION, "W7TP-TRUE8D-MACHINE-CONTRACT/2.1")
        self.assertEqual(
            ACTIVE_CANONICAL_SCHEMA_REF,
            "schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json",
        )


if __name__ == "__main__":
    unittest.main()
