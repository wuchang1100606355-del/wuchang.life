from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_intent_field_candidate as producer
import intent_field_construct as structural
import verify_intent_field_construction as verifier
from test_intent_field_construct import digest, valid_spec


NOW = dt.datetime(2026, 8, 20, 4, 5, 0, tzinfo=dt.timezone.utc)


def write_bytes(root: Path, ref: str, data: bytes) -> str:
    path = root / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def write_json(root: Path, ref: str, value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    return write_bytes(root, ref, data)


def canonical_hash(value: object) -> str:
    return structural.sha256_bytes(structural.canonical_bytes(value))


def complete_spec() -> dict:
    spec = valid_spec()
    user = spec["user_explicit"][0]
    spec["allowed_effects"][0]["immutable_source_chain"] = [
        {
            "id": user["id"],
            "statement_sha256": structural.sha256_text(user["statement"]),
            "source_ref": user["source"]["ref"],
        }
    ]
    spec["provenance_catalog"] = [
        {
            "class": source_class,
            "ref": f"synthetic://provenance/{source_class}",
            "sha256": digest(f"provenance-{source_class}"),
            "grants_authority": False,
        }
        for source_class in sorted(producer.PROVENANCE_CLASSES)
    ]
    spec["product_personas"] = {
        name: {"status": "PASS", "evidence_refs": [f"synthetic://persona/{name}"]}
        for name in producer.PERSONAS
    }
    spec["product_matrix"] = {
        name: {"status": "PASS", "evidence_refs": [f"synthetic://product/{name}"]}
        for name in producer.PRODUCT_MATRIX
    }
    spec["effect_policy"] = {
        "scope": "NEW_RUN_DIRECTORY_CANDIDATE_FILES_ONLY",
        "no_existing_file_overwrite": True,
        "no_external_side_effects": True,
    }
    return spec


def complete_bundle(root: Path, spec: dict) -> dict:
    relational_artifact = {
        "schema_id": "IFGC_RELATIONAL_EVIDENCE_V1",
        "input_revision": spec["revision"],
        "evidence_class": "FIELD_EVIDENCE",
        "runner_verdict": "UNVERIFIED",
        "mainline_relation": spec["mainline_relation"],
        "continuation_distance": spec["continuation_distance"],
        "supply_demand_fit": spec["supply_demand_fit"],
    }
    relational_ref = spec["relational_evidence"]["artifact_ref"]
    relational_sha = write_json(root, relational_ref, relational_artifact)
    spec["relational_evidence"]["artifact_sha256"] = relational_sha
    stage_artifact = {
        "schema_id": "IFGC_RELATIONAL_STAGE_RECEIPT_V1",
        "input_revision": spec["revision"],
        "evidence_class": "FIELD_EVIDENCE",
        "artifact_ref": relational_ref,
        "artifact_sha256": relational_sha,
        "state": "STAGED",
        "runner_verdict": "UNVERIFIED",
        "grants_authority": False,
    }
    stage_ref = spec["relational_evidence"]["stage_receipt_ref"]
    spec["relational_evidence"]["stage_receipt_sha256"] = write_json(
        root, stage_ref, stage_artifact
    )
    candidate = producer.build_candidate(spec)
    candidate_sha = canonical_hash(candidate)
    journey_receipts = []
    for journey in spec["user_journeys"]:
        trace = {
            "journey_id": journey["id"],
            "role": journey["role"],
            "scenario": journey["scenario"],
            "surface": journey["surface"],
            "input_revision": spec["revision"],
            "actual_entrypoint": f"entrypoint://{journey['id']}",
            "runner": "synthetic-journey-runner",
            "runner_version": "1.0",
            "runner_verdict": "UNVERIFIED",
            "executed": True,
            "result": "PASS",
            "steps": [
                {"id": f"step-{index + 1}", "executed": True, "status": "PASS"}
                for index, _ in enumerate(journey["steps"])
            ],
            "feedback_verified": True,
            "error_recovery_tested": True,
            "accessibility_tested": True,
            "authorization_boundary_tested": True,
            "exit_tested": True,
            "partial_effects": False,
        }
        ref = f"evidence/journey-{journey['id']}.json"
        artifact_sha = write_json(root, ref, trace)
        journey_receipts.append(
            {
                "journey_id": journey["id"],
                "role": journey["role"],
                "scenario": journey["scenario"],
                "surface": journey["surface"],
                "input_revision": spec["revision"],
                "actual_entrypoint": trace["actual_entrypoint"],
                "runner": trace["runner"],
                "runner_version": trace["runner_version"],
                "runner_verdict": "UNVERIFIED",
                "executed": True,
                "result": "PASS",
                "artifact_ref": ref,
                "artifact_sha256": artifact_sha,
            }
        )

    pre_fix_sha = digest("pre-fix-candidate")
    previous = pre_fix_sha
    stage_names = list(structural.REDTEAM_CHECKS)
    redteam_receipts = {}
    for index, stage in enumerate(stage_names):
        has_fix = index == 0
        output_sha = candidate_sha
        artifact = {
            "stage": stage,
            "round": 1,
            "input_sha256": previous,
            "output_sha256": output_sha,
            "executed": True,
            "result": "PASS",
        }
        ref = f"evidence/redteam-{stage}.json"
        artifact_sha = write_json(root, ref, artifact)
        redteam_receipts[stage] = {
            "rounds": [
                {
                    "round": 1,
                    "input_sha256": previous,
                    "output_sha256": output_sha,
                    "issues_found": 1 if has_fix else 0,
                    "issues_fixed": 1 if has_fix else 0,
                    "fix_applied": has_fix,
                    "rerun_executed": has_fix,
                    "fix_ref": "synthetic://fix/intent" if has_fix else None,
                    "executed": True,
                    "result": "PASS",
                    "runner": "synthetic-redteam-runner",
                    "artifact_ref": ref,
                    "artifact_sha256": artifact_sha,
                }
            ],
            "downstream_revalidated": stage_names[index + 1 :] if has_fix else [],
        }
        previous = output_sha

    runtime_segments = []
    initial_gap_refs = list(spec["runtime_completion_chain"].get("initial_gap_refs", []))
    previous_runtime_output = candidate["producer"]["input_spec_sha256"]
    for index, stage in enumerate(structural.TECHNICAL_CHAIN_STAGES):
        gap_refs = initial_gap_refs if index == 0 and initial_gap_refs else []
        initial_result = "EVIDENCE_GAP" if gap_refs else "PASS"
        runtime_input_sha = previous_runtime_output
        runtime_output_sha = (
            candidate_sha
            if index == len(structural.TECHNICAL_CHAIN_STAGES) - 1
            else canonical_hash(
                {
                    "stage": stage,
                    "sequence": index + 1,
                    "input_sha256": runtime_input_sha,
                    "candidate_packet_sha256": candidate_sha,
                }
            )
        )
        artifact = {
            "stage": stage,
            "sequence": index + 1,
            "executed": True,
            "initial_result": initial_result,
            "gap_refs": gap_refs,
            "input_sha256": runtime_input_sha,
            "output_sha256": runtime_output_sha,
            "runner": "synthetic-runtime-runner",
            "runner_version": "1.0",
            "runner_verdict": "UNVERIFIED",
            "evidence_class": "FIELD_EVIDENCE",
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
        }
        if stage == structural.HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD:
            artifact["eight_d"] = candidate["eight_d"]
        ref = f"evidence/runtime-{index + 1:02d}-{stage}.json"
        artifact_sha = write_json(root, ref, artifact)
        runtime_segments.append(
            {
                "stage": stage,
                "sequence": index + 1,
                "executed": True,
                "initial_result": initial_result,
                "gap_refs": gap_refs,
                "input_sha256": runtime_input_sha,
                "output_sha256": runtime_output_sha,
                "runner": artifact["runner"],
                "runner_version": artifact["runner_version"],
                "runner_verdict": "UNVERIFIED",
                "evidence_class": "FIELD_EVIDENCE",
                "input_revision": spec["revision"],
                "candidate_packet_sha256": candidate_sha,
                "artifact_ref": ref,
                "artifact_sha256": artifact_sha,
            }
        )
        previous_runtime_output = runtime_output_sha

    runtime_fallbacks = []
    for index, fallback in enumerate(spec["runtime_completion_chain"].get("fallbacks", [])):
        target_gap_refs = list(fallback["target_gap_refs"])
        retrieval_output = verifier._fallback_retrieval_output_sha(
            fallback["source_class"],
            target_gap_refs,
            spec["revision"],
            candidate_sha,
        )
        retrieval = {
            "artifact_kind": "FALLBACK_RETRIEVAL",
            "source_class": fallback["source_class"],
            "enabled_after_stage": structural.TECHNICAL_CHAIN_STAGES[-1],
            "target_gap_refs": target_gap_refs,
            "grants_authority": False,
            "executed": False,
            "result": "RETRIEVED",
            "evidence_class": fallback["source_class"],
            "input_sha256": candidate["producer"]["input_spec_sha256"],
            "output_sha256": retrieval_output,
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
        }
        retrieval_ref = f"evidence/fallback-{index + 1}-retrieval.json"
        retrieval_sha = write_json(root, retrieval_ref, retrieval)
        rerun = {
            "artifact_kind": "FALLBACK_RERUN",
            "source_class": fallback["source_class"],
            "enabled_after_stage": structural.TECHNICAL_CHAIN_STAGES[-1],
            "closed_gap_refs": target_gap_refs,
            "executed": True,
            "result": "PASS",
            "evidence_class": "FIELD_EVIDENCE",
            "runner": "synthetic-fallback-rerun",
            "runner_version": "1.0",
            "runner_verdict": "UNVERIFIED",
            "input_sha256": retrieval_sha,
            "output_sha256": candidate_sha,
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
        }
        rerun_ref = f"evidence/fallback-{index + 1}-rerun.json"
        rerun_sha = write_json(root, rerun_ref, rerun)
        runtime_fallbacks.append(
            {
                "source_class": fallback["source_class"],
                "enabled_after_stage": structural.TECHNICAL_CHAIN_STAGES[-1],
                "target_gap_refs": target_gap_refs,
                "grants_authority": False,
                "input_sha256": retrieval_sha,
                "output_sha256": candidate_sha,
                "retrieval_artifact_ref": retrieval_ref,
                "retrieval_artifact_sha256": retrieval_sha,
                "rerun_artifact_ref": rerun_ref,
                "rerun_artifact_sha256": rerun_sha,
            }
        )

    core_function_receipts = {}
    for function_name in structural.CORE_FUNCTIONS:
        subject_sha = verifier.core_function_subject_sha256(candidate, function_name)
        artifact = {
            "function": function_name,
            "executed": True,
            "result": "PASS",
            "evidence_class": "FIELD_EVIDENCE",
            "subject_sha256": subject_sha,
            "runner": "synthetic-core-runner",
            "runner_version": "1.0",
            "runner_verdict": "UNVERIFIED",
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
        }
        ref = f"evidence/core-{function_name}.json"
        artifact_sha = write_json(root, ref, artifact)
        core_function_receipts[function_name] = {
            "function": function_name,
            "executed": True,
            "result": "PASS",
            "evidence_class": "FIELD_EVIDENCE",
            "subject_sha256": subject_sha,
            "runner": artifact["runner"],
            "runner_version": artifact["runner_version"],
            "runner_verdict": "UNVERIFIED",
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
            "artifact_ref": ref,
            "artifact_sha256": artifact_sha,
        }

    invariant = dict(structural.TRANSFER_INVARIANT)
    invariant_sha = canonical_hash(invariant)
    recipe_manifest = {
        "artifact_kind": "TRANSFER_RECIPE_MANIFEST",
        "recipes": candidate["transfer"]["recipes"],
        "input_revision": spec["revision"],
        "candidate_packet_sha256": candidate_sha,
    }
    recipe_manifest_ref = "evidence/transfer-recipe-manifest.json"
    recipe_manifest_sha = write_json(root, recipe_manifest_ref, recipe_manifest)
    transfer_packet_sha = verifier.transfer_packet_sha256(
        spec["revision"],
        candidate_sha,
        invariant_sha,
        recipe_manifest_sha,
    )
    expected_state_sha = canonical_hash(candidate["code_reconstruction"])
    transfer_stage_artifacts = {}
    for stage in verifier.TRANSFER_EVIDENCE_STAGES:
        if stage == "PROGRAM_TRANSFER_RUBBING":
            stage_input_sha = recipe_manifest_sha
            stage_output_sha = transfer_packet_sha
        elif stage == "RECEIVER_RECONSTRUCTION":
            stage_input_sha = transfer_packet_sha
            stage_output_sha = expected_state_sha
        else:
            stage_input_sha = expected_state_sha
            stage_output_sha = candidate_sha
        artifact = {
            "stage": stage,
            "executed": True,
            "result": "PASS",
            "evidence_class": "FIELD_EVIDENCE",
            "runner": "synthetic-transfer-runner",
            "runner_version": "1.0",
            "runner_verdict": "UNVERIFIED",
            "input_sha256": stage_input_sha,
            "output_sha256": stage_output_sha,
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
        }
        if stage == "PROGRAM_TRANSFER_RUBBING":
            artifact["transfer_mode"] = "PROGRAM_TRANSFER_RUBBING"
            artifact["recipe_manifest_sha256"] = recipe_manifest_sha
            artifact["transfer_packet_sha256"] = transfer_packet_sha
        elif stage == "RECEIVER_RECONSTRUCTION":
            artifact["input_packet_sha256"] = transfer_packet_sha
            artifact["actual_state_sha256"] = expected_state_sha
        elif stage == "EQUIVALENT_STATE_VERIFICATION":
            artifact["expected_state_sha256"] = expected_state_sha
            artifact["actual_state_sha256"] = expected_state_sha
            artifact["equivalence_method"] = verifier.EQUIVALENCE_METHOD
            artifact["equivalent"] = True
        ref = f"evidence/transfer-{stage}.json"
        artifact_sha = write_json(root, ref, artifact)
        transfer_stage_artifacts[stage] = {
            "artifact_ref": ref,
            "artifact_sha256": artifact_sha,
            "input_sha256": stage_input_sha,
            "output_sha256": stage_output_sha,
        }

    transfer_result_for_object = {
        "invariant_sha256": invariant_sha,
        "recipe_manifest_sha256": recipe_manifest_sha,
        "transfer_packet_sha256": transfer_packet_sha,
    }
    object_ref = "evidence/transfer-object.json"
    object_sha = write_json(
        root,
        object_ref,
        verifier.expected_cross_node_transfer_object(
            candidate,
            candidate_sha,
            transfer_result_for_object,
        ),
    )
    replay_ref = "evidence/replay-index.json"
    write_json(root, replay_ref, {"used_nonce_sha256": []})
    nonce = "synthetic_nonce_1234567890"
    scanned_artifacts = [
        {
            "artifact_kind": "IN_MEMORY_CANDIDATE",
            "artifact_ref": "IN_MEMORY",
            "artifact_sha256": candidate_sha,
        },
        {
            "artifact_kind": "TRANSFER_RECIPE_MANIFEST",
            "artifact_ref": recipe_manifest_ref,
            "artifact_sha256": recipe_manifest_sha,
        },
        *[
            {
                "artifact_kind": stage,
                "artifact_ref": transfer_stage_artifacts[stage]["artifact_ref"],
                "artifact_sha256": transfer_stage_artifacts[stage]["artifact_sha256"],
            }
            for stage in verifier.TRANSFER_EVIDENCE_STAGES
        ],
        {
            "artifact_kind": "CROSS_NODE_TRANSFER_OBJECT",
            "artifact_ref": object_ref,
            "artifact_sha256": object_sha,
        },
    ]
    return {
        "producer_code_sha256": candidate["producer"]["code_sha256"],
        "input_spec_sha256": candidate["producer"]["input_spec_sha256"],
        "input_revision": spec["revision"],
        "construction_input_sha256": pre_fix_sha,
        "journey_receipts": journey_receipts,
        "redteam_receipts": redteam_receipts,
        "runtime_receipts": {
            "segments": runtime_segments,
            "fallbacks": runtime_fallbacks,
        },
        "core_function_receipts": core_function_receipts,
        "transfer_receipt": {
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
            "invariant": invariant,
            "invariant_sha256": invariant_sha,
            "recipe_manifest_ref": recipe_manifest_ref,
            "recipe_manifest_sha256": recipe_manifest_sha,
            "transfer_packet_sha256": transfer_packet_sha,
            "stage_artifacts": transfer_stage_artifacts,
        },
        "trade_secret_receipt": {
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
            "boundary": dict(structural.TRADE_SECRET_BOUNDARY),
            "public_contract_only": True,
            "scanned_artifacts": scanned_artifacts,
        },
        "run_context": {
            "run_id": "IFGC_SYNTHETIC_001",
            "nonce": nonce,
            "issued_at": "2026-08-20T04:00:00Z",
            "expires_at": "2026-08-20T04:10:00Z",
        },
        "cross_node_receipt": {
            "protocol": "IFGC-GTP",
            "protocol_version": "1.0.0",
            "run_id": "IFGC_SYNTHETIC_001",
            "nonce": nonce,
            "logical_root_id": spec["logical_root_id"],
            "source_node": spec["node_id"],
            "target_node": "node-b",
            "input_revision": spec["revision"],
            "candidate_packet_sha256": candidate_sha,
            "source_snapshot_sha256": digest("source-snapshot"),
            "target_snapshot_sha256": digest("target-snapshot"),
            "object_ref": object_ref,
            "object_sha256": object_sha,
            "replay_index_ref": replay_ref,
            "source_platform": "linux-x86_64",
            "target_platform": "windows-amd64",
            "platform_compatibility": "PASS",
            "pollution_guard": "PASS",
            "drift_guard": "PASS",
            "tamper_guard": "PASS",
            "rollback_guard": "PASS",
            "verifier_result": "PASS",
            "authority_state": "UNVERIFIED",
            "signature_state": "UNVERIFIED",
        },
    }


class DetachedVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.spec = complete_spec()
        self.bundle = complete_bundle(self.root, self.spec)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def assert_hold(self, code: str, spec: dict | None = None, bundle: dict | None = None) -> None:
        with self.assertRaises(structural.ConstructionHold) as caught:
            verifier.verify(self.root, spec or self.spec, bundle or self.bundle, now=NOW)
        self.assertEqual(code, caught.exception.code)

    def test_producer_emits_only_unverified_candidate_states(self) -> None:
        candidate = producer.build_candidate(self.spec)
        self.assertNotIn("PASS_USER_JOURNEY", candidate["states"])
        self.assertIn("RUNTIME_EVIDENCE_UNVERIFIED", candidate["states"])
        self.assertIn("USER_JOURNEY_EVIDENCE_UNVERIFIED", candidate["states"])
        self.assertIn("CROSS_NODE_REPLAY_UNVERIFIED", candidate["states"])
        self.assertIn("AUTHENTICITY_UNVERIFIED", candidate["states"])
        self.assertEqual("NOT_RUN", candidate["verifier_result"])
        self.assertEqual(
            "STRUCTURAL_ONLY",
            candidate["eight_d"]["dimensions"]["identity_source"]["structural_status"],
        )
        self.assertNotIn("status", candidate["eight_d"]["dimensions"]["identity_source"])
        self.assertEqual("UNVERIFIED", candidate["eight_d"]["dynamic_depth"]["verification_state"])
        self.assertTrue(
            all(
                item["claimed_result"] == "UNVERIFIED"
                and item["evidence_class"] == "STRUCTURAL_ONLY"
                for item in candidate["runtime_completion_chain"]["ordered_stages"]
            )
        )
        self.assertEqual(
            "STRUCTURAL_ONLY",
            candidate["core_functions"]["ANALYSIS"]["structural_status"],
        )
        self.assertEqual("PASS", candidate["product_personas"]["REAL_HUMAN_USER"]["claimed_status"])
        self.assertNotIn("status", candidate["product_matrix"]["risk"])
        self.assertEqual("PASS", candidate["architecture"]["claimed_status"])
        self.assertNotIn("status", candidate["architecture"])
        self.assertEqual("PASS", candidate["architecture"]["constraints"][0]["claimed_status"])
        self.assertEqual("PASS", candidate["code_reconstruction"]["claimed_status"])
        self.assertEqual("PASS", candidate["closure"]["stages"]["runtime_evidence"]["claimed_status"])
        self.assertEqual(
            "STRUCTURAL_ONLY",
            candidate["transfer"]["invariant"]["structural_status"],
        )
        self.assertNotIn("status", candidate["transfer"]["tests"][0])
        self.assertEqual(
            "STRUCTURAL_ONLY",
            candidate["trade_secret_boundary"]["structural_status"],
        )

    def test_detached_verifier_can_reach_review_not_activation(self) -> None:
        packet = verifier.verify(self.root, self.spec, self.bundle, now=NOW)
        self.assertEqual("STRUCTURE_AND_HASH_CHECK_PASS", packet["verifier_result"])
        self.assertNotIn("PASS_USER_JOURNEY", packet["states"])
        self.assertNotIn("READY_FOR_TOTAL_FIELD_REVIEW", packet["states"])
        self.assertIn("RUNTIME_EVIDENCE_UNVERIFIED", packet["states"])
        self.assertIn("USER_JOURNEY_EVIDENCE_UNVERIFIED", packet["states"])
        self.assertIn("CROSS_NODE_REPLAY_UNVERIFIED", packet["states"])
        self.assertIn("AUTHENTICITY_UNVERIFIED", packet["states"])
        self.assertIn("ACTIVATION_NOT_AUTHORIZED", packet["states"])
        self.assertEqual("NOT_AUTHORIZED", packet["governance"]["activation"])
        self.assertEqual(12, len(packet["detached_verification"]["runtime"]["segments"]))
        self.assertEqual(
            "HASH_CHAIN_VALID",
            packet["detached_verification"]["runtime"]["hash_chain"],
        )
        self.assertEqual(
            set(structural.CORE_FUNCTIONS),
            set(packet["detached_verification"]["core_functions"]),
        )
        self.assertEqual(
            "UNVERIFIED",
            packet["detached_verification"]["cross_node"]["authenticity_result"],
        )
        relational = packet["detached_verification"]["relational_contract"]
        self.assertEqual("STRUCTURE_AND_HASH_CHECK_PASS", relational["state"])
        self.assertEqual("PARALLEL_SHADOW", relational["candidate_relation"])
        self.assertFalse(relational["grants_authority"])

    def test_secure_writer_creates_only_three_files_inside_new_run_dir(self) -> None:
        packet = verifier.verify(self.root, self.spec, self.bundle, now=NOW)
        (self.root / "runtime").mkdir()
        report = verifier.secure_write(self.root, "runtime/run-001", packet)
        names = {path.name for path in (self.root / "runtime/run-001").iterdir()}
        self.assertEqual({structural.PACKET_NAME, structural.SHA_NAME, structural.SEAL_NAME}, names)
        self.assertTrue(report["artifacts_written"])
        seal = json.loads((self.root / "runtime/run-001" / structural.SEAL_NAME).read_text(encoding="utf-8"))
        self.assertEqual("UNVERIFIED", seal["authenticity_result"])
        self.assertEqual("STRUCTURE_AND_HASH_CHECK_PASS", seal["verifier_result"])
        self.assertEqual(12, seal["summary"]["runtime_segments"])
        self.assertEqual(
            "PARALLEL_SHADOW",
            seal["summary"]["mainline_relation"]["candidate_relation"],
        )
        self.assertEqual(set(structural.CONTINUATION_AXES), set(seal["summary"]["continuation_distance"]))
        self.assertEqual(
            list(structural.RECOVERY_STEPS),
            [item["step"] for item in seal["summary"]["supply_demand_fit"]["recovery_route"]],
        )

    def test_relational_evidence_tamper_is_detected(self) -> None:
        path = self.root / self.spec["relational_evidence"]["artifact_ref"]
        artifact = json.loads(path.read_text(encoding="utf-8"))
        artifact["mainline_relation"]["candidate_relation"] = "REPLACE"
        path.write_text(
            json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        self.assert_hold("HOLD_RELATIONAL_EVIDENCE_HASH")

    def test_hash_valid_but_contradictory_relational_evidence_is_rejected(self) -> None:
        spec = copy.deepcopy(self.spec)
        artifact_ref = spec["relational_evidence"]["artifact_ref"]
        artifact_path = self.root / artifact_ref
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["mainline_relation"]["candidate_relation"] = "REPLACE"
        artifact_sha = write_json(self.root, artifact_ref, artifact)
        spec["relational_evidence"]["artifact_sha256"] = artifact_sha
        stage_ref = spec["relational_evidence"]["stage_receipt_ref"]
        stage = {
            "schema_id": "IFGC_RELATIONAL_STAGE_RECEIPT_V1",
            "input_revision": spec["revision"],
            "evidence_class": "FIELD_EVIDENCE",
            "artifact_ref": artifact_ref,
            "artifact_sha256": artifact_sha,
            "state": "STAGED",
            "runner_verdict": "UNVERIFIED",
            "grants_authority": False,
        }
        spec["relational_evidence"]["stage_receipt_sha256"] = write_json(
            self.root, stage_ref, stage
        )
        candidate = producer.build_candidate(spec)
        with self.assertRaises(structural.ConstructionHold) as caught:
            verifier.verify_relational_contract(self.root, spec, candidate)
        self.assertEqual("HOLD_RELATIONAL_EVIDENCE_CONFLICT", caught.exception.code)

    def test_tampered_producer_relational_output_is_rejected_detached(self) -> None:
        original = producer.build_candidate

        def tampered(spec: dict) -> dict:
            candidate = original(spec)
            candidate["mainline_relation"]["candidate_relation"] = "REPLACE"
            return candidate

        with patch.object(producer, "build_candidate", side_effect=tampered):
            self.assert_hold("HOLD_RELATIONAL_CANDIDATE_TAMPER")

    def test_all_journeys_need_actual_entrypoint_execution_and_runner(self) -> None:
        for field in ("actual_entrypoint", "runner", "runner_version"):
            with self.subTest(field=field):
                bundle = copy.deepcopy(self.bundle)
                del bundle["journey_receipts"][0][field]
                self.assert_hold("HOLD_REQUIRED_STRING", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["journey_receipts"][0]["executed"] = False
        self.assert_hold("HOLD_JOURNEY_NOT_EXECUTED_PASS", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["journey_receipts"][0]["runner_verdict"] = "PASS"
        self.assert_hold("HOLD_RUNNER_VERDICT_SCOPE", bundle=bundle)

    def test_missing_denial_journey_receipt_holds(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["journey_receipts"] = bundle["journey_receipts"][:1]
        self.assert_hold("HOLD_JOURNEY_RECEIPT_SET", bundle=bundle)

    def test_missing_journey_scenario_or_surface_coverage_holds(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["user_journeys"] = [
            item for item in spec["user_journeys"] if item["scenario"] != "RETURNING"
        ]
        self.assert_hold("HOLD_JOURNEY_SCENARIO_SET_INCOMPLETE", spec=spec)
        spec = copy.deepcopy(self.spec)
        for item in spec["user_journeys"]:
            item["surface"] = "DESKTOP"
        self.assert_hold("HOLD_JOURNEY_SURFACE_SET_INCOMPLETE", spec=spec)

    def test_journey_artifact_tamper_is_detected(self) -> None:
        ref = self.bundle["journey_receipts"][0]["artifact_ref"]
        (self.root / ref).write_text("{}\n", encoding="utf-8")
        self.assert_hold("HOLD_JOURNEY_ARTIFACT_HASH")

    def test_redteam_fix_requires_rerun_and_all_downstream_stages(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["redteam_receipts"]["INTENT"]["rounds"][0]["rerun_executed"] = False
        self.assert_hold("HOLD_REDTEAM_FIX_RERUN", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["redteam_receipts"]["INTENT"]["downstream_revalidated"] = []
        self.assert_hold("HOLD_REDTEAM_DOWNSTREAM_REVALIDATION", bundle=bundle)

    def test_exact_seven_redteam_receipts_are_required(self) -> None:
        self.assertEqual(7, len(structural.REDTEAM_CHECKS))
        for stage in structural.REDTEAM_CHECKS:
            with self.subTest(stage=stage):
                bundle = copy.deepcopy(self.bundle)
                del bundle["redteam_receipts"][stage]
                self.assert_hold("HOLD_REDTEAM_RECEIPT_SET", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["redteam_receipts"]["EXTRA"] = {}
        self.assert_hold("HOLD_REDTEAM_RECEIPT_SET", bundle=bundle)

    def test_producer_code_input_revision_and_candidate_hash_are_bound(self) -> None:
        cases = (
            ("producer_code_sha256", digest("wrong"), "HOLD_PRODUCER_CODE_BINDING"),
            ("input_spec_sha256", digest("wrong"), "HOLD_INPUT_SPEC_BINDING"),
            ("input_revision", "wrong", "HOLD_INPUT_REVISION_BINDING"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                bundle = copy.deepcopy(self.bundle)
                bundle[field] = value
                self.assert_hold(code, bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["cross_node_receipt"]["candidate_packet_sha256"] = digest("wrong")
        self.assert_hold("HOLD_CROSS_NODE_BINDING", bundle=bundle)

    def test_cross_node_root_node_revision_object_platform_and_guards_are_bound(self) -> None:
        cases = (
            ("logical_root_id", "wrong", "HOLD_CROSS_NODE_BINDING"),
            ("source_node", "wrong", "HOLD_CROSS_NODE_BINDING"),
            ("input_revision", "wrong", "HOLD_CROSS_NODE_BINDING"),
            ("target_node", self.spec["node_id"], "HOLD_CROSS_NODE_IDENTITY"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                bundle = copy.deepcopy(self.bundle)
                bundle["cross_node_receipt"][field] = value
                self.assert_hold(code, bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["cross_node_receipt"]["platform_compatibility"] = "HOLD"
        bundle["cross_node_receipt"]["pollution_guard"] = "PASS"
        bundle["cross_node_receipt"]["drift_guard"] = "HOLD"
        packet = verifier.verify(self.root, self.spec, bundle, now=NOW)
        cross_node = packet["detached_verification"]["cross_node"]
        self.assertEqual("HOLD", cross_node["claimed_platform_compatibility"])
        self.assertEqual("PASS", cross_node["claimed_pollution_guard"])
        self.assertEqual("HOLD", cross_node["claimed_drift_guard"])
        self.assertEqual("STRUCTURE_AND_HASH_CHECK_PASS", cross_node["integrity_result"])
        object_ref = self.bundle["cross_node_receipt"]["object_ref"]
        (self.root / object_ref).write_bytes(b"tampered")
        self.assert_hold("HOLD_CROSS_NODE_OBJECT_HASH")

    def test_cross_node_transfer_object_must_be_public_canonical_json(self) -> None:
        bundle = complete_bundle(self.root, self.spec)
        object_ref = "evidence/opaque-transfer-object.bin"
        object_sha = write_bytes(self.root, object_ref, b"opaque-binary")
        bundle["cross_node_receipt"]["object_ref"] = object_ref
        bundle["cross_node_receipt"]["object_sha256"] = object_sha
        self.assert_hold("HOLD_ARTIFACT_JSON_REF", bundle=bundle)

        bundle = complete_bundle(self.root, self.spec)
        object_ref = bundle["cross_node_receipt"]["object_ref"]
        noncanonical = b'{ "protocol" : "IFGC-GTP" }\n'
        (self.root / object_ref).write_bytes(noncanonical)
        bundle["cross_node_receipt"]["object_sha256"] = hashlib.sha256(noncanonical).hexdigest()
        self.assert_hold("HOLD_NON_CANONICAL_JSON", bundle=bundle)

        bundle = complete_bundle(self.root, self.spec)
        object_ref = bundle["cross_node_receipt"]["object_ref"]
        transfer_object = json.loads((self.root / object_ref).read_text(encoding="utf-8"))
        transfer_object["inline_source"] = "def leaked():\n    return 1"
        bundle["cross_node_receipt"]["object_sha256"] = write_json(self.root, object_ref, transfer_object)
        self.assert_hold("HOLD_FULL_SOURCE_EMBEDDED", bundle=bundle)

    def test_nonce_ttl_and_readonly_replay_index_are_hard_gates(self) -> None:
        replay_ref = self.bundle["cross_node_receipt"]["replay_index_ref"]
        nonce = self.bundle["run_context"]["nonce"]
        write_json(self.root, replay_ref, {"used_nonce_sha256": [hashlib.sha256(nonce.encode()).hexdigest()]})
        self.assert_hold("HOLD_REPLAY")
        self.bundle = complete_bundle(self.root, self.spec)
        self.assert_hold(
            "HOLD_TTL",
            bundle=self.bundle,
            spec=self.spec,
        ) if False else None
        with self.assertRaises(structural.ConstructionHold) as caught:
            verifier.verify(
                self.root,
                self.spec,
                self.bundle,
                now=NOW + dt.timedelta(hours=1),
            )
        self.assertEqual("HOLD_TTL", caught.exception.code)

    def test_runtime_receipts_require_exact_order_and_artifact_hashes(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["runtime_receipts"]["segments"] = bundle["runtime_receipts"]["segments"][:-1]
        self.assert_hold("HOLD_RUNTIME_RECEIPT_STAGE_SET", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        segments = bundle["runtime_receipts"]["segments"]
        segments[0], segments[1] = segments[1], segments[0]
        self.assert_hold("HOLD_RUNTIME_RECEIPT_ORDER", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        ref = bundle["runtime_receipts"]["segments"][0]["artifact_ref"]
        (self.root / ref).write_text("{}\n", encoding="utf-8")
        self.assert_hold("HOLD_RUNTIME_ARTIFACT_HASH", bundle=bundle)

    def test_runtime_receipts_require_first_chained_and_final_hashes(self) -> None:
        cases = (
            (0, "input_sha256", digest("wrong")),
            (1, "input_sha256", digest("wrong")),
            (len(structural.TECHNICAL_CHAIN_STAGES) - 1, "output_sha256", digest("wrong")),
        )
        for index, field, value in cases:
            with self.subTest(index=index, field=field):
                bundle = copy.deepcopy(self.bundle)
                bundle["runtime_receipts"]["segments"][index][field] = value
                self.assert_hold("HOLD_RUNTIME_HASH_CHAIN", bundle=bundle)

    def test_runtime_8d_stage_must_bind_exact_candidate_8d(self) -> None:
        stage_index = list(structural.TECHNICAL_CHAIN_STAGES).index(
            structural.HIGHEST_ORDER_8D_DYNAMIC_INTENT_FIELD
        )
        for mutator in ("missing_dimension", "authority_true"):
            with self.subTest(mutator=mutator):
                bundle = complete_bundle(self.root, self.spec)
                segment = bundle["runtime_receipts"]["segments"][stage_index]
                ref = segment["artifact_ref"]
                artifact = json.loads((self.root / ref).read_text(encoding="utf-8"))
                if mutator == "missing_dimension":
                    del artifact["eight_d"]["dimensions"]["identity_source"]
                else:
                    artifact["eight_d"]["dynamic_depth"]["authority_granted"] = True
                segment["artifact_sha256"] = write_json(self.root, ref, artifact)
                self.assert_hold("HOLD_RUNTIME_8D_ARTIFACT_BINDING", bundle=bundle)

    def test_runtime_initial_gaps_and_fallbacks_are_exact(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["runtime_receipts"]["fallbacks"][0]["enabled_after_stage"] = "RUNTIME_GAP_LOCALIZATION"
        self.assert_hold("HOLD_FALLBACK_STAGE", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["runtime_receipts"]["fallbacks"][0]["target_gap_refs"] = ["synthetic://runtime-gap/unknown"]
        self.assert_hold("HOLD_FALLBACK_TARGET_GAP_REFS", bundle=bundle)

        spec = copy.deepcopy(self.spec)
        spec["pattern_recall"]["external"] = []
        spec["runtime_completion_chain"]["initial_gap_refs"] = []
        spec["runtime_completion_chain"]["fallbacks"] = []
        bundle = complete_bundle(self.root, spec)
        bundle["runtime_receipts"]["fallbacks"] = copy.deepcopy(self.bundle["runtime_receipts"]["fallbacks"])
        self.assert_hold("HOLD_FALLBACK_INITIAL_GAP_REFS", spec=spec, bundle=bundle)

    def test_model_prior_retrieval_cannot_masquerade_as_field_evidence(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["pattern_recall"]["external"] = []
        spec["adi_map"]["nodes"].append(
            {
                "id": "N-MODEL-PRIOR",
                "coordinate_ref": "adi://node-a/model-prior/runtime-gap",
                "source_class": "MODEL_PRIOR_CANDIDATE",
            }
        )
        spec["runtime_completion_chain"]["fallbacks"][0]["source_class"] = "MODEL_PRIOR_CANDIDATE"
        bundle = complete_bundle(self.root, spec)
        fallback = bundle["runtime_receipts"]["fallbacks"][0]
        ref = fallback["retrieval_artifact_ref"]
        artifact = json.loads((self.root / ref).read_text(encoding="utf-8"))
        artifact["evidence_class"] = "FIELD_EVIDENCE"
        fallback["retrieval_artifact_sha256"] = write_json(self.root, ref, artifact)
        self.assert_hold("HOLD_FALLBACK_RETRIEVAL_EVIDENCE_CLASS", spec=spec, bundle=bundle)

    def test_fallback_rerun_must_close_exact_gap_refs(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        fallback = bundle["runtime_receipts"]["fallbacks"][0]
        ref = fallback["rerun_artifact_ref"]
        artifact = json.loads((self.root / ref).read_text(encoding="utf-8"))
        artifact["closed_gap_refs"] = ["synthetic://runtime-gap/unknown"]
        fallback["rerun_artifact_sha256"] = write_json(self.root, ref, artifact)
        self.assert_hold("HOLD_FALLBACK_RERUN_BINDING", bundle=bundle)
        bundle = complete_bundle(self.root, self.spec)
        fallback = bundle["runtime_receipts"]["fallbacks"][0]
        ref = fallback["rerun_artifact_ref"]
        artifact = json.loads((self.root / ref).read_text(encoding="utf-8"))
        artifact["input_sha256"] = digest("wrong")
        fallback["rerun_artifact_sha256"] = write_json(self.root, ref, artifact)
        self.assert_hold("HOLD_FALLBACK_RERUN_HASH_CHAIN", bundle=bundle)

    def test_all_four_core_functions_need_independent_artifacts(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        del bundle["core_function_receipts"]["ANALYSIS"]
        self.assert_hold("HOLD_CORE_FUNCTION_RECEIPT_SET", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["core_function_receipts"]["ANALYSIS"]["artifact_ref"] = bundle["core_function_receipts"]["TRANSFER"]["artifact_ref"]
        bundle["core_function_receipts"]["ANALYSIS"]["artifact_sha256"] = bundle["core_function_receipts"]["TRANSFER"]["artifact_sha256"]
        self.assert_hold("HOLD_CORE_FUNCTION_ARTIFACT_BINDING", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["core_function_receipts"]["ANALYSIS"]["subject_sha256"] = digest("wrong")
        self.assert_hold("HOLD_CORE_FUNCTION_SUBJECT_HASH", bundle=bundle)

    def test_transfer_receipt_rechecks_invariant_receiver_and_equivalence(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["transfer_receipt"]["invariant"]["hash_method"] = "sha512"
        self.assert_hold("HOLD_TRANSFER_INVARIANT", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["transfer_receipt"]["transfer_packet_sha256"] = digest("wrong")
        self.assert_hold("HOLD_TRANSFER_PACKET_HASH", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        ref = bundle["transfer_receipt"]["recipe_manifest_ref"]
        artifact = json.loads((self.root / ref).read_text(encoding="utf-8"))
        artifact["recipes"] = []
        bundle["transfer_receipt"]["recipe_manifest_sha256"] = write_json(self.root, ref, artifact)
        self.assert_hold("HOLD_TRANSFER_RECIPE_MANIFEST_BINDING", bundle=bundle)
        bundle = complete_bundle(self.root, self.spec)
        bundle["transfer_receipt"]["stage_artifacts"]["PROGRAM_TRANSFER_RUBBING"]["input_sha256"] = digest("wrong")
        self.assert_hold("HOLD_TRANSFER_HASH_CHAIN", bundle=bundle)
        bundle = complete_bundle(self.root, self.spec)
        ref = bundle["transfer_receipt"]["stage_artifacts"]["RECEIVER_RECONSTRUCTION"]["artifact_ref"]
        artifact = json.loads((self.root / ref).read_text(encoding="utf-8"))
        artifact["actual_state_sha256"] = digest("wrong")
        bundle["transfer_receipt"]["stage_artifacts"]["RECEIVER_RECONSTRUCTION"]["artifact_sha256"] = write_json(self.root, ref, artifact)
        self.assert_hold("HOLD_TRANSFER_RECEIVER_STATE", bundle=bundle)
        bundle = complete_bundle(self.root, self.spec)
        ref = bundle["transfer_receipt"]["stage_artifacts"]["EQUIVALENT_STATE_VERIFICATION"]["artifact_ref"]
        artifact = json.loads((self.root / ref).read_text(encoding="utf-8"))
        artifact["equivalent"] = False
        bundle["transfer_receipt"]["stage_artifacts"]["EQUIVALENT_STATE_VERIFICATION"]["artifact_sha256"] = write_json(self.root, ref, artifact)
        self.assert_hold("HOLD_TRANSFER_EQUIVALENCE", bundle=bundle)
        for stage in ("RECEIVER_RECONSTRUCTION", "EQUIVALENT_STATE_VERIFICATION"):
            with self.subTest(stage=stage):
                bundle = complete_bundle(self.root, self.spec)
                ref = bundle["transfer_receipt"]["stage_artifacts"][stage]["artifact_ref"]
                (self.root / ref).write_text("{}\n", encoding="utf-8")
                self.assert_hold("HOLD_TRANSFER_ARTIFACT_HASH", bundle=bundle)

    def test_trade_secret_receipt_must_remain_public_contract_only(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["trade_secret_receipt"]["boundary"]["weights_included"] = True
        self.assert_hold("HOLD_TRADE_SECRET_BOUNDARY", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["trade_secret_receipt"]["public_contract_only"] = False
        self.assert_hold("HOLD_TRADE_SECRET_BOUNDARY", bundle=bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle["trade_secret_receipt"]["scanned_artifacts"][1] = {
            "artifact_kind": "TRANSFER_RECIPE_MANIFEST",
            "artifact_ref": "evidence/arbitrary.json",
            "artifact_sha256": write_json(self.root, "evidence/arbitrary.json", {"artifact_kind": "ARBITRARY"}),
        }
        self.assert_hold("HOLD_TRADE_SECRET_SCANNED_SET", bundle=bundle)

    def test_authority_claim_never_activates(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        bundle["cross_node_receipt"]["authority_state"] = "VERIFIED"
        packet = verifier.verify(self.root, self.spec, bundle, now=NOW)
        self.assertEqual("NOT_AUTHORIZED", packet["governance"]["activation"])
        self.assertIn("ACTIVATION_NOT_AUTHORIZED", packet["states"])
        self.assertEqual("UNVERIFIED", packet["detached_verification"]["cross_node"]["authenticity_result"])
        self.assertEqual("VERIFIED", packet["detached_verification"]["cross_node"]["claimed_authority_state"])
        self.assertNotIn("authority_state", packet["detached_verification"]["cross_node"])
        bundle = copy.deepcopy(self.bundle)
        bundle["cross_node_receipt"]["authority_state"] = "VERIFIED"
        bundle["cross_node_receipt"]["signature_state"] = "VERIFIED"
        bundle["cross_node_receipt"]["public_key"] = "synthetic-public-key"
        bundle["cross_node_receipt"]["self_signature"] = "synthetic-self-signature"
        packet = verifier.verify(self.root, self.spec, bundle, now=NOW)
        self.assertEqual("UNVERIFIED", packet["detached_verification"]["cross_node"]["authenticity_result"])
        self.assertEqual("VERIFIED", packet["detached_verification"]["cross_node"]["claimed_signature_state"])
        self.assertTrue(packet["detached_verification"]["cross_node"]["claimed_self_signature_present"])
        self.assertEqual("NOT_AUTHORIZED", packet["governance"]["activation"])
        bundle = copy.deepcopy(self.bundle)
        bundle["cross_node_receipt"]["trusted_root"] = "PRESENT"
        self.assert_hold("HOLD_TRUSTED_ROOT_INJECTION", bundle=bundle)

    def test_placeholders_and_refs_are_not_misclassified_as_secrets(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["password"] = {"env_ref": "APP_PASSWORD"}
        spec["key_ref"] = "vault://candidate-key"
        spec["synthetic_rules"] = {
            "weight_parameter_name": "attention_weight",
            "rule_name": "short_weight_rule",
        }
        spec["transfer"]["recipes"][0]["content"] = "placeholder-only"
        candidate = producer.build_candidate(spec)
        self.assertIn("CANDIDATE", candidate["states"])

    def test_substantive_secret_shape_and_full_source_blob_hold(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["password"] = "synthetic-raw-value"
        with self.assertRaises(structural.ConstructionHold) as caught:
            producer.build_candidate(spec)
        self.assertEqual("HOLD_SUBSTANTIVE_SENSITIVE_FIELD", caught.exception.code)
        spec = copy.deepcopy(self.spec)
        spec["code_reconstruction"]["files"][0]["recipe"]["opaque"] = (
            "def generated():\n    return 1\n" * 300
        )
        with self.assertRaises(structural.ConstructionHold) as caught:
            producer.build_candidate(spec)
        self.assertEqual("HOLD_FULL_SOURCE_BY_CONTENT_TYPE", caught.exception.code)

    def test_substantive_private_content_shapes_hold_without_weight_word_false_positive(self) -> None:
        cases = (
            ("weights", [0.1, 0.2], "HOLD_SUBSTANTIVE_PRIVATE_CONTENT"),
            ("private_lookup_table", {"user": "route"}, "HOLD_SUBSTANTIVE_PRIVATE_CONTENT"),
            ("phase_mapping", {"phase_1": "internal"}, "HOLD_SUBSTANTIVE_PRIVATE_CONTENT"),
            ("WHY_IT_RUNS", {"step": "internal mechanism"}, "HOLD_SUBSTANTIVE_PRIVATE_CONTENT"),
            ("content_type", "private_lookup_table", "HOLD_SUBSTANTIVE_PRIVATE_CONTENT_TYPE"),
        )
        for key, value, code in cases:
            with self.subTest(key=key):
                spec = copy.deepcopy(self.spec)
                spec["synthetic_private_shape"] = {key: value}
                with self.assertRaises(structural.ConstructionHold) as caught:
                    producer.build_candidate(spec)
                self.assertEqual(code, caught.exception.code)

    def test_transfer_source_content_fields_hold_unless_placeholder(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["transfer"]["recipes"][0]["source_text"] = "placeholder-only"
        candidate = producer.build_candidate(spec)
        self.assertIn("CANDIDATE", candidate["states"])
        spec = copy.deepcopy(self.spec)
        spec["transfer"]["recipes"][0]["source_text"] = "print('embedded source')"
        with self.assertRaises(structural.ConstructionHold) as caught:
            producer.build_candidate(spec)
        self.assertEqual("HOLD_FULL_SOURCE_EMBEDDED", caught.exception.code)

    def test_product_persona_matrix_provenance_and_effect_chain_are_hard_gates(self) -> None:
        spec = copy.deepcopy(self.spec)
        del spec["product_personas"]["REAL_HUMAN_USER"]
        with self.assertRaises(structural.ConstructionHold) as caught:
            producer.build_candidate(spec)
        self.assertEqual("HOLD_PRODUCT_PERSONAS", caught.exception.code)
        spec = copy.deepcopy(self.spec)
        del spec["product_matrix"]["cost"]
        with self.assertRaises(structural.ConstructionHold) as caught:
            producer.build_candidate(spec)
        self.assertEqual("HOLD_PRODUCT_MATRIX_INCOMPLETE", caught.exception.code)
        spec = copy.deepcopy(self.spec)
        spec["provenance_catalog"] = spec["provenance_catalog"][:-1]
        with self.assertRaises(structural.ConstructionHold) as caught:
            producer.build_candidate(spec)
        self.assertEqual("HOLD_PROVENANCE_SET_INCOMPLETE", caught.exception.code)
        spec = copy.deepcopy(self.spec)
        spec["allowed_effects"][0]["immutable_source_chain"][0]["statement_sha256"] = digest("wrong")
        with self.assertRaises(structural.ConstructionHold) as caught:
            producer.build_candidate(spec)
        self.assertEqual("HOLD_EFFECT_CHAIN_HASH", caught.exception.code)

    def test_output_must_be_new_worktree_local_run_directory(self) -> None:
        packet = verifier.verify(self.root, self.spec, self.bundle, now=NOW)
        with self.assertRaises(structural.ConstructionHold) as caught:
            verifier.secure_write(self.root, "single-level", packet)
        self.assertEqual("HOLD_OUTPUT_NOT_NEW_RUN_DIRECTORY", caught.exception.code)
        (self.root / "runtime").mkdir()
        existing = self.root / "runtime/existing"
        existing.mkdir()
        with self.assertRaises(structural.ConstructionHold) as caught:
            verifier.secure_write(self.root, "runtime/existing", packet)
        self.assertEqual("HOLD_OUTPUT_EXISTS", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
