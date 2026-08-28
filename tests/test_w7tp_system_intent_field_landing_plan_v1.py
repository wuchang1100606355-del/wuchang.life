from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/field/w7tp_system_intent_field_landing_plan_v1.schema.json"
PLAN_PATH = ROOT / "configs/total_field/w7tp_system_intent_field_landing_plan_v1.candidate.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SystemIntentFieldLandingPlanV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.plan = load_json(PLAN_PATH)
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def test_schema_and_plan_are_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)
        self.validator.validate(self.plan)

    def test_plan_is_no_effect_and_not_formally_landed(self) -> None:
        self.assertEqual(self.plan["status"], "CANDIDATE_PLAN_ONLY")
        self.assertFalse(self.plan["current_state"]["formal_landing_allowed"])
        self.assertFalse(self.plan["current_state"]["deployment_executed_by_this_plan"])
        decision = self.plan["current_decision"]
        self.assertEqual(decision["state"], "PLAN_COMPLETE_EXECUTION_NOT_STARTED")
        self.assertEqual(decision["formal_effect_count"], 0)
        self.assertEqual(decision["service_restart_count"], 0)
        self.assertEqual(decision["deployment_count"], 0)

    def test_evidence_anchors_match_source_bytes(self) -> None:
        for name, anchor in self.plan["evidence_anchors"].items():
            path = ROOT / anchor["path"]
            self.assertTrue(path.is_file(), name)
            self.assertEqual(sha256_file(path), anchor["sha256"], name)

    def test_single_field_and_authority_boundaries_are_explicit(self) -> None:
        target = self.plan["target_outcome"]
        self.assertTrue(target["single_intent_field"])
        self.assertIn("NOT_A_SECOND_DATABASE", target["intent_definition"])
        authority = self.plan["authority"]
        self.assertEqual(authority["decision_authority"], "TOTAL_FIELD")
        for key, value in authority.items():
            if key in {"decision_authority", "human_semantic_ratification_required"}:
                continue
            self.assertFalse(value, key)

    def test_identity_and_technical_ownership_do_not_collapse_into_runtime(self) -> None:
        boundary = self.plan["identity_and_ownership_boundary"]
        self.assertEqual(
            boundary["member_identity_sovereignty_source"],
            "ASSOCIATION_GOVERNED_MEMBER_IDENTITY_REGISTRY",
        )
        self.assertFalse(boundary["service_system_becomes_member_registry"])
        self.assertFalse(boundary["full_member_plaintext_replication_allowed"])
        self.assertFalse(boundary["xiaoj_w7tp_technical_ownership_transfer_proven"])
        self.assertTrue(boundary["technical_ownership_and_runtime_authority_are_separate"])
        self.assertFalse(boundary["public_interest_authorization_implies_ownership_transfer"])

    def test_all_eight_system_planes_are_unique(self) -> None:
        ids = [plane["plane_id"] for plane in self.plan["system_planes"]]
        self.assertEqual(
            ids,
            [
                "P_CONTROL",
                "P_INTENT",
                "P_STATE",
                "P_EXECUTION",
                "P_RECONSTRUCTION",
                "P_MEMORY",
                "P_EVIDENCE",
                "P_EXPERIENCE",
            ],
        )
        self.assertEqual(len(ids), len(set(ids)))

    def test_d1_to_d8_are_dynamic_fields_with_fail_closed_states(self) -> None:
        fields = self.plan["dynamic_state_fields"]
        self.assertEqual(
            [field["field"].split("_", 1)[0] for field in fields],
            [f"D{index}" for index in range(1, 9)],
        )
        self.assertTrue(
            all("HOLD_" in field["fail_closed_state"] for field in fields)
        )

    def test_construction_order_matches_true8d_sandbox(self) -> None:
        import sys

        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from tools.total_field.w7tp_true8d_contract_sandbox import construction_order

        self.assertEqual(tuple(self.plan["construction_order"]), construction_order())

    def test_model_receives_unknown_delta_contract_only(self) -> None:
        contracts = self.plan["data_contracts"]
        ingress = contracts["volatile_ingress"]
        self.assertFalse(ingress["raw_input_cache_allowed"])
        self.assertFalse(ingress["raw_input_forwarded_to_delta_model"])
        packet = contracts["model_packet"]
        self.assertEqual(packet["output_authority"], "CANDIDATE_ONLY")
        forbidden = set(packet["forbidden_material"])
        self.assertIn("RAW_USER_INPUT", forbidden)
        self.assertIn("MEMBER_PLAINTEXT", forbidden)
        self.assertIn("CREDENTIAL_OR_TOKEN", forbidden)
        self.assertNotIn("RAW_USER_INPUT", set(packet["allowed_material"]))

    def test_nine_phases_are_ordered_and_each_has_rollback(self) -> None:
        phases = self.plan["landing_phases"]
        self.assertEqual(
            [phase["phase_id"].split("_", 1)[0] for phase in phases],
            [f"L{index:02d}" for index in range(9)],
        )
        for phase in phases:
            self.assertTrue(phase["entry_requires"])
            self.assertTrue(phase["deliverables"])
            self.assertTrue(phase["exit_requires"])
            self.assertTrue(phase["rollback"])

    def test_canary_and_production_are_explicitly_held(self) -> None:
        phases = {phase["phase_id"]: phase for phase in self.plan["landing_phases"]}
        self.assertEqual(
            phases["L07_SCOPED_REVOCABLE_CANARY"]["current_state"],
            "HOLD_AUTHORITY_INACTIVE",
        )
        self.assertEqual(
            phases["L08_FORMAL_PROMOTION_AND_OPERATIONS"]["current_state"],
            "HOLD_NOT_AUTHORIZED",
        )
        self.assertEqual(
            self.plan["current_decision"]["first_execution_phase"],
            "L00_SCOPE_AND_AUTHORITY_LOCK",
        )

    def test_safety_precedes_efficiency_and_zero_tolerance_is_complete(self) -> None:
        metrics = self.plan["measurement_framework"]
        self.assertEqual(metrics["ordered_objectives"][0], "DATA_AND_IDENTITY_SAFETY")
        self.assertEqual(
            metrics["ordered_objectives"][-1],
            "MEMORY_COMPUTE_AND_TRANSFER_EFFICIENCY",
        )
        zero = set(metrics["zero_tolerance_metrics"])
        self.assertIn("UNAUTHORIZED_EFFECT_COUNT", zero)
        self.assertIn("MEMBER_PLAINTEXT_LEAK_COUNT", zero)
        self.assertIn("CANONICAL_SOURCE_DELETE_COUNT", zero)
        self.assertIn("EFFECT_WITHOUT_RECEIPT_COUNT", zero)
        self.assertEqual(
            metrics["numeric_threshold_state"],
            "PENDING_BASELINE_AND_HUMAN_REVIEWED_CALIBRATION",
        )

    def test_only_total_field_role_can_grant_formal_runtime_effect(self) -> None:
        roles = self.plan["responsibility_matrix"]
        grantors = [
            role["role"] for role in roles if role["may_grant_runtime_effect_alone"]
        ]
        self.assertEqual(grantors, ["TOTAL_FIELD"])


if __name__ == "__main__":
    unittest.main()
