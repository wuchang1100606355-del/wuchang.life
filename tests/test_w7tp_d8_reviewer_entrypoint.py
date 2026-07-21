import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field import w7tp_d8_reviewer_entrypoint as reviewer


class D8ReviewerEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.intake = self.root / "intake"
        self.intake.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def resign(request):
        request["request_self_sha256"] = reviewer.sha256_bytes(
            reviewer.canonical_json_bytes(
                {key: value for key, value in request.items() if key != "request_self_sha256"}
            )
        )
        return request

    def offline_build_scope(self):
        base_digest = "sha256:" + "1" * 64
        base_reference = f"example.invalid/offline-base@{base_digest}"
        wheelhouse = self.root / "offline-build" / "wheelhouse"
        wheelhouse.mkdir(parents=True, exist_ok=True)
        (wheelhouse / "dependency.whl").write_bytes(b"offline-wheel")
        (wheelhouse / "requirements.lock").write_text("dependency==1.0 --hash=sha256:" + "2" * 64 + "\n")
        wheelhouse_sha256, wheelhouse_file_count = reviewer.wheelhouse_aggregate_sha256(
            wheelhouse,
            self.root,
        )
        containerfile = self.root / "offline-build" / "Containerfile"
        containerfile.write_text(
            "\n".join(
                [
                    f"FROM {base_reference}",
                    "RUN python3 -m pip install --no-index --find-links=/wheelhouse "
                    "--require-hashes --no-deps -r /wheelhouse/requirements.lock",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "base_image_reference": base_reference,
            "base_image_digest": base_digest,
            "wheelhouse_path": wheelhouse.relative_to(self.root).as_posix(),
            "wheelhouse_sha256": wheelhouse_sha256,
            "wheelhouse_file_count": wheelhouse_file_count,
            "containerfile_path": containerfile.relative_to(self.root).as_posix(),
            "containerfile_sha256": self.sha(containerfile),
            "network": "none",
            "network_download": False,
            "pull": False,
            "pip_no_index": True,
            "single_use_build": True,
            "image_qualification": True,
            "qualification_network": "none",
            "c1_c9_execution": False,
            "production_deploy": False,
            "existing_service_restart": False,
            "db_write": False,
            "canonical_change": False,
            "pointer_change": False,
        }

    def request(self, **overrides):
        now = datetime.now(timezone.utc)
        value = {
            "schema_version": "W7TP-D8-REVIEW-REQUEST/1.0",
            "packet_type": "D8_REVIEW_REQUEST",
            "run_id": "TEST_D8_REVIEW_REQUEST",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "state": "PENDING_TOTAL_FIELD_D8_DECISION",
            "requested_decision": "ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY",
            "only_request": "ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY",
            "canary_started": False,
            "d8_decision": "PENDING",
            "single_use": True,
            "request_self_hash_algorithm": reviewer.REQUEST_SELF_HASH_ALGORITHM,
            "bindings": self.source_bindings(now + timedelta(hours=1)),
            "atomic_gate": {"state": "PASS"},
            "non_execution_assertions": {
                "db_write": False,
                "deploy": False,
                "restart": False,
                "canonical_change": False,
                "pointer_change": False,
            },
        }
        value.update(overrides)
        value["request_self_sha256"] = reviewer.sha256_bytes(reviewer.canonical_json_bytes(value))
        return value

    def source_bindings(self, expires_at):
        archive = self.root / "archive"
        payload = archive / "payload"
        scope_sha = "c" * 64
        special = {
            "payload/SHA256_MANIFEST.json": {"scope_aggregate_sha256": scope_sha},
            "payload/TOTAL_FIELD_REVIEW_RECEIPT.json": {"state": "REVIEW_INPUTS_RECEIVED_AND_REVERIFIED"},
            "payload/TOTAL_FIELD_REVIEW_SHA256_MANIFEST.json": {"state": "PASS_TOTAL_FIELD_REVIEW_ACCEPTED"},
        }
        for rel, value in special.items():
            self.write_json(archive / rel, value)
        for index in range(7):
            self.write_json(payload / f"source_{index}.json", {"index": index, "candidate_only": True})
        payload_files = []
        for path in sorted(payload.glob("*.json")):
            payload_files.append(
                {
                    "path": path.relative_to(archive).as_posix(),
                    "sha256": self.sha(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        hashes = {entry["path"]: entry["sha256"] for entry in payload_files}
        receipt = {
            "source_bytes": "PASS_10_OF_10",
            "counts": {"total_files": 10},
            "files": payload_files,
        }
        receipt_path = archive / "COMPLETE_HANDOFF_RECEIPT.json"
        self.write_json(receipt_path, receipt)
        landing = {
            "candidate_binding": {
                "submitted_manifest_self_sha256": hashes["payload/SHA256_MANIFEST.json"],
                "submitted_scope_sha256": scope_sha,
                "total_field_review_receipt_sha256": hashes["payload/TOTAL_FIELD_REVIEW_RECEIPT.json"],
                "total_field_review_manifest_sha256": hashes["payload/TOTAL_FIELD_REVIEW_SHA256_MANIFEST.json"],
                "status": "PASS",
            },
            "expiry": {
                "reference_expires_at": expires_at.isoformat(),
                "status": "PASS",
            },
            "files": payload_files,
        }
        landing_path = archive / "COMPLETE_LANDING_MANIFEST.json"
        self.write_json(landing_path, landing)
        archive_files = []
        for path in (receipt_path, landing_path, *(archive / entry["path"] for entry in payload_files)):
            archive_files.append(
                {
                    "path": path.relative_to(archive).as_posix(),
                    "sha256": self.sha(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        archive_manifest_path = archive / "SHA256_MANIFEST.json"
        self.write_json(
            archive_manifest_path,
            {"manifest_self_hash_excluded": True, "files": archive_files},
        )
        return {
            "new_archive_path": archive.relative_to(self.root).as_posix(),
            "complete_handoff_receipt_path": receipt_path.relative_to(self.root).as_posix(),
            "complete_handoff_receipt_sha256": self.sha(receipt_path),
            "complete_landing_manifest_path": landing_path.relative_to(self.root).as_posix(),
            "complete_landing_manifest_sha256": self.sha(landing_path),
            "new_archive_manifest_path": archive_manifest_path.relative_to(self.root).as_posix(),
            "new_archive_manifest_sha256": self.sha(archive_manifest_path),
            "landing_payload_count": 10,
            "landing_payload_aggregate_sha256": reviewer.payload_aggregate_sha256(payload_files),
            "aggregate_algorithm_version": reviewer.AGGREGATE_ALGORITHM_VERSION,
            "aggregate_ordering": reviewer.AGGREGATE_ORDERING,
            "landing_payload_input_paths": [entry["path"] for entry in payload_files],
        }

    def package(self, request):
        request_path = self.intake / "D8_REVIEW_REQUEST.json"
        evidence_path = self.intake / "D8_SUBMISSION_EVIDENCE.json"
        self.write_json(request_path, request)
        self.write_json(evidence_path, {"candidate_only": True, "canary_started": False})
        files = []
        for path in (request_path, evidence_path):
            files.append(
                {
                    "path": path.relative_to(self.root).as_posix(),
                    "sha256": self.sha(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        manifest_path = self.intake / "SHA256_MANIFEST.json"
        self.write_json(manifest_path, {"files": files, "manifest_self_hash_excluded": True})
        return request_path, manifest_path, self.sha(manifest_path)

    def review(self, request, name="out", expected_hash=None, replay_root=None):
        request_path, manifest_path, manifest_sha = self.package(request)
        return reviewer.review_once(
            request_path=request_path,
            manifest_path=manifest_path,
            expected_manifest_sha256=expected_hash or manifest_sha,
            output_dir=self.root / name,
            repo_root=self.root,
            replay_root=replay_root,
        )

    def decision(self, name="out"):
        return json.loads((self.root / name / "TOTAL_FIELD_D8_DECISION.json").read_text())

    def test_valid_packet_allows_isolated_runtime_canary_only(self):
        result = self.review(self.request())
        self.assertEqual("ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY", result["final_decision"])
        self.assertFalse(result["canary_started"])
        self.assertEqual("absent", self.decision()["input_final_decision_field"])
        self.assertEqual(10, self.decision()["source_files_verified"])
        self.assertTrue((self.root / "out" / "TOTAL_FIELD_D8_REVIEW_RECEIPT.json").is_file())

    def test_exact_offline_build_enum_is_schema_valid_and_allowed(self):
        request = self.request(
            requested_decision=reviewer.DECISION_ALLOW_OFFLINE_BUILD,
            only_request=reviewer.DECISION_ALLOW_OFFLINE_BUILD,
            offline_build_scope=self.offline_build_scope(),
        )
        schema_path = Path(reviewer.__file__).resolve().parents[2] / "schemas/field/w7tp_total_field_d8_review_request_v1.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(request)))
        result = self.review(request)
        self.assertEqual(reviewer.DECISION_ALLOW_OFFLINE_BUILD, result["final_decision"])
        decision = self.decision()
        self.assertTrue(decision["offline_image_build_authorized"])
        self.assertTrue(decision["image_qualification_authorized"])
        self.assertFalse(decision["image_pull_authorized"])
        self.assertFalse(decision["build_network_authorized"])
        self.assertFalse(decision["c1_c9_execution_authorized"])
        self.assertFalse(decision["deployment_authorized"])

    def test_unknown_or_similar_offline_build_enum_blocks(self):
        for index, value in enumerate(
            (
                "ALLOW_NO_NETWORK_OFFLINE_CANARY_IMAGE_BUILD",
                "ALLOW_NO_NETWORK_OFFLINE_CANARY_IMAGE_BUILD_ONLY_V2",
            )
        ):
            with self.subTest(value=value):
                result = self.review(
                    self.request(requested_decision=value, only_request=value),
                    name=f"unknown-enum-{index}",
                )
                self.assertEqual("BLOCK", result["final_decision"])
                self.assertIn("BLOCK_SCHEMA_DECISION_SCOPE", result["reason_codes"])

    def test_offline_build_only_request_mismatch_blocks(self):
        result = self.review(
            self.request(
                requested_decision=reviewer.DECISION_ALLOW_OFFLINE_BUILD,
                only_request=reviewer.DECISION_ALLOW,
                offline_build_scope=self.offline_build_scope(),
            )
        )
        self.assertEqual("BLOCK", result["final_decision"])
        self.assertIn("BLOCK_SCHEMA_DECISION_SCOPE", result["reason_codes"])

    def test_offline_build_red_team_capability_injections_block(self):
        cases = (
            ("network", "bridge"),
            ("pull", True),
            ("production_deploy", True),
            ("c1_c9_execution", True),
        )
        for index, (field, value) in enumerate(cases):
            with self.subTest(field=field):
                scope = self.offline_build_scope()
                scope[field] = value
                result = self.review(
                    self.request(
                        requested_decision=reviewer.DECISION_ALLOW_OFFLINE_BUILD,
                        only_request=reviewer.DECISION_ALLOW_OFFLINE_BUILD,
                        offline_build_scope=scope,
                    ),
                    name=f"offline-build-injection-{index}",
                )
                self.assertEqual("BLOCK", result["final_decision"])
                self.assertTrue(any("OFFLINE_BUILD" in code for code in result["reason_codes"]))

    def test_offline_build_wheelhouse_hash_mismatch_holds(self):
        scope = self.offline_build_scope()
        scope["wheelhouse_sha256"] = "f" * 64
        result = self.review(
            self.request(
                requested_decision=reviewer.DECISION_ALLOW_OFFLINE_BUILD,
                only_request=reviewer.DECISION_ALLOW_OFFLINE_BUILD,
                offline_build_scope=scope,
            )
        )
        self.assertEqual("HOLD", result["final_decision"])
        self.assertIn("HOLD_OFFLINE_BUILD_WHEELHOUSE_MISMATCH", result["reason_codes"])

    def test_manifest_hash_error_holds(self):
        result = self.review(self.request(), expected_hash="b" * 64)
        self.assertEqual("HOLD", result["final_decision"])
        self.assertIn("HOLD_MANIFEST_SHA256_MISMATCH", result["reason_codes"])

    def test_schema_error_blocks(self):
        request = self.request()
        del request["packet_type"]
        result = self.review(request)
        self.assertEqual("BLOCK", result["final_decision"])
        self.assertIn("BLOCK_SCHEMA_REQUIRED_FIELD", result["reason_codes"])

    def test_expired_request_holds(self):
        request = self.request(
            created_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )
        result = self.review(request)
        self.assertEqual("HOLD", result["final_decision"])
        self.assertIn("HOLD_REQUEST_EXPIRED", result["reason_codes"])

    def test_replay_holds(self):
        request = self.request()
        first = self.review(request, name="decisions/first", replay_root=self.root / "decisions")
        self.assertEqual("ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY", first["final_decision"])
        second = self.review(request, name="decisions/second", replay_root=self.root / "decisions")
        self.assertEqual("HOLD", second["final_decision"])
        self.assertIn("HOLD_REQUEST_REPLAY", second["reason_codes"])

    def test_same_run_and_output_returns_identical_existing_result(self):
        request = self.request()
        first = self.review(request)
        second = self.review(request)
        self.assertEqual(first["decision_sha256"], second["decision_sha256"])
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        self.assertTrue(second["reused_existing_result"])

    def test_source_10_of_10_hash_mismatch_holds(self):
        request = self.request()
        source = self.root / "archive" / "payload" / "source_0.json"
        source.write_text("tampered\n", encoding="utf-8")
        result = self.review(request)
        self.assertEqual("HOLD", result["final_decision"])
        self.assertIn("HOLD_SOURCE_FILE_HASH_OR_SIZE_MISMATCH", result["reason_codes"])

    def test_landing_payload_input_path_set_mismatch_holds(self):
        request = self.request()
        request["bindings"]["landing_payload_input_paths"][0] = "payload/not_the_landing_path.json"
        request["request_self_sha256"] = reviewer.sha256_bytes(
            reviewer.canonical_json_bytes({key: value for key, value in request.items() if key != "request_self_sha256"})
        )
        result = self.review(request)
        self.assertEqual("HOLD", result["final_decision"])
        self.assertIn("HOLD_LANDING_PAYLOAD_INPUT_PATHS_MISMATCH", result["reason_codes"])

    def test_authority_injection_blocks(self):
        result = self.review(self.request(final_decision="ALLOW"))
        self.assertEqual("BLOCK", result["final_decision"])
        self.assertIn("BLOCK_FORBIDDEN_AUTHORITY_INJECTION", result["reason_codes"])

    def test_allow_never_grants_deploy_or_production_execution(self):
        self.review(self.request())
        decision = self.decision()
        self.assertFalse(decision["deployment_authorized"])
        self.assertFalse(decision["production_execution_authority"])
        self.assertFalse(decision["canonical_or_pointer_write_authorized"])
        self.assertFalse(decision["side_effects_executed"])

    def test_status_health_is_functional_and_read_only(self):
        output = self.root / "evidence"
        output.mkdir()
        payload = reviewer.status_payload(self.intake, output, True)
        self.assertEqual("PASS_D8_REVIEWER_FUNCTIONAL_HEALTH", payload["state"])
        self.assertTrue(payload["read_only_status"])
        self.assertTrue(all(payload["checks"].values()))


if __name__ == "__main__":
    unittest.main()
