from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = (
    ROOT
    / "configs/total_field/w7tp_system_intent_field_founder_clarification_v1.candidate.json"
)
SCHEMA_PATH = (
    ROOT
    / "schemas/field/w7tp_system_intent_field_founder_clarification_v1.schema.json"
)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FounderIntentClarificationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = load_json(PACKET_PATH)
        cls.schema = load_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def assert_invalid(self, candidate: dict[str, object]) -> None:
        with self.assertRaises(ValidationError):
            self.validator.validate(candidate)

    def test_packet_is_schema_valid_candidate_delta(self) -> None:
        self.validator.validate(self.packet)
        self.assertEqual(
            self.packet["current_decision"],
            "HOLD_CONFLICTS_RECORDED_NO_AUTO_MERGE",
        )
        self.assertEqual(
            self.packet["next"],
            "RECONCILE_EXISTING_INTENT_FIELD_CONFLICTS_BEFORE_MERGE",
        )

    def test_internal_source_bindings_match_current_exact_bytes(self) -> None:
        for binding in self.packet["source_bindings"]:
            coordinate = binding["coordinate"]
            if coordinate.startswith("windows-path:"):
                self.assertEqual(binding["state"], "EXTERNAL_METADATA_ONLY")
                continue
            self.assertEqual(sha256_file(ROOT / coordinate), binding["sha256"])

    def test_alignment_counts_and_ids_are_exact(self) -> None:
        alignment = self.packet["alignment"]
        ids = [item["item_id"] for item in alignment]
        self.assertEqual(len(ids), len(set(ids)))
        counts = {
            state: sum(item["state"] == state for item in alignment)
            for state in ("ALIGNED", "CONFLICT", "UNKNOWN")
        }
        self.assertEqual(counts["ALIGNED"], 4)
        self.assertEqual(counts["CONFLICT"], 4)
        self.assertEqual(counts["UNKNOWN"], 3)
        self.assertEqual(sum(counts.values()), 11)
        self.assertEqual(
            self.packet["conflict_summary"],
            {"aligned": 4, "conflict": 4, "unknown": 3, "total": 11},
        )

    def test_founder_and_total_field_scopes_are_not_collapsed(self) -> None:
        governance = self.packet["intent_statements"]["governance"]
        self.assertEqual(governance["unique_rule_modification_principal"], "FOUNDER_ONLY")
        self.assertEqual(
            governance["runtime_policy_decision_scope"],
            "TOTAL_FIELD_WITHIN_FOUNDER_DEFINED_RULES",
        )
        self.assertFalse(governance["total_field_can_override_founder"])
        self.assertTrue(governance["rule_modification_requires_exact_founder_packet"])

    def test_local_model_is_translation_dialogue_only_and_no_authority(self) -> None:
        local_llm = self.packet["intent_statements"]["local_llm"]
        self.assertEqual(
            local_llm["operational_role"],
            "INTENT_TRANSLATION_AND_DIALOGUE_CAPABILITY_MANAGEMENT_ONLY",
        )
        self.assertFalse(local_llm["candidate_content_generation_allowed"])
        self.assertEqual(local_llm["model_authority"], "NONE")
        self.assertEqual(local_llm["preferred_isolation"], "DEDICATED_CONTAINER")

    def test_personal_devices_and_information_remain_packet_scoped(self) -> None:
        statements = self.packet["intent_statements"]
        devices = statements["personal_devices"]
        personal = statements["personal_information"]
        self.assertEqual(devices["personal_computer_node"], "MSI")
        self.assertEqual(devices["personal_mobile_node"], "UNKNOWN_UNVERIFIED")
        self.assertTrue(devices["phone_verifies_computer_replacement"])
        self.assertTrue(devices["computer_verifies_phone_replacement"])
        self.assertFalse(devices["device_is_founder_authority"])
        self.assertEqual(personal["governance_source"], "PERSONAL_SOVEREIGNTY_PACKET")
        self.assertFalse(personal["unscoped_cloud_projection_allowed"])

    def test_cloud_writer_identity_and_vpn_do_not_create_authority(self) -> None:
        statements = self.packet["intent_statements"]
        cloud = statements["cloud_governance"]
        receipt = statements["receipt_transport"]
        self.assertEqual(
            cloud["write_principals"],
            ["SPACE_ADMIN_ACCOUNT", "TOTAL_FIELD_SERVICE_ACCOUNT"],
        )
        self.assertFalse(cloud["writer_identity_is_authority"])
        self.assertEqual(receipt["carrier_authority"], "NONE")
        self.assertEqual(receipt["state"], "CANDIDATE_DESIGN_INTENT_REQUIRES_ALIGNMENT")

    def test_schema_rejects_authority_or_state_escalation(self) -> None:
        candidate = copy.deepcopy(self.packet)
        candidate["intent_statements"]["governance"]["total_field_can_override_founder"] = True
        self.assert_invalid(candidate)

        candidate = copy.deepcopy(self.packet)
        candidate["intent_statements"]["local_llm"]["model_authority"] = "FULL"
        self.assert_invalid(candidate)

        candidate = copy.deepcopy(self.packet)
        candidate["authority"]["auto_merge_allowed"] = True
        self.assert_invalid(candidate)

        candidate = copy.deepcopy(self.packet)
        candidate["current_decision"] = "MERGED_ACTIVE"
        self.assert_invalid(candidate)



# C01_EXPLICIT_SEMANTICS_TESTS_V1
import json as _c01_json
import unittest as _c01_unittest
from pathlib import Path as _C01Path


def _c01_find_candidate_governance(obj):
    if isinstance(obj, dict):
        if (
            obj.get("system_owner") == "FOUNDER"
            and obj.get("canonical_maker") == "FOUNDER"
            and obj.get("total_field_can_override_founder") is False
        ):
            return obj
        for value in obj.values():
            found = _c01_find_candidate_governance(value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _c01_find_candidate_governance(value)
            if found is not None:
                return found
    return None


def _c01_find_schema_governance(obj):
    if isinstance(obj, dict):
        props = obj.get("properties")
        if isinstance(props, dict) and {
            "system_owner",
            "canonical_maker",
            "total_field_can_override_founder",
            "runtime_policy_decision_scope",
        }.issubset(props):
            return obj
        for value in obj.values():
            found = _c01_find_schema_governance(value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _c01_find_schema_governance(value)
            if found is not None:
                return found
    return None


class FounderIntentClarificationC01ExplicitSemanticsTests(
    _c01_unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        root = _C01Path(__file__).resolve().parents[1]

        cls.candidate = _c01_json.loads(
            (
                root
                / "configs/total_field/"
                  "w7tp_system_intent_field_founder_clarification_v1.candidate.json"
            ).read_text(encoding="utf-8")
        )

        cls.schema = _c01_json.loads(
            (
                root
                / "schemas/field/"
                  "w7tp_system_intent_field_founder_clarification_v1.schema.json"
            ).read_text(encoding="utf-8")
        )

        cls.gov = _c01_find_candidate_governance(cls.candidate)
        cls.schema_gov = _c01_find_schema_governance(cls.schema)

        if cls.gov is None:
            raise AssertionError("Founder governance candidate block not found")

        if cls.schema_gov is None:
            raise AssertionError("Founder governance schema block not found")

    def test_c01_founder_is_only_grant_origin(self):
        self.assertEqual(
            self.gov["grant_origin"],
            "FOUNDER_ONLY",
        )
        self.assertFalse(
            self.gov["total_field_can_create_founder_grant"]
        )
        self.assertFalse(
            self.gov["grant_scope_expansion_by_total_field"]
        )

    def test_c01_policy_allow_is_not_d8_grant(self):
        self.assertFalse(
            self.gov["policy_allow_equals_d8_grant"]
        )

    def test_c01_fail_closed_rule_and_d8_semantics(self):
        self.assertEqual(
            self.gov["missing_founder_rule_effect"],
            "HOLD",
        )
        self.assertEqual(
            self.gov["ambiguous_founder_rule_effect"],
            "HOLD",
        )
        self.assertEqual(
            self.gov["invalid_d8_effect"],
            "HOLD",
        )
        self.assertEqual(
            self.gov["expired_d8_effect"],
            "HOLD",
        )
        self.assertEqual(
            self.gov["d8_scope_mismatch_effect"],
            "HOLD",
        )

    def test_c01_runtime_allow_is_exactly_bounded(self):
        self.assertEqual(
            self.gov["runtime_allow_preconditions"],
            [
                "VALID_FOUNDER_RULE",
                "APPLICABLE_CURRENT_STATE",
                "REQUIRED_EVIDENCE",
                "VALID_D8",
                "VALID_EFFECT_CONTRACT",
            ],
        )

        self.assertEqual(
            self.gov["total_field_runtime_allow_scope"],
            "EXACT_GRANTED_SCOPE_ONLY",
        )

        self.assertEqual(
            self.gov["executor_boundary"],
            "EXECUTOR_ONLY_WITHIN_VALID_TOTAL_FIELD_DECISION_AND_EFFECT_CONTRACT",
        )

    def test_c01_schema_enforces_explicit_semantics(self):
        required = set(self.schema_gov["required"])
        props = self.schema_gov["properties"]

        expected = {
            "grant_origin": "FOUNDER_ONLY",
            "total_field_can_create_founder_grant": False,
            "grant_scope_expansion_by_total_field": False,
            "policy_allow_equals_d8_grant": False,
            "missing_founder_rule_effect": "HOLD",
            "ambiguous_founder_rule_effect": "HOLD",
            "invalid_d8_effect": "HOLD",
            "expired_d8_effect": "HOLD",
            "d8_scope_mismatch_effect": "HOLD",
            "runtime_allow_preconditions": [
                "VALID_FOUNDER_RULE",
                "APPLICABLE_CURRENT_STATE",
                "REQUIRED_EVIDENCE",
                "VALID_D8",
                "VALID_EFFECT_CONTRACT",
            ],
            "total_field_runtime_allow_scope":
                "EXACT_GRANTED_SCOPE_ONLY",
            "executor_boundary":
                "EXECUTOR_ONLY_WITHIN_VALID_TOTAL_FIELD_DECISION_AND_EFFECT_CONTRACT",
        }

        for key, value in expected.items():
            self.assertIn(key, required)
            self.assertEqual(props[key], {"const": value})

if __name__ == "__main__":
    unittest.main()
