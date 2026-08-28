from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/field/w7tp_xiaoj_adi_moving_v_adaptive_integration_v3.schema.json"
CONFIG_PATH = ROOT / "configs/total_field/w7tp_xiaoj_adi_moving_v_adaptive_integration_v3.candidate.json"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: dict[str, Any]) -> str:
    body = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


class AdaptiveIntegrationV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.config = load_json(CONFIG_PATH)
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def test_schema_and_candidate_are_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)
        self.validator.validate(self.config)

    def test_lineage_is_append_only_and_hash_bound(self) -> None:
        expected = {
            "W7TP_MOVING_V_PRELOAD_CLEANUP_V1_CANDIDATE",
            "W7TP_MOVING_V_ROUTE_CLEANUP_V2_CANDIDATE",
            "W7TP_XIAOJ_ADI_MOVING_V_SHADOW_V1_CANDIDATE",
        }
        self.assertEqual(
            {entry["contract_id"] for entry in self.config["lineage"]},
            expected,
        )
        for entry in self.config["lineage"]:
            self.assertFalse(entry["mutation_allowed"])
            self.assertEqual(sha256_file(ROOT / entry["path"]), entry["sha256"])

    def test_evidence_files_match_declared_hashes(self) -> None:
        anchors = self.config["evidence_anchors"]
        for key, anchor in anchors.items():
            path = ROOT / anchor["path"]
            self.assertTrue(path.is_file(), key)
            self.assertEqual(sha256_file(path), anchor["sha256"], key)

    def test_shadow_report_is_internal_consistent_and_no_effect(self) -> None:
        anchor = self.config["evidence_anchors"]["shadow_observation"]
        report = load_json(ROOT / anchor["path"])
        shadow_config = load_json(ROOT / report["config_path"])
        self.assertEqual(
            canonical_sha256(shadow_config),
            anchor["config_canonical_sha256"],
        )
        self.assertEqual(report["config_sha256"], anchor["config_canonical_sha256"])
        self.assertEqual(report["summary"]["sample_count"], anchor["sample_count"])
        self.assertEqual(
            report["summary"]["endpoint_failure_count"],
            anchor["endpoint_failure_count"],
        )
        self.assertEqual(
            report["summary"]["active_model_count_max"],
            anchor["active_model_count_max"],
        )
        self.assertEqual(report["recommendation"]["reason"], anchor["reason"])
        self.assertFalse(report["recommendation"]["applies_change"])
        self.assertTrue(all(value is False for value in report["effects"].values()))

    def test_topology_is_complete_and_ordered(self) -> None:
        ids = [component["component_id"] for component in self.config["components"]]
        self.assertEqual(ids, self.config["ordered_data_flow"])
        self.assertEqual(len(ids), len(set(ids)))
        for required in (
            "XIAOJ_INTENT_FIELD",
            "GOVERNED_INTENT_CACHE",
            "NATIVE_ADI_DELTA_F",
            "MOVING_V_CLASSIFIER",
            "GTP_RECONSTRUCTION",
            "OLLAMA_MODEL_RESIDENCY",
            "SHADOW_ADAPTATION_LOOP",
            "TOTAL_FIELD_AUTHORITY_GATE",
        ):
            self.assertIn(required, ids)

    def test_unproven_adi_gtp_and_authority_stay_hold(self) -> None:
        states = {
            component["component_id"]: component["state"]
            for component in self.config["components"]
        }
        self.assertEqual(
            states["NATIVE_ADI_DELTA_F"],
            "SOURCE_CANDIDATE_PRESENT_BINDING_REQUIRED",
        )
        self.assertEqual(states["GTP_RECONSTRUCTION"], "ADAPTER_REQUIRED_HOLD")
        self.assertEqual(states["TOTAL_FIELD_AUTHORITY_GATE"], "INACTIVE_HOLD")
        self.assertFalse(
            self.config["evidence_anchors"]["native_adi_core_candidate"][
                "runtime_binding_proven"
            ]
        )
        self.assertTrue(
            all(gate["state"] == "HOLD" for gate in self.config["readiness_gates"])
        )

    def test_three_stage_lifecycle_never_grants_live_effect(self) -> None:
        stages = self.config["temporal_lifecycle"]
        self.assertEqual(
            [stage["stage"] for stage in stages],
            [
                "PREDICTED_NOT_GENERATED",
                "GENERATION_SCHEDULED_OR_RUNNING",
                "GENERATION_COMPLETED",
            ],
        )
        self.assertTrue(all(stage["live_effect"] == "DENIED" for stage in stages))

    def test_adaptive_loop_stops_before_review_or_effect(self) -> None:
        loop = self.config["adaptive_loop"]
        self.assertEqual(
            loop["ordered_phases"],
            [
                "OBSERVE",
                "NORMALIZE",
                "CLASSIFY",
                "RECOMMEND",
                "REVIEW_GATE",
                "CANARY_GATE",
                "COMMIT_RECEIPT",
            ],
        )
        self.assertEqual(loop["current_phase_ceiling"], "RECOMMEND")
        self.assertFalse(loop["applies_change"])

    def test_authority_and_all_material_effects_are_false(self) -> None:
        authority = self.config["authority"]
        boolean_values = [
            value for key, value in authority.items() if key != "decision_authority"
        ]
        self.assertTrue(boolean_values)
        self.assertTrue(all(value is False for value in boolean_values))
        self.assertEqual(self.config["current_decision"]["live_effect_count"], 0)
        self.assertEqual(self.config["current_decision"]["state"], "HOLD_SHADOW_ONLY")

    def test_all_network_sources_are_loopback_and_read_boundaries_hold(self) -> None:
        boundaries = self.config["source_boundaries"]
        for url in boundaries["loopback_urls"]:
            parsed = urlsplit(url)
            self.assertEqual(parsed.scheme, "http")
            self.assertEqual(parsed.hostname, "127.0.0.1")
        self.assertFalse(boundaries["model_generation_request_allowed"])
        self.assertFalse(boundaries["non_loopback_network_allowed"])
        forbidden = set(boundaries["forbidden_reads"])
        self.assertIn("MEMBER_PLAINTEXT", forbidden)
        self.assertIn("CREDENTIAL_OR_TOKEN", forbidden)
        self.assertIn("SECRET_FILE_CONTENT", forbidden)

    def test_safety_and_objective_precedence_are_explicit(self) -> None:
        invariants = set(self.config["safety_invariants"])
        self.assertIn("V_INTERIOR_AND_CURRENT_ARE_ALWAYS_PROTECTED", invariants)
        self.assertIn("CANONICAL_SOURCE_IS_NEVER_DELETED", invariants)
        objectives = self.config["ordered_optimization_objectives"]
        self.assertEqual(objectives[0], "DATA_SAFETY")
        self.assertEqual(objectives[-1], "MEMORY_AND_TRANSFER_SAVINGS")


if __name__ == "__main__":
    unittest.main()
