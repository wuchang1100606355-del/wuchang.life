from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from jsonschema import Draft202012Validator

from tools.total_field.w7tp_intent_field_suite.canonical_hash import canonical_sha256
from tools.total_field import w7tp_review_candidate_v2_3_adapter as adapter


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_MAP = ROOT / adapter.IDENTITY_MAP_REF
CANONICAL_SCHEMA = ROOT / "schemas/w7tp_8d_multipurpose_packet_canonical_v2.schema.json"
CANONICAL_DOC = (
    ROOT
    / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)
PACKAGE_MANIFEST_SCHEMA = (
    ROOT / "schemas/field/variable_cognition_package_manifest.schema.json"
)
NORMALIZATION_RULES = [
    "PACKET_CANONICAL_ID_TO_CANONICAL_ID_EXACT",
    "SOURCE_2_3_RETAINED_AS_ADAPTER_RECEIPT",
    "D1_TO_D5_AS_CANONICAL_HASH_PROFILE_REFS",
    "SOURCE_STATE_AND_COORDINATE_PROFILE_EXACT_WRAP",
    "SOURCE_D6_PROTOCOL_EXACT",
    "SOURCE_D6_REMAINDER_AS_HASH_BOUND_REFERENCE",
    "LIVE_DB_WRITE_TO_DB_WRITE_EXACT_ALIAS",
    "SOURCE_TIME_WINDOW_TO_POSITIVE_INTEGER_TTL",
    "SOURCE_NONCE_TO_ENVELOPE_NONCE_EXACT",
    "CANONICAL_TECHNOLOGY_FLAGS_FROM_SCHEMA_CONST",
    "CANONICAL_PACKET_HASH_EXCLUDES_BOTH_ENVELOPE_SHA256_FIELDS",
    "CANDIDATE_REVIEW_DECISION_ALWAYS_HOLD",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ReviewCandidateV23AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        self.mapping = load_json(IDENTITY_MAP)
        self._copy_canonical_pins()
        self._write_manifests()
        state = adapter.inspect_skill_manifest_bindings(
            self.mapping,
            workspace_root=self.workspace,
        )
        self.assertEqual("PASS_EXACT_FIVE_MANIFESTS_HASH_BOUND", state["state"])
        self.manifest_state = state
        self.source_packet = self._source_packet()
        self.source_bytes = json.dumps(
            self.source_packet,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.request = self._adapter_request()
        self.now = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _copy_canonical_pins(self) -> None:
        for source, relative in (
            (
                CANONICAL_SCHEMA,
                "schemas/w7tp_8d_multipurpose_packet_canonical_v2.schema.json",
            ),
            (
                CANONICAL_DOC,
                "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md",
            ),
            (
                PACKAGE_MANIFEST_SCHEMA,
                "schemas/field/variable_cognition_package_manifest.schema.json",
            ),
        ):
            destination = self.workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

    @staticmethod
    def _manifest(target_skill_id: str, package_id: str) -> dict:
        return {
            "package_id": package_id,
            "name": target_skill_id,
            "version": "1.0.0",
            "sha256": hashlib.sha256(f"payload:{package_id}".encode()).hexdigest(),
            "source_ref": f"source-ref:{target_skill_id}",
            "capability_scope": [target_skill_id],
            "requested_permissions": ["read_package_state", "emit_candidate"],
            "allowed_nodes": ["taiji01"],
            "compatibility": {
                "cpu_baseline_required": True,
                "required_dependencies": [],
                "conflicts": [],
            },
            "reconstruction_conditions": {"mode": "L3_CANDIDATE"},
            "packet_carried_protocol": {
                "kind": "W7TP_8D_STATE_FIELD_PACKET",
                "protocol_native": True,
                "references": True,
                "lookup": True,
                "reconstruction_contract": True,
            },
            "packet_carried_validation": {
                "total_field_verification": True,
                "before_state_sha256": True,
                "after_state_sha256": True,
            },
            "evidence_refs": [f"fixture-evidence:{target_skill_id}"],
            "risk_status": "CLEAR",
            "installed_by": None,
            "founder_command_ref": None,
            "lifecycle_state": "CANDIDATE",
            "created_at": "2026-07-22T00:00:00Z",
            "updated_at": "2026-07-22T00:00:00Z",
        }

    def _write_manifests(self) -> None:
        for target_skill_id, binding in self.mapping["bindings"].items():
            path = self.workspace / binding["manifest_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    self._manifest(target_skill_id, binding["package_id"]),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )

    def _source_packet(self) -> dict:
        manifest_hashes = {
            source_key: item["manifest_file_sha256"]
            for source_key, item in self.manifest_state["bindings"].items()
        }
        return {
            "packet_id": "W7TP_REVIEW_REQ_20260722T000000Z",
            "packet_canonical_id": adapter.CANONICAL_ID,
            "schema_version": "2.3",
            "d1_intent": {
                "intent": "SUBMIT_FOR_ISOLATED_TOTAL_FIELD_REVIEW",
                "product_outcome": "Submit five hash-bound skill candidates for isolated review.",
            },
            "d2_state": {
                "state_profile": "LIFECYCLE_TRANSITION",
                "baseline": ["CANDIDATE_FOR_TOTAL_FIELD_REVIEW"],
                "proposed": ["ALLOW_ISOLATED_CANARY_ONLY"],
            },
            "d3_coordinate": {
                "coordinate_profile": "SOVEREIGN_NODE_DEPLOYMENT",
                "target_node": "taiji01",
                "target_workspace": "/home/taiji_admin/Taiji_Hub",
                "receiver": "TOTAL_FIELD_RECEIVE_CANDIDATE_AND_DECISION_GATEWAY",
            },
            "d4_evidence": {
                "evidence_contract": "EXACT_HASH_BOUND_MANIFEST_SUBMISSION",
                "skill_manifest_hashes": manifest_hashes,
            },
            "d5_execution": {
                "action": "AUTHORIZE_ISOLATED_CANARY_REVIEW",
                "forbidden_effects": [
                    "ACTIVE",
                    "LIVE_DB_WRITE",
                    "DEPLOY",
                    "ROUTER_WRITE",
                ],
            },
            "d6_transmission": {
                "protocol": "W7TP_GOVERNANCE_PACKET",
                "routing": {
                    "source": "taiji01_local",
                    "destination": "total_field_inbox",
                },
                "reconstruction": {"mode": "EXACT_BYTES"},
                "verification": {"procedure": "validate_skill_manifest.py"},
            },
            "d7_risk": {
                "max_candidates": 5,
                "duplicate_action": "HOLD_REPLAY_DETECTED",
                "nonce": "nonce_20260722T000000Z_8f7d",
                "issued_at": "2026-07-22T00:00:00Z",
                "expires_at": "2026-07-23T00:00:00Z",
                "replay_window": "86400",
            },
            "d8_envelope": {
                "auth_algorithm": "FOUNDER_DIGITAL_SIGNATURE_PROFILE",
                "domain_separator": "W7TP_TOTAL_FIELD_REVIEW_V1",
                "signature_scope": "FULL_PACKET_EXCLUDING_D8_SIGNATURE",
                "key_registry_id": "FOUNDER_TRUST_ROOT_REGISTRY",
                "signature": "PENDING_FOUNDER_LOCAL_SEAL",
            },
        }

    def _adapter_request(self) -> dict:
        manifest_bindings = {
            source_key: {
                "manifest_path": item["manifest_path"],
                "manifest_file_sha256": item["manifest_file_sha256"],
                "package_id": item["package_id"],
            }
            for source_key, item in self.manifest_state["bindings"].items()
        }
        request = {
            "adapter_contract_version": "W7TP-REVIEW-CANDIDATE-2.3-TO-CANONICAL-V2/1.0",
            "source_packet": deepcopy(self.source_packet),
            "source_packet_raw_sha256": hashlib.sha256(self.source_bytes).hexdigest(),
            "source_packet_canonical_sha256": canonical_sha256(self.source_packet),
            "identity_map_ref": adapter.IDENTITY_MAP_REF,
            "identity_map_self_sha256": self.mapping["binding_matrix_self_sha256"],
            "manifest_bindings": manifest_bindings,
            "canonical_requirements": {
                "domain": "TOTAL_FIELD_DECISION",
                "lookup_profile_ref": "profile:five-skill-review:lookup:v1",
                "generation_profile_ref": "profile:five-skill-review:generation:v1",
                "reconstruction_profile_ref": "profile:five-skill-review:reconstruction:v1",
                "verification_profile_ref": "profile:five-skill-review:verification:v1",
                "d6": {
                    "routing": "route:taiji01-local-to-total-field-inbox:v1",
                    "segmentation": "single-hash-bound-review-candidate",
                    "merge_conditions": ["all-five-manifest-hashes-match"],
                    "references": ["contract:review-candidate-v2.3:v1"],
                    "generation_rules": ["reconstruct-only-explicit-sidecar-bindings"],
                    "reconstruction_contract": "contract:l3-five-skill-review:v1",
                    "verification_contract": "contract:five-skill-hash-review:v1",
                    "residual": [],
                    "refill_policy": "hold-on-missing-explicit-binding",
                    "on_demand_materialization": False,
                },
                "generation": {
                    "generation_rules": ["reconstruct-only-explicit-sidecar-bindings"],
                    "reconstruction_contract": "contract:l3-five-skill-review:v1",
                    "verification_contract": "contract:five-skill-hash-review:v1",
                    "target_equivalence": "L3_CANDIDATE_NO_AUTHORITY",
                },
                "transmission": {
                    "routing": "route:taiji01-local-to-total-field-inbox:v1",
                    "path": ["taiji01_local", "total_field_inbox"],
                    "segment": 0,
                    "order": 0,
                    "references": ["contract:review-candidate-v2.3:v1"],
                    "merge_conditions": ["all-five-manifest-hashes-match"],
                },
                "composition_mode": "MERGED_AS_SELF_CONTAINED_PACKET",
                "reconstruction": {
                    "zero_prior_content_receiver": True,
                    "materialization": "LIMITED_RECONSTRUCTION",
                    "economic_mode": "W7TP_GENERATIVE",
                },
                "verification": {
                    "level": "L3_CANDIDATE",
                    "method_ref": "tools.total_field.w7tp_review_candidate_v2_3_adapter.inspect_skill_manifest_bindings",
                    "contract_ref": "contract:five-skill-hash-review:v1",
                },
                "envelope": {
                    "authority_ref": "FOUNDER_TRUST_ROOT_REGISTRY",
                    "version": "2.3-to-2.0.0-candidate/1.0",
                    "verifier_ref": "tools.total_field.w7tp_review_candidate_v2_3_adapter.verify_canonical_packet_hash",
                    "seal_policy": "PENDING_FOUNDER_LOCAL_SEAL_NO_AUTHORITY",
                },
            },
            "normalization_rules": list(NORMALIZATION_RULES),
        }
        return adapter.with_request_self_hash(request)

    def adapt(self, **kwargs) -> dict:
        return adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            self.request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
            **kwargs,
        )

    def test_exact_five_skill_mapping_and_hashes(self) -> None:
        validated = adapter.validate_identity_map(
            self.mapping,
            workspace_root=self.workspace,
        )
        self.assertEqual(5, len(validated["bindings"]))
        self.assertEqual(5, len(self.manifest_state["bindings"]))
        self.assertRegex(self.manifest_state["manifest_aggregate_sha256"], r"^[0-9a-f]{64}$")
        for target_skill_id, binding in validated["bindings"].items():
            with self.subTest(target_skill_id=target_skill_id):
                unsigned = dict(binding)
                supplied = unsigned.pop("identity_binding_sha256")
                self.assertEqual(canonical_sha256(unsigned), supplied)
                measured = self.manifest_state["bindings"][binding["source_key"]]
                self.assertEqual(binding["package_id"], measured["package_id"])
                self.assertRegex(measured["manifest_file_sha256"], r"^[0-9a-f]{64}$")
                self.assertFalse(measured["package_payload_hash_verified"])

    def test_missing_manifests_hold_with_null_hashes(self) -> None:
        empty = Path(tempfile.mkdtemp(dir=self.temporary.name))
        for source, relative in (
            (CANONICAL_SCHEMA, self.mapping["canonical_target"]["machine_schema_ref"]),
            (CANONICAL_DOC, self.mapping["canonical_target"]["canonical_doc_ref"]),
            (PACKAGE_MANIFEST_SCHEMA, self.mapping["package_manifest_schema"]["ref"]),
        ):
            destination = empty / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        result = adapter.inspect_skill_manifest_bindings(
            self.mapping,
            workspace_root=empty,
        )
        self.assertEqual("HOLD_MISSING_SOURCE_MANIFEST", result["state"])
        self.assertEqual(0, result["present_count"])
        self.assertIsNone(result["manifest_aggregate_sha256"])
        self.assertTrue(
            all(item["manifest_file_sha256"] is None for item in result["bindings"].values())
        )

    def test_adapter_builds_schema_valid_l3_candidate_without_authority(self) -> None:
        result = self.adapt()
        self.assertEqual("PASS_ADAPTER_CONTRACT_RECONSTRUCTED_CANDIDATE", result["state"])
        self.assertEqual("HOLD", result["decision"])
        self.assertFalse(result["authority_granted"])
        self.assertTrue(all(value is False for value in result["side_effects"].values()))
        packet = result["canonical_packet"]
        schema = load_json(CANONICAL_SCHEMA)
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(packet)))
        self.assertEqual(12, len(packet["dimensions"]["D6_GENERATIVE_TRANSMISSION"]))
        self.assertEqual(8, len(packet["envelope"]))
        self.assertEqual(packet["envelope"], packet["dimensions"]["D8_ENVELOPE"])
        self.assertEqual(packet["risk"], packet["dimensions"]["D7_RISK"])
        self.assertEqual("L3_CANDIDATE", packet["verification"]["level"])
        self.assertEqual("W7TP_GENERATIVE", packet["reconstruction"]["economic_mode"])
        self.assertTrue(adapter.verify_canonical_packet_hash(packet))
        request_ref = "w7tp-v2.3-adapter-request:sha256:" + self.request[
            "request_self_sha256"
        ]
        self.assertEqual(self.request["request_self_sha256"], result["request_self_sha256"])
        self.assertIn(request_ref, packet["dimensions"]["D6_GENERATIVE_TRANSMISSION"]["references"])
        self.assertIn(request_ref, packet["transmission_packet"]["reference"])
        self.assertEqual(self.source_packet, result["source_packet"])
        self.assertEqual(result["source_leaf_count"], len(result["projection_ledger"]))
        self.assertEqual([], result["unclassified_source_paths"])

    def test_adapter_is_deterministic_and_does_not_mutate_inputs(self) -> None:
        source_before = bytes(self.source_bytes)
        request_before = deepcopy(self.request)
        mapping_before = deepcopy(self.mapping)
        first = self.adapt()
        second = self.adapt()
        self.assertEqual(first, second)
        self.assertEqual(source_before, self.source_bytes)
        self.assertEqual(request_before, self.request)
        self.assertEqual(mapping_before, self.mapping)

        reordered = deepcopy(self.mapping)
        reordered["bindings"] = dict(reversed(list(reordered["bindings"].items())))
        validated = adapter.validate_identity_map(reordered, workspace_root=self.workspace)
        self.assertEqual(
            self.mapping["binding_matrix_self_sha256"],
            validated["binding_matrix_self_sha256"],
        )

    def test_source_raw_byte_drift_holds_before_projection(self) -> None:
        result = adapter.adapt_review_candidate_v2_3(
            self.source_bytes + b"\n",
            self.request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
        )
        self.assertEqual("HOLD_SOURCE_PACKET_RAW_HASH_MISMATCH", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_manifest_byte_drift_holds_before_projection(self) -> None:
        first = next(iter(self.mapping["bindings"].values()))
        path = self.workspace / first["manifest_path"]
        path.write_bytes(path.read_bytes() + b" ")
        result = self.adapt()
        self.assertEqual("HOLD_MANIFEST_FILE_HASH_MISMATCH", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_identity_map_hash_drift_holds(self) -> None:
        drifted = deepcopy(self.mapping)
        drifted["binding_matrix_self_sha256"] = "f" * 64
        result = adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            self.request,
            workspace_root=self.workspace,
            identity_map=drifted,
            now=self.now,
        )
        self.assertEqual("HOLD_IDENTITY_MAP_HASH_MISMATCH", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_incomplete_d6_sidecar_is_schema_hold(self) -> None:
        request = deepcopy(self.request)
        request["canonical_requirements"]["d6"].pop("segmentation")
        request = adapter.with_request_self_hash(request)
        result = adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
        )
        self.assertEqual("HOLD_ADAPTER_REQUEST_SCHEMA_INVALID", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_contradictory_sidecar_contracts_hold(self) -> None:
        request = deepcopy(self.request)
        request["canonical_requirements"]["generation"][
            "verification_contract"
        ] = "contract:contradictory:v1"
        request = adapter.with_request_self_hash(request)
        result = adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
        )
        self.assertEqual("HOLD_CANONICAL_BINDING_INCONSISTENT", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_authority_route_and_verifier_sidecar_injection_holds(self) -> None:
        mutations = (
            ("authority", ("envelope", "authority_ref"), "authority:FOUNDER_ALLOW_ACTIVE"),
            ("route", ("d6", "routing"), "route:unrelated"),
            ("verifier", ("verification", "method_ref"), "validate_skill_manifest.py"),
        )
        for label, path, value in mutations:
            with self.subTest(label=label):
                request = deepcopy(self.request)
                request["canonical_requirements"][path[0]][path[1]] = value
                request = adapter.with_request_self_hash(request)
                result = adapter.adapt_review_candidate_v2_3(
                    self.source_bytes,
                    request,
                    workspace_root=self.workspace,
                    identity_map=self.mapping,
                    now=self.now,
                )
                self.assertEqual("HOLD_ADAPTER_REQUEST_SCHEMA_INVALID", result["reason_code"])
                self.assertIsNone(result["canonical_packet"])

    def test_placeholder_hash_is_rejected(self) -> None:
        request = deepcopy(self.request)
        request["source_packet"]["d4_evidence"]["skill_manifest_hashes"][
            "build-intent-field"
        ] = "PENDING_TOTAL_FIELD_SEAL_V1"
        request = adapter.with_request_self_hash(request)
        result = adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
        )
        self.assertEqual("HOLD_ADAPTER_REQUEST_SCHEMA_INVALID", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_authority_injection_blocks(self) -> None:
        request = deepcopy(self.request)
        request["source_packet"]["d1_intent"]["final_decision"] = "ALLOW"
        result = adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
        )
        self.assertEqual("BLOCK", result["decision"])
        self.assertEqual("BLOCK_AUTHORITY_INJECTION", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_replay_and_time_window_hold(self) -> None:
        replay = self.adapt(seen_nonces={self.source_packet["d7_risk"]["nonce"]})
        self.assertEqual("HOLD_REPLAY_DETECTED", replay["reason_code"])
        expired = adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            self.request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=datetime(2026, 7, 23, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual("HOLD_PACKET_EXPIRED", expired["reason_code"])

    def test_projection_ledger_only_maps_time_fields_to_ttl(self) -> None:
        result = self.adapt()
        ledger = {item["source_path"]: item for item in result["projection_ledger"]}
        for path in (
            "/d7_risk/issued_at",
            "/d7_risk/expires_at",
            "/d7_risk/replay_window",
        ):
            with self.subTest(path=path):
                self.assertEqual("NORMALIZED_BY_EXACT_RULE", ledger[path]["classification"])
                self.assertIn("/envelope/ttl_seconds", ledger[path]["target_paths"])
        for path in ("/d7_risk/max_candidates", "/d7_risk/duplicate_action"):
            with self.subTest(path=path):
                self.assertEqual("EVIDENCE_ONLY", ledger[path]["classification"])
                self.assertNotIn("/envelope/ttl_seconds", ledger[path]["target_paths"])

    def test_package_manifest_schema_hash_pin_drift_holds(self) -> None:
        schema_path = self.workspace / self.mapping["package_manifest_schema"]["ref"]
        schema_path.write_bytes(schema_path.read_bytes() + b"\n")
        result = self.adapt()
        self.assertEqual("HOLD_PACKAGE_MANIFEST_SCHEMA_HASH_MISMATCH", result["reason_code"])
        self.assertIsNone(result["canonical_packet"])

    def test_invalid_boundary_types_fail_closed(self) -> None:
        invalid_source = adapter.adapt_review_candidate_v2_3(
            "not-bytes",
            self.request,
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
        )
        self.assertEqual("HOLD_SOURCE_PACKET_BYTES_REQUIRED", invalid_source["reason_code"])
        self.assertIsNone(invalid_source["source_packet_raw_sha256"])
        invalid_request = adapter.adapt_review_candidate_v2_3(
            self.source_bytes,
            ["not", "an", "object"],
            workspace_root=self.workspace,
            identity_map=self.mapping,
            now=self.now,
        )
        self.assertEqual("HOLD_ADAPTER_REQUEST_OBJECT_REQUIRED", invalid_request["reason_code"])
        self.assertIsNone(invalid_request["canonical_packet"])

    def test_traditional_or_non_candidate_mode_is_rejected(self) -> None:
        for field, value in (
            ("economic_mode", "DIRECT_TRANSFER"),
            ("verification_level", "L1_FULL"),
        ):
            with self.subTest(field=field):
                request = deepcopy(self.request)
                if field == "economic_mode":
                    request["canonical_requirements"]["reconstruction"][field] = value
                else:
                    request["canonical_requirements"]["verification"]["level"] = value
                request = adapter.with_request_self_hash(request)
                result = adapter.adapt_review_candidate_v2_3(
                    self.source_bytes,
                    request,
                    workspace_root=self.workspace,
                    identity_map=self.mapping,
                    now=self.now,
                )
                self.assertEqual("HOLD_ADAPTER_REQUEST_SCHEMA_INVALID", result["reason_code"])
                self.assertIsNone(result["canonical_packet"])

    def test_adapter_has_no_network_process_or_database_imports(self) -> None:
        tree = ast.parse(Path(adapter.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(
            imported.isdisjoint(
                {"socket", "requests", "httpx", "subprocess", "sqlite3", "odoo"}
            )
        )


if __name__ == "__main__":
    unittest.main()
