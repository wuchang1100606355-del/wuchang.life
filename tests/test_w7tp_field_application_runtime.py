from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.total_field.w7tp_field_application_runtime import (
    CAPABILITY_REGISTRY_PATH,
    SCENARIO_ROUTE_TABLE_PATH,
    FieldApplicationError,
    build_field_application_packet,
    canonical_sha256,
    parse_intent,
)


EXPECTED_SCENARIOS = {"ASSOCIATION", "PROPERTY", "CAFE_POS", "HOUSEHOLD", "GENERIC"}


class W7TPFieldApplicationRuntimeTest(unittest.TestCase):
    def test_all_registered_application_scenarios_build_8d_candidates(self) -> None:
        route_table = json.loads(SCENARIO_ROUTE_TABLE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(route_table["routes"]), EXPECTED_SCENARIOS)
        for scenario in sorted(EXPECTED_SCENARIOS):
            with self.subTest(scenario=scenario):
                packet = build_field_application_packet(
                    scenario,
                    {"requested_result": f"candidate:{scenario.casefold()}"},
                )
                route = route_table["routes"][scenario]
                self.assertEqual(packet["D1"]["scenario"], scenario)
                self.assertEqual(packet["D3"]["packet_type"], route["packet_type"])
                self.assertEqual(packet["D4"]["capability_ref"], route["capability_ref"])
                self.assertTrue(packet["D5"]["candidate_only"])
                self.assertEqual(packet["D8"]["decision"], "PENDING_TOTAL_FIELD_REVIEW")

    def test_generates_protocol_native_8d_not_file_transfer(self) -> None:
        packet = build_field_application_packet("GENERIC", {"requested_result": "candidate"})
        self.assertEqual(
            packet["D6"]["generative_transmission"],
            "PROTOCOL_NATIVE_8D_STATE_FIELD_PACKET",
        )
        self.assertTrue(packet["D6"]["packet_carried_protocol"])
        self.assertTrue(packet["D6"]["packet_carried_validation"])
        self.assertEqual(packet["D6"]["reconstruction_conditions"]["equivalence_level"], "L3_CANDIDATE")

    def test_output_is_deterministic_and_self_hashed(self) -> None:
        intent = {"requested_result": "candidate", "parameters": {"alpha": 1}}
        first = build_field_application_packet("ASSOCIATION", intent)
        second = build_field_application_packet("ASSOCIATION", copy.deepcopy(intent))
        self.assertEqual(first, second)
        expected = dict(first)
        supplied_hash = expected.pop("packet_sha256")
        self.assertEqual(supplied_hash, canonical_sha256(expected))

    def test_unknown_and_unsafe_scenarios_block(self) -> None:
        for scenario, reason in (
            ("UNKNOWN", "SCENARIO_NOT_REGISTERED"),
            ("../PROPERTY", "SCENARIO_TOKEN_INVALID"),
        ):
            with self.subTest(scenario=scenario):
                with self.assertRaises(FieldApplicationError) as caught:
                    build_field_application_packet(scenario, {"requested_result": "candidate"})
                self.assertEqual(caught.exception.reason_code, reason)

    def test_nested_authority_escalation_blocks(self) -> None:
        with self.assertRaises(FieldApplicationError) as caught:
            build_field_application_packet(
                "GENERIC",
                {"requested_result": "candidate", "nested": {"d8_decision": "ALLOW"}},
            )
        self.assertEqual(caught.exception.reason_code, "AUTHORITY_ESCALATION_BLOCKED")
        self.assertEqual(caught.exception.path, "$.nested.d8_decision")

    def test_sensitive_input_blocks_without_value_echo(self) -> None:
        sensitive_value = "fixture-sensitive-value-not-for-output"
        with self.assertRaises(FieldApplicationError) as caught:
            build_field_application_packet(
                "PROPERTY",
                {"requested_result": "candidate", "nested": {"raw_token": sensitive_value}},
            )
        self.assertEqual(caught.exception.reason_code, "SENSITIVE_INTENT_BLOCKED")
        self.assertNotIn(sensitive_value, str(caught.exception))

    def test_registry_mismatch_blocks(self) -> None:
        route_table = json.loads(SCENARIO_ROUTE_TABLE_PATH.read_text(encoding="utf-8"))
        registry = json.loads(CAPABILITY_REGISTRY_PATH.read_text(encoding="utf-8"))
        route_table["routes"]["GENERIC"]["capability_ref"] = "CAPABILITY_NOT_REGISTERED"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            route_path = root / "routes.json"
            registry_path = root / "registry.json"
            route_path.write_text(json.dumps(route_table), encoding="utf-8")
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(FieldApplicationError) as caught:
                build_field_application_packet(
                    "GENERIC",
                    {"requested_result": "candidate"},
                    route_table_path=route_path,
                    capability_registry_path=registry_path,
                )
        self.assertEqual(
            caught.exception.reason_code,
            "SCENARIO_CAPABILITY_REGISTRY_MISMATCH",
        )

    def test_non_json_and_non_object_intent_block(self) -> None:
        for value, reason in (
            ("not-json", "INTENT_JSON_INVALID"),
            ("[]", "INTENT_OBJECT_REQUIRED"),
        ):
            with self.subTest(value=value):
                with self.assertRaises(FieldApplicationError) as caught:
                    parse_intent(value)
                self.assertEqual(caught.exception.reason_code, reason)

    def test_every_execution_side_effect_is_false(self) -> None:
        packet = build_field_application_packet("CAFE_POS", {"requested_result": "candidate"})
        self.assertTrue(packet["D5"]["side_effects"])
        self.assertFalse(any(packet["D5"]["side_effects"].values()))
        self.assertFalse(packet["D8"]["cloud_model_auto_enabled"])

    def test_llm_is_device_only_and_server_model_material_is_blocked(self) -> None:
        packet = build_field_application_packet("GENERIC", {"requested_result": "candidate"})
        policy = packet["D5"]["llm_execution"]
        self.assertEqual(policy["llm_inference_location"], "USER_DEVICE_ONLY")
        self.assertEqual(policy["server_llm_execution"], "BLOCK")
        self.assertEqual(policy["raw_prompt_upload"], "BLOCK")
        self.assertEqual(packet["D8"]["server_model_authority"], "NONE")
        for key in ("raw_prompt", "model_context", "model_weights"):
            with self.subTest(key=key):
                with self.assertRaises(FieldApplicationError) as caught:
                    build_field_application_packet(
                        "GENERIC",
                        {"requested_result": "candidate", key: "must-stay-on-device"},
                    )
                self.assertEqual(caught.exception.reason_code, "SENSITIVE_INTENT_BLOCKED")


if __name__ == "__main__":
    unittest.main()
